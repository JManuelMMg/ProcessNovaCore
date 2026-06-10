from django.urls import path
from . import views

app_name = 'logistics'

urlpatterns = [
    path('', views.shipment_list, name='shipment_list'),
    path('shipments/<int:pk>/', views.shipment_detail, name='shipment_detail'),
    path('vehicles/', views.vehicle_list, name='vehicle_list'),
]
