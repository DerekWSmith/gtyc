import json

from django.contrib.auth import get_user_model
from django.db.models import Max, Q
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_POST, require_GET

from .decorators import secretary_required
from .models import MembershipType, AdminLevel, Title

User = get_user_model()


@secretary_required
def members_admin_page(request):
    """Member management page."""
    return render(request, 'accounts/admin.html', {
        'membership_types': MembershipType.choices,
        'admin_levels': AdminLevel.choices,
        'titles': Title.choices,
    })


@secretary_required
@require_GET
def api_member_list(request):
    """Return members as JSON with optional search/filter."""
    qs = User.objects.all().order_by('last_name', 'first_name')

    search = request.GET.get('search', '').strip()
    if search:
        qs = qs.filter(
            Q(first_name__icontains=search) |
            Q(last_name__icontains=search) |
            Q(email__icontains=search) |
            Q(preferred_name__icontains=search)
        )

    membership = request.GET.get('membership')
    if membership:
        types = [t.strip() for t in membership.split(',') if t.strip()]
        if len(types) == 1:
            qs = qs.filter(membership_type=types[0])
        elif types:
            qs = qs.filter(membership_type__in=types)

    if request.GET.get('committee') == 'true':
        qs = qs.filter(is_committee=True)

    if request.GET.get('rsa') == 'true':
        qs = qs.filter(is_rsa=True)

    if request.GET.get('rotation') == 'true':
        qs = qs.filter(is_in_rotation=True)

    if request.GET.get('inactive') == 'true':
        qs = qs.filter(is_active=False)
    else:
        qs = qs.filter(is_active=True)

    members = []
    for u in qs:
        members.append({
            'id': u.id,
            'email': u.email,
            'first_name': u.first_name,
            'last_name': u.last_name,
            'preferred_name': u.preferred_name,
            'display_name': u.display_name,
            'phone': u.phone,
            'membership_type': u.membership_type,
            'membership_display': u.get_membership_type_display(),
            'is_committee': u.is_committee,
            'admin_level': u.admin_level,
            'admin_display': u.get_admin_level_display() if u.admin_level else '',
            'title': u.title,
            'title_display': u.get_title_display() if u.title else '',
            'is_rsa': u.is_rsa,
            'is_in_rotation': u.is_in_rotation,
            'rotation_position': u.rotation_position,
            'is_active': u.is_active,
        })

    return JsonResponse({'members': members})


@secretary_required
@require_GET
def api_member_detail(request, user_id):
    """Return single member detail."""
    try:
        u = User.objects.get(pk=user_id)
    except User.DoesNotExist:
        return JsonResponse({'error': 'User not found'}, status=404)

    return JsonResponse({'member': {
        'id': u.id,
        'email': u.email,
        'first_name': u.first_name,
        'last_name': u.last_name,
        'preferred_name': u.preferred_name,
        'phone': u.phone,
        'membership_type': u.membership_type,
        'is_committee': u.is_committee,
        'admin_level': u.admin_level,
        'title': u.title,
        'is_rsa': u.is_rsa,
        'is_in_rotation': u.is_in_rotation,
        'rotation_position': u.rotation_position,
        'is_active': u.is_active,
    }})


@secretary_required
@require_POST
def api_member_create(request):
    """Create a new user/contact."""
    try:
        body = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    email = body.get('email', '').strip().lower()
    if not email:
        return JsonResponse({'error': 'Email is required'}, status=400)
    if User.objects.filter(email__iexact=email).exists():
        return JsonResponse({'error': 'A user with this email already exists'}, status=400)

    user = User.objects.create_user(
        email=email,
        first_name=body.get('first_name', '').strip(),
        last_name=body.get('last_name', '').strip(),
        preferred_name=body.get('preferred_name', '').strip(),
        phone=body.get('phone', '').strip(),
        membership_type=body.get('membership_type', 'full'),
        is_committee=body.get('is_committee', False),
        admin_level=body.get('admin_level', ''),
        title=body.get('title', ''),
        is_rsa=body.get('is_rsa', False),
        is_in_rotation=body.get('is_in_rotation', False),
    )

    # Auto-set rotation position if adding to rotation
    if user.is_in_rotation:
        max_pos = User.objects.filter(
            is_in_rotation=True,
        ).exclude(pk=user.pk).aggregate(m=Max('rotation_position'))['m'] or 0
        user.rotation_position = max_pos + 1
        user.is_rsa = True  # Rotation implies RSA
        user.save()

    return JsonResponse({'success': True, 'id': user.id})


@secretary_required
@require_POST
def api_member_update(request, user_id):
    """Update an existing user."""
    try:
        user = User.objects.get(pk=user_id)
    except User.DoesNotExist:
        return JsonResponse({'error': 'User not found'}, status=404)

    try:
        body = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    # Update simple fields
    for field in ['first_name', 'last_name', 'preferred_name', 'phone',
                  'membership_type', 'is_committee', 'admin_level', 'title',
                  'is_rsa', 'is_active']:
        if field in body:
            setattr(user, field, body[field])

    # Email update with uniqueness check
    if 'email' in body:
        new_email = body['email'].strip().lower()
        if new_email != user.email and User.objects.filter(email__iexact=new_email).exists():
            return JsonResponse({'error': 'Email already in use'}, status=400)
        user.email = new_email

    # Handle rotation toggle
    was_in_rotation = user.is_in_rotation
    if 'is_in_rotation' in body:
        user.is_in_rotation = body['is_in_rotation']

    if user.is_in_rotation and not was_in_rotation:
        # Adding to rotation
        max_pos = User.objects.filter(
            is_in_rotation=True,
        ).exclude(pk=user.pk).aggregate(m=Max('rotation_position'))['m'] or 0
        user.rotation_position = max_pos + 1
        user.is_rsa = True  # Rotation implies RSA
    elif not user.is_in_rotation and was_in_rotation:
        # Removing from rotation
        user.rotation_position = None

    user.save()
    return JsonResponse({'success': True})
