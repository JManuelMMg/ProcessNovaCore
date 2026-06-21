from django.urls import path
from . import views

app_name = 'inventory'

urlpatterns = [
    path('', views.product_list, name='product_list'),
    path('products/<int:pk>/', views.product_detail, name='product_detail'),
    path('products/new/', views.product_create, name='product_create'),
    path('products/<int:pk>/edit/', views.product_edit, name='product_edit'),
    path('categories/', views.category_list, name='category_list'),
    path('categories/new/', views.category_create, name='category_create'),
    path('api/create-category/', views.api_create_category, name='api_create_category'),
    path('stocks/', views.stock_list, name='stock_list'),
    path('intake/', views.stock_intake, name='stock_intake'),
    path('movements/', views.movement_list, name='movement_list'),
    path('low-stock/', views.low_stock_alerts, name='low_stock_alerts'),
    path('api/quick-create/', views.api_quick_create, name='api_quick_create'),
    path('api/add-stock/', views.api_add_stock, name='api_add_stock'),
    path('api/low-stock/', views.api_low_stock, name='api_low_stock'),
]
