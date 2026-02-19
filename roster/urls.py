from django.urls import path
from . import views

app_name = 'roster'

urlpatterns = [
    # Public
    path('', views.public_roster, name='public'),

    # Admin page
    path('admin/', views.admin_page, name='admin_page'),
    path('admin/print/', views.print_view, name='print'),

    # Admin API — Staff
    path('admin/staff/', views.api_staff_list, name='api_staff_list'),
    path('admin/staff/add/', views.api_staff_add, name='api_staff_add'),
    path('admin/staff/<int:staff_id>/update/', views.api_staff_update, name='api_staff_update'),
    path('admin/staff/<int:staff_id>/delete/', views.api_staff_delete, name='api_staff_delete'),
    path('admin/staff/reorder/', views.api_staff_reorder, name='api_staff_reorder'),

    # Admin API — Dates
    path('admin/dates/', views.api_dates, name='api_dates'),
    path('admin/dates/<str:date_str>/override/', views.api_override, name='api_override'),
    path('admin/dates/<str:date_str>/clear/', views.api_clear_override, name='api_clear_override'),
]
