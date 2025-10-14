from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import ensure_csrf_cookie
import json
from .models.models_userdata import UsersData

@csrf_exempt
@require_http_methods(["POST"])
def update_fcm_token(request):
    try:
        # Parse request data
        data = json.loads(request.body)
        fcm_token = data.get('fcm_token')
        
        if not fcm_token:
            return JsonResponse({'error': 'FCM token is required'}, status=400)
        
        # Get the current user
        user = request.user
        if not user.is_authenticated:
            return JsonResponse({'error': 'Authentication required'}, status=401)
        
        # Update the user's FCM token
        user_profile = UsersData.objects.get(id=user.id)
        user_profile.fcm_token = fcm_token
        user_profile.save()
        
        return JsonResponse({'message': 'FCM token updated successfully'}, status=200)
    
    except UsersData.DoesNotExist:
        return JsonResponse({'error': 'User not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
