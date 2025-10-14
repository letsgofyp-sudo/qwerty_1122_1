from . import views
from django.urls import path
app_name = 'administration'
urlpatterns = [
    # Admin view
    path('', views.admin_view, name='admin_view'),
    path("api/kpis/", views.api_kpis, name="api_kpis"),
    path("api/chart-data/", views.api_chart_data, name="api_chart_data"),
    # Login view
    path('login/', views.login_view, name='login_view'),
    # Logout view
    path('logout/', views.logout_view, name='logout_view'),
    # List page
    path('users/', views.user_list_view, name='user_list'),
    # API for AJAX
    path('users/api/', views.api_users, name='api_users'),

    # Add user page
    path('users/add/', views.user_add_view, name='user_add'),

    # Detail page
    path('users/<int:user_id>/view/', views.user_detail_view, name='user_detail'),
    path('users/<int:user_id>/view/api/', views.api_user_detail, name='api_user_detail'),
    path('users/<int:user_id>/view/status/', views.update_user_status_view, name='update_user_status'),

    # Edit page
    path('users/<int:user_id>/edit/', views.user_edit_view, name='user_edit'),
    path('users/<int:user_id>/edit/submit/', views.submit_user_edit, name='submit_user_edit'),
]
