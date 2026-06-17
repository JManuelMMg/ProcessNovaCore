from django.urls import path
from . import views

app_name = 'logistics'

urlpatterns = [
    path('', views.shipment_list, name='shipment_list'),
    path('shipments/<int:pk>/', views.shipment_detail, name='shipment_detail'),
    path('shipments/<int:pk>/update-status/', views.update_shipment_status, name='update_shipment_status'),
    path('routes/', views.route_list, name='route_list'),
    path('carriers/', views.carrier_list, name='carrier_list'),
    path('orders/', views.order_list, name='order_list'),
]
