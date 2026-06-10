from django.urls import path
from . import views

app_name = 'crm'

urlpatterns = [
    path('', views.customer_list, name='customer_list'),
    path('customers/<int:pk>/', views.customer_detail, name='customer_detail'),
    path('customers/new/', views.customer_create, name='customer_create'),
    path('segments/', views.segment_list, name='segment_list'),
    path('interactions/', views.interaction_list, name='interaction_list'),
]
