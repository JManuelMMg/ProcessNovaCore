from django.urls import path
from . import views

app_name = 'crm'

urlpatterns = [
    path('', views.customer_list, name='customer_list'),
    path('customers/new/', views.customer_create, name='customer_create'),
    path('customers/<int:pk>/', views.customer_detail, name='customer_detail'),
    path('customers/<int:pk>/edit/', views.customer_edit, name='customer_edit'),
    path('customers/<int:pk>/delete/', views.customer_delete, name='customer_delete'),
    
    path('leads/', views.lead_list, name='lead_list'),
    path('leads/new/', views.lead_create, name='lead_create'),
    path('leads/<int:pk>/', views.lead_detail, name='lead_detail'),
    
    path('opportunities/', views.opportunity_list, name='opportunity_list'),
    path('opportunities/new/', views.opportunity_create, name='opportunity_create'),
    
    path('campaigns/', views.campaign_list, name='campaign_list'),
    path('campaigns/new/', views.campaign_create, name='campaign_create'),
    
    path('segments/', views.segment_list, name='segment_list'),
    path('segments/new/', views.segment_create, name='segment_create'),
    
    path('interactions/', views.interaction_list, name='interaction_list'),
    path('interactions/new/', views.interaction_create, name='interaction_create'),

    path('analytics/', views.crm_analytics, name='crm_analytics'),
    path('api/stats/', views.api_crm_stats, name='api_crm_stats'),
]
