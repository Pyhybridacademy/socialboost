from django.urls import path, reverse_lazy
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    # Main pages
    path('', views.index, name='index'),
    path('services/', views.services, name='services'),
    path('services/categories/', views.services_by_category, name='services_by_category'),
    path('service/<int:service_id>/', views.service_detail, name='service_detail'),
    
    # Order related
    path('order/create/', views.create_order, name='create_order'),
    path('order/status/', views.order_status, name='order_status'),
    path('order/status/<int:order_id>/', views.order_status, name='order_status'),
    path('order/confirmation/<int:order_id>/', views.order_confirmation, name='order_confirmation'),
    
    # User account
    path('dashboard/', views.dashboard, name='dashboard'),
    path('profile/', views.profile, name='profile'),
    path('add-funds/', views.add_funds, name='add_funds'),
    path('process-payment/', views.process_payment, name='process_payment'),
    path('paystack/callback/', views.paystack_callback, name='paystack_callback'),
    
    # Authentication
    path('register/', views.register, name='register'),
    path('login/', views.user_login, name='login'),
    path('logout/', views.user_logout, name='logout'), 
    
 path('password-reset/',
        auth_views.PasswordResetView.as_view(
            template_name='registration/password_reset.html',
            email_template_name='registration/password_reset_email.html',
            subject_template_name='registration/password_reset_subject.txt',
            success_url=reverse_lazy('password_reset_done')
        ),
        name='password_reset'),
    
    path('password-reset/done/',
        auth_views.PasswordResetDoneView.as_view(
            template_name='registration/password_reset_done.html'
        ),
        name='password_reset_done'),
    
    path('password-reset-confirm/<uidb64>/<token>/',
        auth_views.PasswordResetConfirmView.as_view(
            template_name='registration/password_reset_confirm.html',
            success_url=reverse_lazy('password_reset_complete')
        ),
        name='password_reset_confirm'),
    
    path('password-reset-complete/',
        auth_views.PasswordResetCompleteView.as_view(
            template_name='registration/password_reset_complete.html'
        ),
        name='password_reset_complete'),
              
]




    