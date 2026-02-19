from django.urls import path
from . import views

app_name = 'events'

urlpatterns = [
    # Public
    path('', views.public_events, name='public'),

    # Admin page
    path('admin/', views.admin_page, name='admin_page'),

    # Admin API — Events
    path('admin/api/list/', views.api_event_list, name='api_list'),
    path('admin/api/create/', views.api_event_create, name='api_create'),
    path('admin/api/<int:event_id>/', views.api_event_detail, name='api_detail'),
    path('admin/api/<int:event_id>/update/', views.api_event_update, name='api_update'),
    path('admin/api/<int:event_id>/delete/', views.api_event_delete, name='api_delete'),
    path('admin/api/<int:event_id>/approve/', views.api_event_approve, name='api_approve'),

    # Admin API — Event Categories
    path('admin/api/categories/', views.api_category_list, name='api_category_list'),
    path('admin/api/categories/create/', views.api_category_create, name='api_category_create'),
    path('admin/api/categories/<int:category_id>/update/', views.api_category_update, name='api_category_update'),
    path('admin/api/categories/<int:category_id>/delete/', views.api_category_delete, name='api_category_delete'),
]
