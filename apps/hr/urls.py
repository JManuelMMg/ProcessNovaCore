from django.urls import path
from . import views

app_name = 'hr'

urlpatterns = [
    path('', views.employee_list, name='employee_list'),
    path('employees/create/', views.employee_create, name='employee_create'),
    path('employees/<int:pk>/', views.employee_detail, name='employee_detail'),
    path('employees/<int:pk>/edit/', views.employee_edit, name='employee_edit'),
    path('departments/', views.department_list, name='department_list'),
    path('analytics/', views.hr_analytics, name='hr_analytics'),
    path('api/stats/', views.api_hr_stats, name='api_hr_stats'),
]
