from django.urls import path
from . import views

app_name = 'users'

urlpatterns = [
    path('team/', views.user_list, name='user_list'),
    path('team/new/', views.user_create, name='user_create'),
    path('team/invite/', views.user_invite, name='user_invite'),
    path('team/<int:user_id>/edit/', views.user_edit, name='user_edit'),
    path('team/<int:user_id>/deactivate/', views.user_deactivate, name='user_deactivate'),
    path('invite/accept/<uuid:token>/', views.accept_invite, name='accept_invite'),
    path('invite/<int:invitation_id>/revoke/', views.invitation_revoke, name='invitation_revoke'),
    path('branches/', views.branch_list, name='branch_list'),
    path('branches/new/', views.branch_create, name='branch_create'),
    path('branches/<int:branch_id>/edit/', views.branch_edit, name='branch_edit'),
    path('branches/switch/', views.branch_switch, name='branch_switch'),
]
