from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.tokens import default_token_generator
from django.contrib.auth.forms import SetPasswordForm
from django.shortcuts import render, redirect
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.core.mail import send_mail
from django.conf import settings

from .forms import LoginForm, RegistrationForm
from .models import User


def login_view(request):
    """Email + password login."""
    if request.user.is_authenticated:
        return redirect(settings.LOGIN_REDIRECT_URL)

    form = LoginForm(request.POST or None)
    error = None

    if request.method == 'POST' and form.is_valid():
        user = authenticate(
            request,
            username=form.cleaned_data['email'],
            password=form.cleaned_data['password'],
        )
        if user is not None:
            login(request, user)
            next_url = request.GET.get('next', settings.LOGIN_REDIRECT_URL)
            return redirect(next_url)
        else:
            error = 'Invalid email or password.'

    return render(request, 'accounts/login.html', {
        'form': form,
        'error': error,
    })


def register_view(request):
    """Self-registration — creates a Member-role account."""
    if request.user.is_authenticated:
        return redirect(settings.LOGIN_REDIRECT_URL)

    form = RegistrationForm(request.POST or None)

    if request.method == 'POST' and form.is_valid():
        user = form.save()
        login(request, user, backend='accounts.backends.EmailBackend')
        return redirect(settings.LOGIN_REDIRECT_URL)

    return render(request, 'accounts/register.html', {
        'form': form,
    })


def logout_view(request):
    """Log out and redirect to login page."""
    logout(request)
    return redirect('accounts:login')


def password_reset_request_view(request):
    """Request a password reset email."""
    sent = False

    if request.method == 'POST':
        email = request.POST.get('email', '').strip().lower()
        try:
            user = User.objects.get(email__iexact=email)
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            token = default_token_generator.make_token(user)
            reset_url = request.build_absolute_uri(
                f'/accounts/password-reset/{uid}/{token}/'
            )
            send_mail(
                subject='GTYC — Password Reset',
                message=f'Click this link to reset your password:\n\n{reset_url}',
                from_email=None,  # uses DEFAULT_FROM_EMAIL
                recipient_list=[user.email],
                fail_silently=False,
            )
        except User.DoesNotExist:
            pass  # Don't reveal whether email exists
        sent = True

    return render(request, 'accounts/password_reset_request.html', {
        'sent': sent,
    })


def password_reset_confirm_view(request, uidb64, token):
    """Set a new password from a reset link."""
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None

    if user is None or not default_token_generator.check_token(user, token):
        return render(request, 'accounts/password_reset_confirm.html', {
            'valid': False,
        })

    form = SetPasswordForm(user, request.POST or None)

    if request.method == 'POST' and form.is_valid():
        form.save()
        login(request, user, backend='accounts.backends.EmailBackend')
        return redirect(settings.LOGIN_REDIRECT_URL)

    return render(request, 'accounts/password_reset_confirm.html', {
        'valid': True,
        'form': form,
    })
