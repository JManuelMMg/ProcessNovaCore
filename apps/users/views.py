from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login
from django.contrib import messages
from django.db import transaction

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
