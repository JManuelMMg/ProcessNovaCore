from django.urls import path
from . import views

app_name = 'finance'

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('invoices/', views.invoice_list, name='invoice_list'),
    path('invoices/<int:pk>/', views.invoice_detail, name='invoice_detail'),
    path('invoices/<int:pk>/stamp/', views.invoice_stamp, name='invoice_stamp'),
    path('invoices/<int:pk>/xml/', views.invoice_download_xml, name='invoice_download_xml'),
    path('invoices/from-sale/<int:sale_id>/', views.invoice_from_sale, name='invoice_from_sale'),
    path('incomes/', views.income_list, name='income_list'),
    path('expenses/', views.expense_list, name='expense_list'),
    path('api/stats/', views.api_finance_stats, name='api_finance_stats'),
]
