from django.urls import path
from . import views

app_name = 'sales'

urlpatterns = [
    path('pos/', views.pos_view, name='pos'),
    path('history/', views.sale_list, name='sale_list'),
    path('history/<int:pk>/', views.sale_detail, name='sale_detail'),
    path('api/add-to-cart/', views.api_add_to_cart, name='api_add_to_cart'),
    path('api/remove-from-cart/', views.api_remove_from_cart, name='api_remove_from_cart'),
    path('api/get-cart/', views.api_get_cart, name='api_get_cart'),
    path('api/clear-cart/', views.api_clear_cart, name='api_clear_cart'),
    path('api/checkout/', views.api_checkout, name='api_checkout'),
    path('api/scan-product/', views.api_scan_product, name='api_scan_product'),
    path('api/switch-branch/', views.api_switch_branch, name='api_switch_branch'),
    path('api/products-cache/', views.api_products_cache, name='api_products_cache'),
    path('api/sync-offline/', views.api_sync_offline, name='api_sync_offline'),
]
