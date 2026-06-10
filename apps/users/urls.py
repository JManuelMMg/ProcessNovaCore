from django.urls import path
from . import views

app_name = 'users'

urlpatterns = [
    path('team/', views.user_list, name='user_list'),
    path('team/new/', views.user_create, name='user_create'),
    path('team/invite/', views.user_invite, name='user_invite'),
    path('invite/accept/<uuid:token>/', views.accept_invite, name='accept_invite'),
    path('branches/', views.branch_list, name='branch_list'),
    path('branches/new/', views.branch_create, name='branch_create'),
    path('branches/switch/', views.branch_switch, name='branch_switch'),
]
