from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login
from django.contrib import messages
from django.db import transaction
from django.utils import timezone
import logging

logger = logging.getLogger(__name__)

from core.permissions import permission_required, tenant_required
from .models import User, Membership, Branch, UserInvitation
from .forms import UserInviteForm, BranchForm, EmailInviteForm, AcceptInviteForm
from .emails import send_user_invitation


@login_required
@tenant_required
@permission_required('users_manage')
def user_list(request):
    memberships = Membership.objects.filter(
        organization=request.organization
    ).select_related('user', 'branch')
    pending_invites = UserInvitation.objects.filter(
        organization=request.organization, accepted=False
    )
    return render(request, 'users/user_list.html', {
        'memberships': memberships,
        'pending_invites': pending_invites,
    })


@login_required
@tenant_required
@permission_required('users_manage')
def user_create(request):
    if request.method == 'POST':
        form = UserInviteForm(request.POST, organization=request.organization)
        if form.is_valid():
            user = form.save()
            Membership.objects.create(
                user=user,
                organization=request.organization,
                role=form.cleaned_data['role'],
                branch=form.cleaned_data.get('branch'),
            )
            messages.success(request, f'Usuario "{user.username}" creado correctamente.')
            return redirect('users:user_list')
    else:
        form = UserInviteForm(organization=request.organization)
    return render(request, 'users/user_form.html', {'form': form})


@login_required
@tenant_required
@permission_required('users_manage')
def user_invite(request):
    if request.method == 'POST':
        form = EmailInviteForm(request.POST, organization=request.organization)
        if form.is_valid():
            invitation = form.save(commit=False)
            invitation.organization = request.organization
            invitation.invited_by = request.user
            invitation.save()
            try:
                send_user_invitation(invitation, request)
                messages.success(request, f'Invitación enviada a {invitation.email}')
            except Exception as e:
                messages.warning(
                    request,
                    f'Invitación creada pero el correo no se pudo enviar: {e}. '
                    f'Comparte este enlace: /users/invite/accept/{invitation.token}/'
                )
            return redirect('users:user_list')
    else:
        form = EmailInviteForm(organization=request.organization)
    return render(request, 'users/invite_form.html', {'form': form})


@transaction.atomic
def accept_invite(request, token):
    invitation = get_object_or_404(UserInvitation, token=token)
    if not invitation.is_valid:
        return render(request, 'users/invite_expired.html', {'invitation': invitation})

    if request.method == 'POST':
        form = AcceptInviteForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.email = invitation.email
            user.first_name = invitation.first_name
            user.last_name = invitation.last_name
            user.save()
            Membership.objects.create(
                user=user,
                organization=invitation.organization,
                role=invitation.role,
                branch=invitation.branch,
            )
            invitation.accepted = True
            invitation.accepted_at = timezone.now()  # Bug 4 fix: registrar fecha de aceptación
            invitation.save()
            login(request, user)
            messages.success(request, f'¡Bienvenido a {invitation.organization.name}!')
            return redirect('dashboard')
    else:
        form = AcceptInviteForm(initial={'username': invitation.email.split('@')[0]})

    return render(request, 'users/accept_invite.html', {
        'form': form,
        'invitation': invitation,
    })


@login_required
@tenant_required
@permission_required('branches_manage')
def branch_list(request):
    branches = Branch.objects.for_org(request.organization)
    return render(request, 'users/branch_list.html', {'branches': branches})


@login_required
@tenant_required
@permission_required('branches_manage')
def branch_create(request):
    if request.method == 'POST':
        form = BranchForm(request.POST)
        if form.is_valid():
            branch = form.save(commit=False)
            branch.organization = request.organization
            if branch.is_main:
                Branch.objects.filter(
                    organization=request.organization, is_main=True
                ).update(is_main=False)
            branch.save()
            messages.success(request, f'Sucursal "{branch.name}" creada.')
            return redirect('users:branch_list')
    else:
        form = BranchForm()
    return render(request, 'users/branch_form.html', {'form': form})


@login_required
@tenant_required
@permission_required('branches_manage')
def branch_switch(request):
    if request.method == 'POST':
        branch_id = request.POST.get('branch_id')
        branch = get_object_or_404(
            Branch.objects.for_org(request.organization),
            id=branch_id,
        )
        request.session['active_branch_id'] = branch.id
        request.session.pop('current_sale', None)
        messages.success(request, f'Sucursal activa: {branch.name}')
    return redirect(request.META.get('HTTP_REFERER', 'dashboard'))


@login_required
@tenant_required
@permission_required('users_manage')
def user_edit(request, user_id):
    """Editar rol y sucursal de un miembro del equipo."""
    membership = get_object_or_404(
        Membership.objects.select_related('user', 'branch'),
        user_id=user_id,
        organization=request.organization,
    )
    if request.method == 'POST':
        new_role = request.POST.get('role')
        new_branch_id = request.POST.get('branch')
        valid_roles = [r[0] for r in Membership.ROLE_CHOICES]
        if new_role not in valid_roles:
            messages.error(request, 'Rol inválido.')
            return redirect('users:user_list')
        membership.role = new_role
        if new_branch_id:
            branch = Branch.objects.for_org(request.organization).filter(id=new_branch_id).first()
            membership.branch = branch
        else:
            membership.branch = None
        membership.save()
        messages.success(request, f'Usuario "{membership.user.username}" actualizado.')
        return redirect('users:user_list')

    branches = Branch.objects.for_org(request.organization).filter(is_active=True)
    return render(request, 'users/user_edit.html', {
        'membership': membership,
        'branches': branches,
        'role_choices': Membership.ROLE_CHOICES,
    })


@login_required
@tenant_required
@permission_required('users_manage')
def user_deactivate(request, user_id):
    """Activar / desactivar un miembro del equipo."""
    membership = get_object_or_404(
        Membership, user_id=user_id, organization=request.organization
    )
    if membership.user == request.user:
        messages.error(request, 'No puedes desactivarte a ti mismo.')
        return redirect('users:user_list')
    membership.is_active = not membership.is_active
    membership.save()
    estado = 'activado' if membership.is_active else 'desactivado'
    messages.success(request, f'Usuario "{membership.user.username}" {estado}.')
    return redirect('users:user_list')


@login_required
@tenant_required
@permission_required('users_manage')
def invitation_revoke(request, invitation_id):
    """Revocar una invitación pendiente."""
    invitation = get_object_or_404(
        UserInvitation, id=invitation_id, organization=request.organization, accepted=False
    )
    invitation.delete()
    messages.success(request, f'Invitación a {invitation.email} revocada.')
    return redirect('users:user_list')


@login_required
@tenant_required
@permission_required('branches_manage')
def branch_edit(request, branch_id):
    """Editar una sucursal existente."""
    branch = get_object_or_404(
        Branch.objects.for_org(request.organization), id=branch_id
    )
    if request.method == 'POST':
        form = BranchForm(request.POST, instance=branch)
        if form.is_valid():
            b = form.save(commit=False)
            if b.is_main:
                Branch.objects.filter(
                    organization=request.organization, is_main=True
                ).exclude(id=branch.id).update(is_main=False)
            b.save()
            messages.success(request, f'Sucursal "{b.name}" actualizada.')
            return redirect('users:branch_list')
    else:
        form = BranchForm(instance=branch)
    return render(request, 'users/branch_form.html', {'form': form, 'branch': branch})


@login_required
def user_profile(request):
    """Ver y editar el perfil del usuario autenticado."""
    from apps.users.models import User as UserModel
    user_obj = request.user
    if request.method == 'POST':
        first_name = request.POST.get('first_name', '').strip()
        last_name = request.POST.get('last_name', '').strip()
        email = request.POST.get('email', '').strip()
        phone = request.POST.get('phone', '').strip()
        user_obj.first_name = first_name
        user_obj.last_name = last_name
        user_obj.email = email
        user_obj.phone = phone
        user_obj.save()
        messages.success(request, 'Perfil actualizado correctamente.')
        return redirect('user_profile')
    return render(request, 'users/user_profile.html', {'profile_user': user_obj})
