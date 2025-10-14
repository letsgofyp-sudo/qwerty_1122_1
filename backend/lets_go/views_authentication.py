from django.shortcuts import render
from django.http import JsonResponse, HttpResponse, Http404
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.hashers import make_password, check_password
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.utils import timezone
from datetime import datetime, timedelta, time
import time as pytime
from decimal import Decimal
import json
import random
import string
import base64
from .models import UsersData, Vehicle, Trip, Route, RouteStop, TripStopBreakdown, Booking
from django.views.decorators.http import require_GET
from .utils.fare_calculator import is_peak_hour, get_fare_matrix_for_route
from .email_otp import send_email_otp, send_email_otp_for_reset
from .phone_otp_send import send_phone_otp, send_phone_otp_for_reset
from .constants import url

def get_user_data_dict(request, user):
    data = {
        'id': user.id,
        'name': user.name,
        'username': user.username,
        'email': user.email,
        'password': user.password,  # Only include if needed for admin/debug; remove for security in production
        'address': user.address,
        'phone_no': user.phone_no,
        'phone_number': user.phone_no,
        'cnic_no': user.cnic_no,
        'cnic': user.cnic_no,
        'gender': user.gender,
        'driving_license_no': user.driving_license_no,
        'accountno': user.accountno,
        'bankname': user.bankname,
        'status': user.status,
        'driver_rating': user.driver_rating,
        'passenger_rating': user.passenger_rating,
        'created_at': user.created_at.isoformat() if user.created_at else None,
        'updated_at': user.updated_at.isoformat() if user.updated_at else None,
    }
    # Images according to current UsersData model
    image_fields = [
        'profile_photo', 'live_photo',
        'cnic_front_image', 'cnic_back_image',
        'driving_license_front', 'driving_license_back',
        'accountqr'
    ]
    for field in image_fields:
        if getattr(user, field):
            data[field] = f"{url}/lets_go/user_image/{user.id}/{field}/"
        else:

            data[field] = None
    # Add vehicles if any
    vehicles = []
    if hasattr(user, 'vehicles'):
        for v in user.vehicles.all():
            vehicle_data = {
                'id': v.id,
                'model_number': v.model_number,
                'variant': v.variant,
                'company_name': v.company_name,
                'plate_number': v.plate_number,
                'vehicle_type': v.vehicle_type,
                'color': v.color,
                'seats': v.seats,
                'engine_number': v.engine_number,
                'chassis_number': v.chassis_number,
                'fuel_type': v.fuel_type,
                'registration_date': str(v.registration_date) if v.registration_date else None,
                'insurance_expiry': str(v.insurance_expiry) if v.insurance_expiry else None,
                'photo_front': f'{url}/lets_go/vehicle_image/{v.id}/photo_front/' if v.photo_front else None,
                'photo_back': f'{url}/lets_go/vehicle_image/{v.id}/photo_back/' if v.photo_back else None,
                'documents_image': f'{url}/lets_go/vehicle_image/{v.id}/documents_image/' if v.documents_image else None,
            }
            vehicles.append(vehicle_data)
    data['vehicles'] = vehicles
    print(f"data: {data}")
    return data

@require_GET
def user_profile(request, user_id):
    """Return a user's profile with license-related fields so the app can detect driver status.
    Returns a lightweight object with URLs for images (no binary blobs).
    """
    try:
        # Fetch user with essential fields only; avoid loading binary fields
        user = (
            UsersData.objects.only(
                'id', 'name', 'username', 'email', 'address', 'phone_no',
                'cnic_no', 'gender', 'status', 'driver_rating', 'passenger_rating',
                'created_at', 'updated_at',
                # License-related fields
                'driving_license_no'
            ).get(id=user_id)
        )

        # Build response. Reuse helper to include image URLs and vehicles list as URLs/ids only
        # Note: get_user_data_dict generates URL paths for images and enumerates vehicles
        data = get_user_data_dict(request, user)
        return JsonResponse(data)
    except UsersData.DoesNotExist:
        return JsonResponse({'error': 'User not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

def get_user_summary_dict(user):
    """Lightweight user serializer for login: avoids loading large image blobs and vehicles."""
    return {
        'id': user.id,
        'name': user.name,
        'username': user.username,
        'email': user.email,
        'address': user.address,
        'phone_no': user.phone_no,
        'cnic_no': user.cnic_no,
        'gender': user.gender,
        'status': user.status,
        'driving_license_no': user.driving_license_no,
        'driver_rating': user.driver_rating,
        'passenger_rating': user.passenger_rating,
        'created_at': user.created_at.isoformat() if user.created_at else None,
        'updated_at': user.updated_at.isoformat() if user.updated_at else None,
        # Do not include password, images, or vehicles here.
    }

@csrf_exempt
def login(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')
        print(f"email: {email}")
        print(f"password: {password}")
        try:
            # Fetch only essential fields to avoid loading large blobs on login
            user = (
                UsersData.objects.only(
                    'id', 'name', 'username', 'email', 'password', 'address', 'phone_no',
                    'cnic_no', 'gender', 'status', 'driver_rating', 'passenger_rating',
                    'created_at', 'updated_at'
                )
                .get(email=email)
            )
            print(f" user is {user}")
            if check_password(password, user.password):
                request.session['user_id'] = user.id
                print(f"user_id: {user.id}")
                # Return a lightweight payload to keep login fast
                user_summary = get_user_summary_dict(user)
                return JsonResponse({'success': True, 'message': 'Login successful', 'UsersData': [user_summary]})
            else:
                return JsonResponse({'success': False, 'error': 'Invalid email or password'}, status=404)
        except UsersData.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Invalid email or password'}, status=404)
    else:
        return JsonResponse({'error': 'Invalid request method'}, status=400)

@csrf_exempt
def register_pending(request):
    if request.method == 'GET':
        user_id = request.session.get('user_id')
        if not user_id:
            return JsonResponse({'error': 'No user session found'}, status=400)
        user = UsersData.objects.get(id=user_id)
        print(f"user: {user}")
        user_data = get_user_data_dict(request, user)
        print(f"user_data: {user_data}")
        return JsonResponse({'message': 'Registration pending', 'UsersData': [user_data]})
    else:
        return JsonResponse({'error': 'Invalid request method'}, status=400)


def user_image(request, user_id, image_field):
    """Serve user profile images"""
    try:
        print(f"Attempting to serve {image_field} for user {user_id}")
        # Ensure the requested field exists on the model
        if not hasattr(UsersData, image_field):
            print(f"Invalid image field requested: {image_field}")
            raise Http404("Invalid image field")

        # Increase statement timeout locally for this request to avoid large-blob timeouts
        from django.db import connection
        try:
            with connection.cursor() as cursor:
                cursor.execute("SET LOCAL statement_timeout = 30000")  # 30 seconds
        except Exception as e:
            print(f"Warning: could not set local statement_timeout: {e}")

        # Fetch only the specific binary field to avoid loading entire row with large blobs
        image_data = (
            UsersData.objects.only(image_field)
            .values_list(image_field, flat=True)
            .get(id=user_id)
        )
        
        print(f"Image data type: {type(image_data)}")
        try:
            print(f"Image data length: {len(image_data) if image_data is not None else 'None'}")
        except Exception:
            pass
        
        if not image_data:
            print(f"No image data found for {image_field}")
            raise Http404("Image not found")
        
        # Handle different image data types
        if isinstance(image_data, bytes):
            # already bytes
            pass
        elif isinstance(image_data, memoryview):
            # Convert memoryview to bytes
            image_data = image_data.tobytes()
        elif isinstance(image_data, str):
            # Data might be base64 encoded or a file path
            try:
                # Try to decode base64 if it's encoded
                import base64
                image_data = base64.b64decode(image_data)
            except:
                # If not base64, treat as file path
                raise Http404("Invalid image format")
        else:
            # Convert to bytes if possible
            try:
                image_data = bytes(image_data)
            except:
                raise Http404("Invalid image format")
        
        # Determine content type based on image field
        content_type = 'image/jpeg'  # Default
        if image_field in ['profile_photo', 'live_photo']:
            content_type = 'image/jpeg'
        elif image_field in ['cnic_front_image', 'cnic_back_image']:
            content_type = 'image/jpeg'
        elif image_field == 'accountqr':
            content_type = 'image/png'  # QR codes are usually PNG
        
        print(f"Serving image with content type: {content_type}")
        try:
            print(f"Final image data length: {len(image_data)} bytes")
        except Exception:
            pass
        
        # Set cache headers for better performance
        response = HttpResponse(image_data, content_type=content_type)
        response['Cache-Control'] = 'public, max-age=3600'  # Cache for 1 hour
        return response
        
    except UsersData.DoesNotExist:
        print(f"User {user_id} not found")
        raise Http404("User not found")
    except Exception as e:
        print(f"Error serving image {image_field} for user {user_id}: {str(e)}")
        raise Http404("Image not found")

@require_GET
def vehicle_image(request, vehicle_id, image_field):
    """Serve vehicle images"""
    try:
        print(f"Attempting to serve {image_field} for vehicle {vehicle_id}")
        vehicle = Vehicle.objects.get(id=vehicle_id)
        image_data = getattr(vehicle, image_field)
        
        print(f"Image data type: {type(image_data)}")
        print(f"Image data length: {len(image_data) if image_data else 'None'}")
        
        if not image_data:
            print(f"No image data found for {image_field}")
            raise Http404("Image not found")
        
        # Handle different image data types
        if isinstance(image_data, bytes):
            # Data is already in bytes format
            pass
        elif isinstance(image_data, str):
            # Data might be base64 encoded or a file path
            try:
                # Try to decode base64 if it's encoded
                import base64
                image_data = base64.b64decode(image_data)
            except:
                # If not base64, treat as file path
                raise Http404("Invalid image format")
        else:
            # Convert to bytes if possible
            try:
                image_data = bytes(image_data)
            except:
                raise Http404("Invalid image format")
        
        # Determine content type based on image field
        content_type = 'image/jpeg'  # Default for vehicle photos
        
        print(f"Serving image with content type: {content_type}")
        print(f"Final image data length: {len(image_data)} bytes")
        
        # Set cache headers for better performance
        response = HttpResponse(image_data, content_type=content_type)
        response['Cache-Control'] = 'public, max-age=3600'  # Cache for 1 hour
        return response
        
    except Vehicle.DoesNotExist:
        print(f"Vehicle {vehicle_id} not found")
        raise Http404("Vehicle not found")
    except Exception as e:
        print(f"Error serving image {image_field} for vehicle {vehicle_id}: {str(e)}")
        raise Http404("Image not found")

@require_GET
def user_vehicles(request, user_id):
    try:
        # Fetch user (lightweight)
        UsersData.objects.only('id').get(id=user_id)

        # Important: Build a lightweight vehicle list to avoid loading binary image fields.
        # Do not access v.photo_* attributes directly, as that may load large blobs.
        qs = (
            Vehicle.objects
            .filter(owner_id=user_id)
            .only(
                'id', 'model_number', 'company_name', 'plate_number',
                'vehicle_type', 'color', 'seats', 'fuel_type', 'variant',
                'engine_number', 'chassis_number', 'registration_date', 'insurance_expiry'
            )
            .defer(
                'photo_front', 'photo_back', 'documents_image'
            )
        )

        vehicles = []
        for v in qs:
            vehicles.append({
                'id': v.id,
                # New, minimal keys
                'model': v.model_number,
                'make': v.company_name,
                'registration_no': v.plate_number,
                'vehicle_type': v.vehicle_type,
                'color': v.color,
                'seats': v.seats,
                'fuel_type': (v.get_fuel_type_display() if hasattr(v, 'get_fuel_type_display') and v.fuel_type else ''),
                'variant': v.variant,
                'engine_number': v.engine_number,
                'chassis_number': v.chassis_number,
                'registration_date': (v.registration_date.isoformat() if v.registration_date else None),
                'insurance_expiry': (v.insurance_expiry.isoformat() if v.insurance_expiry else None),
                # Compatibility keys expected by existing Flutter UI
                'model_number': v.model_number,
                'company_name': v.company_name,
                'plate_number': v.plate_number,
                # Always provide image URL path (handler returns 404 if not present)
                'photo_front': f'{url}/lets_go/vehicle_image/{v.id}/photo_front/',
                'photo_back': f'{url}/lets_go/vehicle_image/{v.id}/photo_back/',
                'documents_image': f'{url}/lets_go/vehicle_image/{v.id}/documents_image/',
            })

        return JsonResponse({'vehicles': vehicles})
    except UsersData.DoesNotExist:
        return JsonResponse({'vehicles': []})

@require_GET
def vehicle_detail(request, vehicle_id):
    try:
        # Load all non-binary, display-relevant fields efficiently
        v = (
            Vehicle.objects
            .only(
                'id', 'model_number', 'company_name', 'plate_number',
                'vehicle_type', 'color', 'seats', 'fuel_type', 'variant',
                'engine_number', 'chassis_number', 'registration_date', 'insurance_expiry'
            )
            .get(id=vehicle_id)
        )

        data = {
            'id': v.id,
            'model_number': v.model_number,
            'company_name': v.company_name,
            'plate_number': v.plate_number,
            'vehicle_type': v.vehicle_type,
            'color': v.color,
            'seats': v.seats,
            'fuel_type': (v.get_fuel_type_display() if hasattr(v, 'get_fuel_type_display') and v.fuel_type else ''),
            'variant': v.variant,
            'engine_number': v.engine_number,
            'chassis_number': v.chassis_number,
            'registration_date': (v.registration_date.isoformat() if v.registration_date else None),
            'insurance_expiry': (v.insurance_expiry.isoformat() if v.insurance_expiry else None),
            # Image handler URLs (may 404 if not present)
            'photo_front': f'{url}/lets_go/vehicle_image/{v.id}/photo_front/',
            'photo_back': f'{url}/lets_go/vehicle_image/{v.id}/photo_back/',
            'documents_image': f'{url}/lets_go/vehicle_image/{v.id}/documents_image/',
        }
        return JsonResponse(data)
    except Vehicle.DoesNotExist:
        return JsonResponse({'error': 'Vehicle not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
@csrf_exempt
def signup(request):
    if request.method == 'POST':
        try:
            import json
            data = request.POST.dict()
            files = request.FILES
            email = data.get('email')
            phone = data.get('phone_no')
            if not email or not phone:
                return JsonResponse({'success': False, 'error': 'Email and phone are required.'}, status=400)
            cache_key = get_cache_key(email)
            cached = cache.get(cache_key)
            if not cached or not (cached.get('email_verified') and cached.get('phone_verified')):
                return JsonResponse({'success': False, 'error': 'Both OTPs must be verified before registration.'}, status=400)
            # Check for duplicate email/username/phone
            if UsersData.objects.filter(email=email).exists():
                return JsonResponse({'success': False, 'error': 'Email already registered.'}, status=400)
            if UsersData.objects.filter(username=data.get('username')).exists():
                return JsonResponse({'success': False, 'error': 'Username already registered.'}, status=400)
            if UsersData.objects.filter(phone_no=phone).exists():
                return JsonResponse({'success': False, 'error': 'Phone number already registered.'}, status=400)
            # Create user
            print("----------------creating user----------------")

            print(f"data: {data}")
            print(f"files: {files}")
            print(f"email: {email}")
            print(f"phone: {phone}")
            user = UsersData(
                name=data.get('name', ''),
                username=data.get('username', ''),
                email=email,
                password=make_password(data.get('password', '')),
                address=data.get('address', ''),
                phone_no=phone,
                cnic_no=data.get('cnic_no', ''),
                gender=data.get('gender', ''),
                driving_license_no=data.get('driving_license_no', ''),
                accountno=data.get('accountno', ''),
                bankname=data.get('bankname', ''),
                profile_photo=files['profile_photo'].read() if 'profile_photo' in files else None,
                live_photo=files['live_photo'].read() if 'live_photo' in files else None,
                cnic_front_image=files['cnic_front_image'].read() if 'cnic_front_image' in files else None,
                cnic_back_image=files['cnic_back_image'].read() if 'cnic_back_image' in files else None,
                driving_license_front=files['driving_license_front'].read() if 'driving_license_front' in files else None,
                driving_license_back=files['driving_license_back'].read() if 'driving_license_back' in files else None,
                accountqr=files['accountqr'].read() if 'accountqr' in files else None,
            )
            user.save()
            # Parse vehicles JSON
            vehicles_json = data.get('vehicles')
            if vehicles_json:
                vehicles = json.loads(vehicles_json)
                print(f"vehicles : {vehicles}")
                for v in vehicles:
                    plate = v.get('plate_number')
                    Vehicle.objects.create(
                        owner=user,
                        model_number=v.get('model_number', ''),
                        variant=v.get('variant', ''),
                        company_name=v.get('company_name', ''),
                        plate_number=plate,
                        vehicle_type=v.get('vehicle_type', 'TW'),
                        color=v.get('color', ''),
                        photo_front=files.get(f'photo_front_{plate}').read() if files.get(f'photo_front_{plate}') else None,
                        photo_back=files.get(f'photo_back_{plate}').read() if files.get(f'photo_back_{plate}') else None,
                        documents_image=files.get(f'documents_image_{plate}').read() if files.get(f'documents_image_{plate}') else None,
                        seats=int(v['seats']), # if v.get('vehicle_type') == 'FW' and v.get('seats') else None,
                        engine_number=v.get('engine_number', ''),
                        chassis_number=v.get('chassis_number', ''),
                        fuel_type=v.get('fuel_type', ''),
                        registration_date=v.get('registration_date') or None,
                        insurance_expiry=v.get('insurance_expiry') or None,
                    )
            cache.delete(cache_key)
            return JsonResponse({'success': True, 'message': 'Registration successful.'})
        except Exception as e:
            print(f"error: {e}")
            return JsonResponse({'success': False, 'error': str(e)}, status=400)
    return JsonResponse({'error': 'Invalid request method'}, status=400)

def generate_otp(length=6):
    return ''.join(random.choices(string.digits, k=length))

def get_cache_key(email):
    return f"pending_signup_{email}"

def get_reset_cache_key(method, value):
    return f"reset_pwd_{method}_{value}"

def send_otp_internal(email, phone, resend, otp_for, cached_data):
    now = int(pytime.time())
    
    # Cooldown check
    if 'email_expiry' in cached_data and now < cached_data['email_expiry'] and (resend == 'email' or resend == 'both'):
        return {'success': False, 'error': 'An OTP has already been sent. Please wait.'}
    if 'phone_expiry' in cached_data and now < cached_data['phone_expiry'] and (resend == 'phone' or resend == 'both'):
        return {'success': False, 'error': 'An OTP has already been sent. Please wait.'}

    email_otp = cached_data.get('email_otp')
    phone_otp = cached_data.get('phone_otp')

    if otp_for == 'verify_email_phoneno':
        if email and (resend in ['email', 'both']) and not cached_data.get('email_verified'):
            email_otp = generate_otp()
            print(f"email_otp for verification: {email_otp} email : {email}")
            # send_email_otp(email, email_otp)
            cached_data['email_expiry'] = now + 300
        
        if phone and (resend in ['phone', 'both']) and not cached_data.get('phone_verified'):
            phone_otp = generate_otp()
            print(f"phone_otp for verification: {phone_otp} phone: {phone}")
            # send_phone_otp(phone, phone_otp)
            cached_data['phone_expiry'] = now + 300
    else:  # for reset password
        if email and (resend in ['email', 'both']):
            email_otp = generate_otp()
            print(f"email_otp for reset password: {email_otp} email : {email}")
            # send_email_otp_for_reset(email, email_otp)
            cached_data['email_expiry'] = now + 300

        if phone and (resend in ['phone', 'both']):
            phone_otp = generate_otp()
            print(f"phone_otp for reset password: {phone_otp} phone: {phone}")
            # send_phone_otp_for_reset(phone, phone_otp)
            cached_data['phone_expiry'] = now + 300

    cached_data['email_otp'] = email_otp
    cached_data['phone_otp'] = phone_otp
    
    cache_key = get_cache_key(email if email else phone)
    
    cache.set(cache_key, cached_data, timeout=300)
    
    return {
        'success': True,
        'message': 'OTP(s) sent.',
        'email_expiry': cached_data.get('email_expiry'),
        'phone_expiry': cached_data.get('phone_expiry')
    }

@csrf_exempt
def send_otp(request):
    """
    Handles sending OTPs for both registration and password reset.
    - For registration: uses get_cache_key and stores OTPs under 'email_otp'/'phone_otp' with verification flags.
    - For reset_password: uses get_reset_cache_key and stores OTPs under 'email_otp'/'phone_otp' with verification flags.
    The frontend must send:
      - email or phone_no
      - otp_for: 'registration' or 'reset_password'
      - resend: 'email', 'phone', or 'both'
    """
    if request.method == 'POST':
        data = request.POST.dict()
        email = data.get('email', '').strip()
        phone = data.get('phone_no', '').strip()
        otp_for = data.get('otp_for', 'registration')
        resend = data.get('resend', 'both')
        print(f"data: {data}")
        print(f"email: {email}")
        print(f"phone: {phone}")
        print(f"otp_for: {otp_for}")
        print(f"resend: {resend}")
        if not email and not phone:
            return JsonResponse({'success': False, 'error': 'Email or phone is required.'}, status=400)

        # Choose the correct cache key and structure
        if otp_for == 'reset_password':
            method = 'email' if email else 'phone'
            value = email if email else phone
            cache_key = get_reset_cache_key(method, value)
        else:
            cache_key = get_cache_key(email if email else phone)

        cached = cache.get(cache_key) or {}

        # For registration, block resend if already verified
        if otp_for == 'registration' and (cached.get('email_verified') or cached.get('phone_verified')):
            return JsonResponse({'success': False, 'error': 'OTP already verified.'}, status=400)

        import random, time
        now = int(pytime.time())
        # Generate OTPs as needed
        email_otp = str(random.randint(100000, 999999)) if email else None
        phone_otp = str(random.randint(100000, 999999)) if phone else None
        email_expiry = now + 300 if email else None
        phone_expiry = now + 300 if phone else None

        # Build the cache data structure
        cache_data = {
            'email': email,
            'phone_no': phone,
            'otp_for': otp_for,
            'email_otp': email_otp if resend in ['email', 'both'] else cached.get('email_otp'),
            'phone_otp': phone_otp if resend in ['phone', 'both'] else cached.get('phone_otp'),
            'email_expiry': email_expiry if resend in ['email', 'both'] else cached.get('email_expiry'),
            'phone_expiry': phone_expiry if resend in ['phone', 'both'] else cached.get('phone_expiry'),
            'email_verified': False if resend in ['email', 'both'] else cached.get('email_verified', False),
            'phone_verified': False if resend in ['phone', 'both'] else cached.get('phone_verified', False),
        }
        cache.set(cache_key, cache_data, timeout=300)

        print(f"cache_data line 399 : {cache_data}")
        print(f"cache_key line 340 : {cache_key}")
        # if otp_for == 'registration':
        #     send_email_otp(email, cache_data['email_otp'])
        #     send_phone_otp(phone, cache_data['phone_otp'])
        # else:
        #     send_email_otp_for_reset(email, cache_data['email_otp'])
        #     send_phone_otp_for_reset(phone, cache_data['phone_otp'])


        return JsonResponse({
            'success': True,
            'message': 'OTP sent',
            'email_expiry': cache_data.get('email_expiry'),
            'phone_expiry': cache_data.get('phone_expiry')
        })
    return JsonResponse({'success': False, 'error': 'Invalid request'}, status=400)

@csrf_exempt
def verify_otp(request):
    if request.method == 'POST':
        data = request.POST.dict()
        email = data.get('email', '').strip()
        phone = data.get('phone_no', '').strip()
        otp_for = data.get('otp_for', 'registration')
        otp = data.get('otp', '').strip()
        which = data.get('which', '')  # 'email' or 'phone'
        cache_key = get_cache_key(email if email else phone)
        cached = cache.get(cache_key)
        if not cached:
            return JsonResponse({'success': False, 'error': 'OTP session expired. Please request a new OTP.'}, status=400)
        now = int(pytime.time())
        # Check which OTP to verify
        if which == 'email' and cached.get('email_otp') == otp and now <= cached.get('email_expiry', 0):
            cached['email_verified'] = True
            cache.set(cache_key, cached, timeout=300)
            return JsonResponse({'success': True, 'message': 'Email OTP verified.'})
        elif which == 'phone' and cached.get('phone_otp') == otp and now <= cached.get('phone_expiry', 0):
            cached['phone_verified'] = True
            cache.set(cache_key, cached, timeout=300)
            return JsonResponse({'success': True, 'message': 'Phone OTP verified.'})
        else:
            return JsonResponse({'success': False, 'error': 'Invalid or expired OTP.'}, status=400)
    return JsonResponse({'success': False, 'error': 'Invalid request'}, status=400)

@csrf_exempt
def verify_password_reset_otp(request):
    if request.method == 'POST':
        method = request.POST.get('method')  # 'email' or 'phone'
        value = request.POST.get('value')    # email address or phone number
        otp = request.POST.get('otp')        # OTP entered by user
        print(f"method: {method}")
        print(f"value: {value}")
        print(f"otp: {otp}")
        # Validate required fields
        if method not in ['email', 'phone'] or not value or not otp:
            return JsonResponse({'success': False, 'error': 'Invalid data.'}, status=400)

        # Build the cache key for password reset OTPs
        cache_key = get_reset_cache_key(method, value)
        print(f"cache_key: {cache_key}")
        cached = cache.get(cache_key)
        print(f"cached: {cached}")
        if not cached:
            return JsonResponse({'success': False, 'error': 'OTP expired or not found.'}, status=400)

        # Get the correct expiry and OTP key based on method
        expiry_timestamp = cached.get('email_expiry') if method == 'email' else cached.get('phone_expiry')
        otp_key = 'email_otp' if method == 'email' else 'phone_otp'
        print(f"cached['{otp_key}']: {cached.get(otp_key)}")
        # Check if the OTP matches
        if cached.get(otp_key) == otp:
            # Mark as verified and update cache
            cache.set(cache_key, {otp_key: otp, 'verified': True, 'expiry': expiry_timestamp}, timeout=300)
            return JsonResponse({'success': True, 'message': 'OTP verified.', 'expiry': expiry_timestamp})
        else:
            return JsonResponse({'success': False, 'error': 'Invalid OTP.', 'expiry': expiry_timestamp}, status=400)
    return JsonResponse({'success': False, 'error': 'Invalid request method.'}, status=400)

@csrf_exempt
def reset_password(request):
    if request.method == 'POST':
        method = request.POST.get('method')
        value = request.POST.get('value')
        new_password = request.POST.get('new_password')
        if method not in ['email', 'phone'] or not value or not new_password:
            return JsonResponse({'success': False, 'error': 'Invalid data.'}, status=400)

        cache_key = get_reset_cache_key(method, value)
        cached = cache.get(cache_key)
        if not cached or not cached.get('verified'):
            return JsonResponse({'success': False, 'error': 'OTP not verified or expired.'}, status=400)

        try:
            if method == 'email':
                user = UsersData.objects.get(email=value)
            else:
                user = UsersData.objects.get(phone_no=value)
            user.password = make_password(new_password)
            user.save()
            cache.delete(cache_key)
            return JsonResponse({'success': True, 'message': 'Password reset successful.'})
        except UsersData.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'User not found.'}, status=404)
    return JsonResponse({'success': False, 'error': 'Invalid request method.'}, status=400)


