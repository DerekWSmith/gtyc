from functools import wraps

from django.http import JsonResponse
from django.shortcuts import redirect, render


def _is_api_request(request):
    """Check if this is an API request (expects JSON)."""
    return (
        request.content_type == 'application/json'
        or request.headers.get('Accept', '').startswith('application/json')
        or '/api/' in request.path
    )


def admin_required(view_func):
    """Require authenticated user with club admin access (Secretary or Event Officer)."""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('accounts:login')
        if not request.user.can_admin:
            if _is_api_request(request):
                return JsonResponse({'error': 'Admin access required'}, status=403)
            return render(request, '403.html', status=403)
        return view_func(request, *args, **kwargs)
    return wrapper


def event_officer_required(view_func):
    """Require authenticated user who can approve events (Secretary or Event Officer)."""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('accounts:login')
        if not request.user.can_approve_events:
            if _is_api_request(request):
                return JsonResponse({'error': 'Event approval access required'}, status=403)
            return render(request, '403.html', status=403)
        return view_func(request, *args, **kwargs)
    return wrapper


def secretary_required(view_func):
    """Require authenticated user with Secretary admin level (can manage members)."""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('accounts:login')
        if not request.user.can_manage_members:
            if _is_api_request(request):
                return JsonResponse({'error': 'Secretary access required'}, status=403)
            return render(request, '403.html', status=403)
        return view_func(request, *args, **kwargs)
    return wrapper
