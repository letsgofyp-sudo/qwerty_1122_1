from django.urls import path
from . import views_authentication
from . import views_rideposting
from . import views_ridebooking
# from . import views_notifications
urlpatterns = [
    path('login/', views_authentication.login, name='login'),
    path('register_pending/', views_authentication.register_pending, name='register_pending'),
    path('signup/', views_authentication.signup, name='signup'),
    path('send_otp/', views_authentication.send_otp, name='send_otp'),
    path('verify_otp/', views_authentication.verify_otp, name='verify_otp'),
    path('verify_password_reset_otp/', views_authentication.verify_password_reset_otp, name='verify_password_reset_otp'),
    path('reset_password/', views_authentication.reset_password, name='reset_password'),
    # User profile (lightweight) for Flutter role detection
    path('users/<int:user_id>/', views_authentication.user_profile, name='user_profile'),
    path('create_trip/', views_rideposting.create_trip, name='create_trip'),
    path('all_trips/', views_rideposting.all_trips, name='all_trips'),
    path('trip/<str:trip_id>/breakdown/', views_rideposting.get_trip_breakdown, name='get_trip_breakdown'),
    path('users/<int:user_id>/vehicles/', views_authentication.user_vehicles, name='user_vehicles'),
    path('vehicles/<int:vehicle_id>/', views_authentication.vehicle_detail, name='vehicle_detail'),
    path('create_route/', views_rideposting.create_route, name='create_route'),
    path('calculate_fare/', views_rideposting.calculate_fare, name='calculate_fare'),
    
    # Image serving endpoints
    path('user_image/<int:user_id>/<str:image_field>/', views_authentication.user_image, name='user_image'),
    path('vehicle_image/<int:vehicle_id>/<str:image_field>/', views_authentication.vehicle_image, name='vehicle_image'),
    
    # MyRides API endpoints
    path('users/<int:user_id>/rides/', views_rideposting.get_user_rides, name='get_user_rides'),
    path('trips/<str:trip_id>/', views_rideposting.get_trip_details, name='get_trip_details'),
    path('trips/<str:trip_id>/update/', views_rideposting.update_trip, name='update_trip'),
    path('trips/<str:trip_id>/delete/', views_rideposting.delete_trip, name='delete_trip'),
    path('trips/<str:trip_id>/cancel/', views_rideposting.cancel_trip, name='cancel_trip'),
    
    # Ride Booking endpoints
    path('ride-booking/<str:trip_id>/', views_ridebooking.get_ride_booking_details, name='get_ride_booking_details'),
    path('ride-booking/<str:trip_id>/request/', views_rideposting.handle_ride_booking_request, name='handle_ride_booking_request'),
    # Driver request management
    path('ride-booking/<str:trip_id>/requests/', views_rideposting.list_pending_requests, name='list_pending_requests'),
    path('ride-booking/<str:trip_id>/requests/<int:booking_id>/', views_rideposting.booking_request_details, name='booking_request_details'),
    path('ride-booking/<str:trip_id>/requests/<int:booking_id>/respond/', views_rideposting.respond_booking_request, name='respond_booking_request'),
    # Passenger decision endpoint
    path('ride-booking/<str:trip_id>/requests/<int:booking_id>/passenger-respond/', views_rideposting.passenger_respond_booking, name='passenger_respond_booking'),
    
    # Additional endpoints that might be needed
    path('routes/<int:route_id>/', views_rideposting.get_route_details, name='get_route_details'),
    path('routes/<int:route_id>/statistics/', views_rideposting.get_route_statistics, name='get_route_statistics'),
    path('routes/search/', views_rideposting.search_routes, name='search_routes'),
    path('trips/<int:trip_id>/available-seats/', views_rideposting.get_available_seats, name='get_available_seats'),
    path('bookings/', views_rideposting.create_booking, name='create_booking'),
    path('users/<int:user_id>/bookings/', views_rideposting.get_user_bookings, name='get_user_bookings'),
    path('rides/search/', views_rideposting.search_rides, name='search_rides'),
    path('rides/<int:ride_id>/', views_rideposting.cancel_ride, name='cancel_ride'),
]
    # Notification endpoints
    # path('update_fcm_token/', views_notifications.update_fcm_token, name='update_fcm_token'),
# ]