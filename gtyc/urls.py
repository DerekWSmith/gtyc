from django.contrib import admin
from django.shortcuts import redirect
from django.urls import include, path

urlpatterns = [
    path('', lambda request: redirect('accounts:login')),
    path('accounts/', include('accounts.urls')),
    path('roster/', include('roster.urls')),
    path('events/', include('events.urls')),
    path('admin/', admin.site.urls),
]
