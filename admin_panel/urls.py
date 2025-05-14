from django.urls import path
from . import views

app_name = 'admin_panel'

urlpatterns = [
    # Dashboard
    path('dashboard/', views.admin_dashboard, name='dashboard'),
    
    # User Management
    path('users/', views.admin_users, name='users'),
    path('users/<int:user_id>/', views.admin_user_detail, name='user_detail'),
    path('users/edit/', views.admin_user_edit, name='user_edit'),
    path('users/<int:user_id>/activate/', views.admin_user_activate, name='user_activate'),
    path('users/<int:user_id>/deactivate/', views.admin_user_deactivate, name='user_deactivate'),
    path('users/<int:user_id>/adjust-balance/', views.admin_adjust_balance, name='adjust_balance'),
    path('users/export/', views.admin_export_users, name='export_users'),
    path('users/<int:user_id>/orders/', views.admin_user_orders, name='user_orders'),
    path('users/<int:user_id>/transactions/', views.admin_user_transactions, name='user_transactions'),
    
    # Service Management
    path('services/', views.admin_services, name='services'),
    path('services/<int:service_id>/', views.admin_service_detail, name='service_detail'),
    path('services/edit/', views.admin_service_edit, name='service_edit'),
    path('services/toggle/', views.admin_service_toggle, name='service_toggle'),
    path('services/export/', views.admin_export_services, name='export_services'),
    path('services/sync/', views.sync_services_manual, name='sync_services_manual'),
    
    # Order Management
    path('orders/', views.admin_orders, name='orders'),
    path('orders/<int:order_id>/', views.admin_order_detail, name='order_detail'),
    path('orders/update-status/', views.admin_order_update_status, name='order_update_status'),
    path('orders/export/', views.admin_export_orders, name='export_orders'),
    path('orders/update/', views.update_orders_manual, name='update_orders_manual'),
    path('orders/<int:order_id>/add-note/', views.admin_order_add_note, name='order_add_note'),
    
    # Transactions Management
    path('transactions/', views.admin_transactions, name='transactions'),
    path('transactions/export/', views.admin_export_transactions, name='export_transactions'),
    
    # Settings Management
    path('settings/', views.admin_settings, name='settings'),
    path('settings/save/', views.admin_save_settings, name='save_settings'),
    
    # Provider Payments
    path('provider/payment/', views.record_provider_payment, name='record_provider_payment'),
    path('provider/payment/history/', views.provider_payment_history, name='provider_payment_history'),
    
    # API Management
    path('api/check-balance/', views.admin_check_balance, name='check_balance'),
    path('api/test-connection/', views.test_api_connection, name='test_api_connection'),
    
    # Markup Management
    path('markup/adjust/', views.adjust_markup, name='adjust_markup'),
]
