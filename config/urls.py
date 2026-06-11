"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from core import views
from apps.users import views as user_views
from core.auth_views import SafePasswordResetView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('sw.js', views.serve_sw, name='sw'),
    path('manifest.json', views.serve_manifest, name='manifest'),
    path('', views.landing_page, name='landing'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('profile/', user_views.user_profile, name='user_profile'),
    path('password-change/', 
         auth_views.PasswordChangeView.as_view(
             template_name='registration/password_change_form.html',
             success_url='/profile/'
         ), 
         name='password_change'),
    path('login/', auth_views.LoginView.as_view(template_name='registration/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('register/', views.register, name='register'),
    # Recuperación de usuario
    path('username-recovery/', views.username_recovery, name='username_recovery'),
    path('username-recovery/done/', views.username_recovery_done, name='username_recovery_done'),
    # Recuperación de contraseña (con manejo seguro de errores)
    path('password-reset/', 
         SafePasswordResetView.as_view(
             template_name='registration/password_reset_form.html',
             email_template_name='registration/password_reset_email.html',
             subject_template_name='registration/password_reset_subject.txt'
         ), 
         name='password_reset'),
    path('password-reset/done/', 
         auth_views.PasswordResetDoneView.as_view(
             template_name='registration/password_reset_done.html'
         ), 
         name='password_reset_done'),
    path('reset/<uidb64>/<token>/', 
         auth_views.PasswordResetConfirmView.as_view(
             template_name='registration/password_reset_confirm.html'
         ), 
         name='password_reset_confirm'),
    path('reset/done/', 
         auth_views.PasswordResetCompleteView.as_view(
             template_name='registration/password_reset_complete.html'
         ), 
         name='password_reset_complete'),
    path('ai/', include('apps.ai_engine.urls', namespace='ai_engine')),
    path('inventory/', include('apps.inventory.urls', namespace='inventory')),
    path('crm/', include('apps.crm.urls', namespace='crm')),
    path('finance/', include('apps.finance.urls', namespace='finance')),
    path('hr/', include('apps.hr.urls', namespace='hr')),
    path('logistics/', include('apps.logistics.urls', namespace='logistics')),
    path('notifications/', include('apps.notifications.urls', namespace='notifications')),
    path('sales/', include('apps.sales.urls', namespace='sales')),
    path('users/', include('apps.users.urls', namespace='users')),
]

# Servir media files solo en desarrollo
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
