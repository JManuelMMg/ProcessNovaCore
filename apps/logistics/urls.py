from django.urls import path
from . import views

app_name = 'logistics'

urlpatterns = [
    path('', views.order_list, name='order_list'),
    path('orders/new/', views.order_create, name='order_create'),
    path('orders/<int:pk>/', views.order_detail, name='order_detail'),
    path('orders/<int:pk>/fulfill/', views.order_fulfill, name='order_fulfill'),
    path('shipments/', views.shipment_list, name='shipment_list'),
    path('shipments/<int:pk>/', views.shipment_detail, name='shipment_detail'),
    path('shipments/<int:pk>/update-status/', views.update_shipment_status, name='update_shipment_status'),
    path('routes/', views.route_list, name='route_list'),
    path('carriers/', views.carrier_list, name='carrier_list'),
]
