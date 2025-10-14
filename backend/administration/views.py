# Add user creation view (GET: show form, POST: save user)
from django.http import HttpResponseRedirect , JsonResponse
from django.contrib.auth import authenticate, login, logout
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt , csrf_protect
import random
from django.views.decorators.http import require_http_methods
from lets_go.models import UsersData
import base64
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.hashers import make_password

@csrf_protect
def user_add_view(request):
    if request.method == 'POST':
        user = UsersData()
        user.name = request.POST.get('name')
        user.username = request.POST.get('username')
        user.email = request.POST.get('email')
        raw_password = request.POST.get('password')
        user.password = make_password(raw_password) if raw_password else None
        user.address = request.POST.get('address')
        phone_no = request.POST.get('phone_no')
        # Ensure phone number has + prefix for international format
        if phone_no and not phone_no.startswith('+'):
            phone_no = '+' + phone_no
        user.phone_no = phone_no
        user.gender = request.POST.get('gender')
        user.status = request.POST.get('status') or 'PENDING'
        user.driver_rating = request.POST.get('driver_rating') or None
        user.passenger_rating = request.POST.get('passenger_rating') or None
        user.cnic_no = request.POST.get('cnic_no')
        user.driving_license_no = request.POST.get('driving_license_no')
        user.accountno = request.POST.get('accountno')
        user.bankname = request.POST.get('bankname')
        # handle file uploads for all binary fields
        if request.FILES.get('accountqr'):
            user.accountqr = request.FILES['accountqr'].read()
        if request.FILES.get('profile_photo'):
            user.profile_photo = request.FILES['profile_photo'].read()
        if request.FILES.get('live_photo'):
            user.live_photo = request.FILES['live_photo'].read()
        if request.FILES.get('cnic_front_image'):
            user.cnic_front_image = request.FILES['cnic_front_image'].read()
        if request.FILES.get('cnic_back_image'):
            user.cnic_back_image = request.FILES['cnic_back_image'].read()
        if request.FILES.get('driving_license_front'):
            user.driving_license_front = request.FILES['driving_license_front'].read()
        if request.FILES.get('driving_license_back'):
            user.driving_license_back = request.FILES['driving_license_back'].read()
        try:
            user.full_clean()
            user.save()
            return redirect('administration:user_list')
        except Exception as e:
            return render(request, 'administration/user_add.html', {'error': str(e)})
    return render(request, 'administration/user_add.html')
# Create your views here.
def admin_view(request):
    return render(request, "administration/index.html")

def api_kpis(request):
    # Replace with real queries
    data = {
        "active_users": random.randint(1000, 1500),
        "rides_today": random.randint(200, 500),
        "cancellations": random.randint(5, 50),
        "avg_wait": round(random.uniform(3.5, 5.0), 2),
        "completed_trips": random.randint(180, 480),
        "flagged_incidents": random.randint(0, 10),
    }
    return JsonResponse(data)

def api_chart_data(request):
    # Include other datasets if needed
    return JsonResponse({
        "tsRides": [300, 320, 310, 340, 360, 380, 400],
        "byHour": [15, 45, 190, 340, 260, 110, 25],
        "drivers": [800, 820, 830, 850, 870, 900, 920],
        "riders": [600, 620, 640, 660, 680, 700, 730],
        "cancelReasons": [12, 8, 5, 2],
        "completedTrips": [300,320,310,340,360,380,400],
        "avgWait": [5,4.8,4.9,4.6,4.4,4.3,4.2],
    })

def user_list_view(request):
    return render(request, 'administration/users_list.html')
# AJAX API: list users
def api_users(request):
    qs = UsersData.objects.all().values(
        'id','name','email','status','driver_rating','passenger_rating','created_at'
    )
    return JsonResponse({'users': list(qs)})
# 2) Detail page
def user_detail_view(request, user_id):
    # api_user_detail(request, user_id)
    return render(request, 'administration/users_detail.html', {'user_id': user_id})
# AJAX API: detail JSON
def api_user_detail(request, user_id):
    user = get_object_or_404(UsersData, pk=user_id)
    data = {f: getattr(user, f) for f in [
        'id','name','username','email','address','phone_no','status','gender',
        'driver_rating','passenger_rating','cnic_no','driving_license_no',
        'accountno','bankname','created_at','updated_at'
    ]}
    # Add all image/binary fields
    for img in ['accountqr','profile_photo','live_photo','cnic_front_image','cnic_back_image','driving_license_front','driving_license_back']:
        blob = getattr(user, img)
        data[img] = f"data:image/jpeg;base64,{base64.b64encode(blob).decode()}" if blob else None
    return JsonResponse(data)
# Update status via HTML form
@require_http_methods(['POST'])
def update_user_status_view(request, user_id):
    user = get_object_or_404(UsersData, pk=user_id)
    status = request.POST.get('status')
    if status in ['PENDING','VERIFIED','REJECTED','BANNED']:
        user.status = status
        user.save()
    return redirect('administration:user_detail', user_id=user_id)
# 3) Edit page HTML form
def user_edit_view(request, user_id):
    user = get_object_or_404(UsersData, pk=user_id)
    return render(request, 'administration/users_edit.html', {'user': user, 'user_id': user_id})
# Handle edit form submission
@require_http_methods(['POST'])
def submit_user_edit(request, user_id):
    user = get_object_or_404(UsersData, pk=user_id)
    user.name = request.POST.get('name')
    user.username = request.POST.get('username')
    user.email = request.POST.get('email')
    password = request.POST.get('password')
    if password:
        user.password = make_password(password)
    user.address = request.POST.get('address')
    phone_no = request.POST.get('phone_no')
    # Ensure phone number has + prefix for international format
    if phone_no and not phone_no.startswith('+'):
        phone_no = '+' + phone_no
    user.phone_no = phone_no
    user.gender = request.POST.get('gender')
    user.status = request.POST.get('status')
    user.driver_rating = request.POST.get('driver_rating') or None
    user.passenger_rating = request.POST.get('passenger_rating') or None
    user.cnic_no = request.POST.get('cnic_no')
    user.driving_license_no = request.POST.get('driving_license_no')
    user.accountno = request.POST.get('accountno')
    user.bankname = request.POST.get('bankname')
    # handle file uploads for all binary fields
    if request.FILES.get('accountqr'):
        user.accountqr = request.FILES['accountqr'].read()
    if request.FILES.get('profile_photo'):
        user.profile_photo = request.FILES['profile_photo'].read()
    if request.FILES.get('live_photo'):
        user.live_photo = request.FILES['live_photo'].read()
    if request.FILES.get('cnic_front_image'):
        user.cnic_front_image = request.FILES['cnic_front_image'].read()
    if request.FILES.get('cnic_back_image'):
        user.cnic_back_image = request.FILES['cnic_back_image'].read()
    if request.FILES.get('driving_license_front'):
        user.driving_license_front = request.FILES['driving_license_front'].read()
    if request.FILES.get('driving_license_back'):
        user.driving_license_back = request.FILES['driving_license_back'].read()
    try:
        user.full_clean()
        user.save()
        return redirect('administration:user_detail', user_id=user_id)
    except Exception as e:
        return render(request, 'administration/users_edit.html', {'user': user, 'user_id': user_id, 'error': str(e)})
@csrf_exempt
def login_view(request):
    error_message = ''
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user_admin = authenticate(request, username=username, password=password)
        if user_admin is not None:
            login(request, user_admin)
            return redirect('administration:admin_view')
        else:
            error_message = 'Invalid credentials'
    return render(request, 'administration/login.html', {'error_message': error_message})
def logout_view(request):
    logout(request)
    return HttpResponseRedirect(reverse("recipt:login"))
