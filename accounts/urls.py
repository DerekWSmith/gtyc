from django.urls import path
from . import views, admin_views

app_name = 'accounts'

urlpatterns = [
    path('login/', views.login_view, name='login'),
    path('register/', views.register_view, name='register'),
    path('logout/', views.logout_view, name='logout'),
    path('password-reset/request/', views.password_reset_request_view, name='password_reset_request'),
    path('password-reset/<uidb64>/<token>/', views.password_reset_confirm_view, name='password_reset_confirm'),

    # Member management (secretary only)
    path('members/', admin_views.members_admin_page, name='members_admin'),
    path('members/api/list/', admin_views.api_member_list, name='api_member_list'),
    path('members/api/create/', admin_views.api_member_create, name='api_member_create'),
    path('members/api/<int:user_id>/', admin_views.api_member_detail, name='api_member_detail'),
    path('members/api/<int:user_id>/update/', admin_views.api_member_update, name='api_member_update'),
]
