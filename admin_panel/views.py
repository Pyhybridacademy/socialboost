from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib import messages
from django.conf import settings
from django.http import JsonResponse, HttpResponse
from django.db.models import Sum, Q, Count
from django.utils import timezone
from django.views.decorators.http import require_POST
from django.contrib.auth.models import User
from django.core.paginator import Paginator
from django.urls import reverse
from decimal import Decimal
import csv
import json
import logging

from core.models import Order, Transaction, Service, UserBalance, SiteSettings, ProviderPayment
from core.api_client import SocialMediaAPI

logger = logging.getLogger(__name__)

@staff_member_required
def admin_dashboard(request):
    # Get total customer payments
    total_customer_payments = Transaction.objects.filter(
        transaction_type='deposit'
    ).aggregate(Sum('amount'))['amount__sum'] or Decimal('0.00')
    
    # Get total orders
    total_orders = Order.objects.filter(
        status__in=['completed', 'processing', 'pending']
    )
    
    # Get site settings for markup calculation
    site_settings = SiteSettings.get_settings()
    markup_multiplier = (Decimal('100') + site_settings.markup_percentage) / Decimal('100')
    
    total_wholesale_cost = Decimal('0.00')
    total_retail_value = Decimal('0.00')
    
    for order in total_orders:
        # Use charge consistently
        wholesale_price = (order.charge / markup_multiplier).quantize(Decimal('0.01'))
        total_wholesale_cost += wholesale_price
        total_retail_value += order.charge
    
    # Calculate profit
    profit = total_retail_value - total_wholesale_cost
    
    # Get recent orders
    recent_orders = Order.objects.all().order_by('-created_at')[:10]
    
    # Get recent transactions
    recent_transactions = Transaction.objects.all().order_by('-created_at')[:10]
    
    # Get current admin balance
    admin_balance = total_customer_payments - total_wholesale_cost
    
    # Get order statistics
    order_stats = {
        'total': Order.objects.count(),
        'pending': Order.objects.filter(status='pending').count(),
        'processing': Order.objects.filter(status='processing').count(),
        'completed': Order.objects.filter(status='completed').count(),
        'canceled': Order.objects.filter(status='canceled').count(),
        'error': Order.objects.filter(status='error').count(),
    }
    
    # Get payments to provider
    provider_payments = ProviderPayment.objects.filter(
        status='completed'
    ).aggregate(Sum('amount'))['amount__sum'] or Decimal('0.00')
    
    # Calculate amount owed to provider
    amount_owed_to_provider = total_wholesale_cost - provider_payments
    
    context = {
        'total_customer_payments': total_customer_payments,
        'total_wholesale_cost': total_wholesale_cost,
        'total_retail_value': total_retail_value,
        'profit': profit,
        'recent_orders': recent_orders,
        'recent_transactions': recent_transactions,
        'admin_balance': admin_balance,
        'order_stats': order_stats,
        'provider_payments': provider_payments,
        'amount_owed_to_provider': amount_owed_to_provider,
    }
    
    return render(request, 'admin_panel/dashboard.html', context)

@staff_member_required
def admin_users(request):
    # Get all users
    users_list = User.objects.all().order_by('-date_joined')
    
    # Handle search
    search_query = request.GET.get('search', '')
    if search_query:
        users_list = users_list.filter(
            Q(username__icontains=search_query) | 
            Q(email__icontains=search_query) |
            Q(first_name__icontains=search_query) |
            Q(last_name__icontains=search_query)
        )
    
    # Pagination
    paginator = Paginator(users_list, 20)  # Show 20 users per page
    page = request.GET.get('page', 1)
    
    try:
        page = int(page)
        if page < 1:  # Corrected here
            page = 1
    except ValueError:
        page = 1
    
    try:
        users = paginator.page(page)
    except:
        # If the page is out of range, deliver the last page
        users = paginator.page(paginator.num_pages)
    
    # Get user balances
    user_balances = {}
    for user in users:
        balance = UserBalance.objects.get_or_create(user=user)[0]
        user_balances[user.id] = balance.balance
    
    context = {
        'users': users,
        'user_balances': user_balances,
        'search_query': search_query,
    }
    
    return render(request, 'admin_panel/users.html', context)

@staff_member_required
def admin_user_detail(request, user_id):
    user = get_object_or_404(User, id=user_id)
    user_balance = UserBalance.objects.get_or_create(user=user)[0]
    
    # Get user's orders
    orders = Order.objects.filter(user=user).order_by('-created_at')[:10]
    
    # Get user's transactions
    transactions = Transaction.objects.filter(user=user).order_by('-created_at')[:10]
    
    # Calculate statistics
    total_orders = Order.objects.filter(user=user).count()
    completed_orders = Order.objects.filter(user=user, status='completed').count()
    total_spent = Order.objects.filter(user=user).aggregate(Sum('charge'))['charge__sum'] or 0
    
    context = {
        'user_detail': user,
        'user_balance': user_balance,
        'orders': orders,
        'transactions': transactions,
        'total_orders': total_orders,
        'completed_orders': completed_orders,
        'total_spent': total_spent,
    }
    
    return render(request, 'admin_panel/user_detail.html', context)

@staff_member_required
@require_POST
def admin_user_edit(request):
    user_id = request.POST.get('user_id')
    user = get_object_or_404(User, id=user_id)
    
    # Update user information
    user.username = request.POST.get('username', user.username)
    user.email = request.POST.get('email', user.email)
    user.first_name = request.POST.get('first_name', user.first_name)
    user.last_name = request.POST.get('last_name', user.last_name)
    
    # Handle password change if provided
    new_password = request.POST.get('new_password', '')
    if new_password:
        user.set_password(new_password)
    
    user.save()
    
    messages.success(request, f"User {user.username} updated successfully!")
    return redirect('admin_panel:user_detail', user_id=user.id)

@staff_member_required
def admin_user_activate(request, user_id):
    user = get_object_or_404(User, id=user_id)
    user.is_active = True
    user.save()
    
    messages.success(request, f"User {user.username} activated successfully!")
    return redirect('admin_panel:user_detail', user_id=user.id)

@staff_member_required
def admin_user_deactivate(request, user_id):
    user = get_object_or_404(User, id=user_id)
    user.is_active = False
    user.save()
    
    messages.success(request, f"User {user.username} deactivated successfully!")
    return redirect('admin_panel:user_detail', user_id=user.id)

@staff_member_required
@require_POST
def admin_adjust_balance(request, user_id):
    user = get_object_or_404(User, id=user_id)
    user_balance = UserBalance.objects.get_or_create(user=user)[0]
    
    amount_str = request.POST.get('amount', '0')
    description = request.POST.get('description', 'Balance adjustment by admin')
    
    try:
        amount = Decimal(amount_str)
    except:
        messages.error(request, "Invalid amount format")
        return redirect('admin_panel:user_detail', user_id=user.id)
    
    # Update user balance
    user_balance.balance += amount
    user_balance.save()
    
    # Record the transaction
    transaction_type = 'deposit' if amount > 0 else 'withdrawal'
    Transaction.objects.create(
        user=user,
        amount=abs(amount),
        transaction_type=transaction_type,
        description=description
    )
    
    messages.success(request, f"Balance adjusted by ₦{amount} for {user.username}")
    return redirect('admin_panel:user_detail', user_id=user.id)

@staff_member_required
def admin_export_users(request):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="users.csv"'
    
    writer = csv.writer(response)
    writer.writerow(['ID', 'Username', 'Email', 'First Name', 'Last Name', 'Date Joined', 'Last Login', 'Active', 'Balance'])
    
    users = User.objects.all().order_by('-date_joined')
    
    for user in users:
        user_balance = UserBalance.objects.get_or_create(user=user)[0]
        writer.writerow([
            user.id,
            user.username,
            user.email,
            user.first_name,
            user.last_name,
            user.date_joined,
            user.last_login,
            user.is_active,
            user_balance.balance
        ])
    
    return response

@staff_member_required
def admin_user_orders(request, user_id):
    user = get_object_or_404(User, id=user_id)
    orders = Order.objects.filter(user=user).order_by('-created_at')
    
    # Pagination
    paginator = Paginator(orders, 20)  # Show 20 orders per page
    page = request.GET.get('page')
    orders_page = paginator.get_page(page)
    
    context = {
        'user_detail': user,
        'orders': orders_page,
    }
    
    return render(request, 'admin_panel/user_orders.html', context)

@staff_member_required
def admin_user_transactions(request, user_id):
    user = get_object_or_404(User, id=user_id)
    transactions = Transaction.objects.filter(user=user).order_by('-created_at')
    
    # Pagination
    paginator = Paginator(transactions, 20)  # Show 20 transactions per page
    page = request.GET.get('page')
    transactions_page = paginator.get_page(page)
    
    context = {
        'user_detail': user,
        'transactions': transactions_page,
    }
    
    return render(request, 'admin_panel/user_transactions.html', context)

@staff_member_required
def admin_services(request):
    # Get all services
    services_list = Service.objects.all().order_by('-id')
    
    # Handle search
    search_query = request.GET.get('search', '')
    if search_query:
        services_list = services_list.filter(
            Q(name__icontains=search_query) | 
            Q(description__icontains=search_query) |
            Q(category__icontains=search_query)
        )
    
    # Handle category filter
    selected_category = request.GET.get('category', '')
    if selected_category:
        services_list = services_list.filter(category=selected_category)
    
    # Get all unique categories for the filter dropdown
    categories = Service.objects.values_list('category', flat=True).distinct()
    
    # Pagination
    paginator = Paginator(services_list, 20)  # Show 20 services per page
    page = request.GET.get('page')
    services = paginator.get_page(page)
    
    context = {
        'services': services,
        'categories': categories,
        'selected_category': selected_category,
        'search_query': search_query,
    }
    
    return render(request, 'admin_panel/services.html', context)

@staff_member_required
def admin_service_detail(request, service_id):
    service = get_object_or_404(Service, id=service_id)
    
    # Get orders for this service
    orders = Order.objects.filter(service=service).order_by('-created_at')[:10]
    
    # Calculate statistics
    total_orders = Order.objects.filter(service=service).count()
    completed_orders = Order.objects.filter(service=service, status='completed').count()
    total_revenue = Order.objects.filter(service=service).aggregate(Sum('charge'))['charge__sum'] or 0
    
    context = {
        'service': service,
        'orders': orders,
        'total_orders': total_orders,
        'completed_orders': completed_orders,
        'total_revenue': total_revenue,
    }
    
    return render(request, 'admin_panel/service_detail.html', context)

@staff_member_required
@require_POST
def admin_service_edit(request):
    service_id = request.POST.get('service_id')
    service = get_object_or_404(Service, id=service_id)
    
    # Update service information
    service.name = request.POST.get('name', service.name)
    service.description = request.POST.get('description', service.description)
    service.category = request.POST.get('category', service.category)
    
    try:
        service.rate = Decimal(request.POST.get('rate', service.rate))
        service.min_quantity = int(request.POST.get('min_quantity', service.min_quantity))
        service.max_quantity = int(request.POST.get('max_quantity', service.max_quantity))
    except:
        messages.error(request, "Invalid number format for rate or quantity")
        return redirect('admin_panel:service_detail', service_id=service.id)
    
    service.save()
    
    messages.success(request, f"Service {service.name} updated successfully!")
    return redirect('admin_panel:service_detail', service_id=service.id)

@staff_member_required
@require_POST
def admin_service_toggle(request):
    service_id = request.POST.get('service_id')
    service = get_object_or_404(Service, id=service_id)
    
    service.is_active = not service.is_active
    service.save()
    
    status = "activated" if service.is_active else "deactivated"
    messages.success(request, f"Service {service.name} {status} successfully!")
    
    return redirect('admin_panel:service_detail', service_id=service.id)

@staff_member_required
def admin_export_services(request):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="services.csv"'
    
    writer = csv.writer(response)
    writer.writerow(['ID', 'Service ID', 'Name', 'Description', 'Category', 'Rate', 'Min Quantity', 'Max Quantity', 'Active'])
    
    services = Service.objects.all().order_by('-id')
    
    for service in services:
        writer.writerow([
            service.id,
            service.service_id,
            service.name,
            service.description,
            service.category,
            service.rate,
            service.min_quantity,
            service.max_quantity,
            service.is_active
        ])
    
    return response

@staff_member_required
def sync_services_manual(request):
    try:
        api = SocialMediaAPI(settings.API_KEY)
        response = api.get_services()
        
        if 'error' in response:
            messages.error(request, f"Error syncing services: {response['error']}")
            return redirect('admin_panel:services')
        
        # Get site settings for markup calculation
        site_settings = SiteSettings.get_settings()
        markup_multiplier = (Decimal('100') + site_settings.markup_percentage) / Decimal('100')
        
        # Process services
        services_added = 0
        services_updated = 0
        
        for service_data in response:
            service_id = service_data.get('service')
            
            if not service_id:
                continue
            
            # Try to find existing service
            try:
                service = Service.objects.get(service_id=service_id)
                # Update existing service
                service.name = service_data.get('name', service.name)
                service.category = service_data.get('category', service.category)
                service.description = service_data.get('description', service.description)
                
                # Apply markup to rate
                original_rate = Decimal(str(service_data.get('rate', 0)))
                service.rate = (original_rate * markup_multiplier).quantize(Decimal('0.01'))
                
                service.min_quantity = service_data.get('min', service.min_quantity)
                service.max_quantity = service_data.get('max', service.max_quantity)
                
                service.save()
                services_updated += 1
            except Service.DoesNotExist:
                # Create new service
                original_rate = Decimal(str(service_data.get('rate', 0)))
                rate_with_markup = (original_rate * markup_multiplier).quantize(Decimal('0.01'))
                
                Service.objects.create(
                    service_id=service_id,
                    name=service_data.get('name', ''),
                    category=service_data.get('category', ''),
                    description=service_data.get('description', ''),
                    rate=rate_with_markup,
                    min_quantity=service_data.get('min', 0),
                    max_quantity=service_data.get('max', 0),
                    is_active=True
                )
                services_added += 1
        
        messages.success(request, f"Services synced successfully! {services_added} added, {services_updated} updated.")
    except Exception as e:
        messages.error(request, f"Error syncing services: {str(e)}")
    
    return redirect('admin_panel:services')

@staff_member_required
def admin_orders(request):
    # Get all orders
    orders_list = Order.objects.all().order_by('-created_at')
    
    # Handle search
    search_query = request.GET.get('search', '')
    if search_query:
        orders_list = orders_list.filter(
            Q(id__icontains=search_query) | 
            Q(order_id__icontains=search_query) |
            Q(user__username__icontains=search_query) |
            Q(user__email__icontains=search_query) |
            Q(service__name__icontains=search_query)
        )
    
    # Handle status filter
    status_filter = request.GET.get('status', '')
    if status_filter:
        orders_list = orders_list.filter(status=status_filter)
    
    # Pagination
    paginator = Paginator(orders_list, 20)  # Show 20 orders per page
    page = request.GET.get('page')
    orders = paginator.get_page(page)
    
    context = {
        'orders': orders,
        'status_filter': status_filter,
        'search_query': search_query,
    }
    
    return render(request, 'admin_panel/orders.html', context)

@staff_member_required
def admin_order_detail(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    
    # If the order is still processing, check for updates
    if order.status == 'processing' and order.order_id:
        api = SocialMediaAPI(settings.API_KEY)
        response = api.get_order_status(order.order_id)
        
        if 'status' in response:
            # Map API status to our status
            status_mapping = {
                'Pending': 'pending',
                'In progress': 'processing',
                'Completed': 'completed',
                'Canceled': 'canceled',
                'Error': 'error'
            }
            
            new_status = status_mapping.get(response['status'], order.status)
            
            if new_status != order.status:
                order.status = new_status
                order.save()
    
    context = {
        'order': order,
    }
    
    return render(request, 'admin_panel/order_detail.html', context)

@staff_member_required
@require_POST
def admin_order_update_status(request):
    order_id = request.POST.get('order_id')
    new_status = request.POST.get('status')
    
    order = get_object_or_404(Order, id=order_id)
    
    # Validate status
    valid_statuses = ['pending', 'processing', 'completed', 'canceled', 'error']
    if new_status not in valid_statuses:
        messages.error(request, "Invalid status")
        return redirect('admin_panel:order_detail', order_id=order.id)
    
    # Update status
    order.status = new_status
    order.save()
    
    messages.success(request, f"Order #{order.id} status updated to {new_status}")
    return redirect('admin_panel:order_detail', order_id=order.id)

@staff_member_required
def admin_export_orders(request):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="orders.csv"'
    
    writer = csv.writer(response)
    writer.writerow(['ID', 'Order ID', 'User', 'Service', 'Link', 'Quantity', 'Charge', 'Status', 'Created At'])
    
    orders = Order.objects.all().order_by('-created_at')
    
    for order in orders:
        writer.writerow([
            order.id,
            order.order_id,
            order.user.username,
            order.service.name,
            order.link,
            order.quantity,
            order.charge,
            order.status,
            order.created_at
        ])
    
    return response

@staff_member_required
def update_orders_manual(request):
    try:
        api = SocialMediaAPI(settings.API_KEY)
        
        # Get processing orders
        processing_orders = Order.objects.filter(status='processing')
        
        updated_count = 0
        
        for order in processing_orders:
            if not order.order_id:
                continue
            
            response = api.get_order_status(order.order_id)
            
            if 'status' in response:
                # Map API status to our status
                status_mapping = {
                    'Pending': 'pending',
                    'In progress': 'processing',
                    'Completed': 'completed',
                    'Canceled': 'canceled',
                    'Error': 'error'
                }
                
                new_status = status_mapping.get(response['status'], order.status)
                
                if new_status != order.status:
                    order.status = new_status
                    order.save()
                    updated_count += 1
        
        messages.success(request, f"Orders updated successfully! {updated_count} orders updated.")
    except Exception as e:
        messages.error(request, f"Error updating orders: {str(e)}")
    
    return redirect('admin_panel:orders')

@staff_member_required
def admin_order_add_note(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    
    if request.method == 'POST':
        note = request.POST.get('note', '')
        
        if note:
            # Assuming you have a notes field in your Order model
            # If not, you might need to create a separate OrderNote model
            if not hasattr(order, 'notes') or order.notes is None:
                order.notes = note
            else:
                order.notes += f"\n\n{timezone.now().strftime('%Y-%m-%d %H:%M:%S')} - {note}"
            
            order.save()
            
            messages.success(request, "Note added successfully!")
        else:
            messages.error(request, "Note cannot be empty")
    
    return redirect('admin_panel:order_detail', order_id=order.id)

@staff_member_required
def admin_transactions(request):
    # Get all transactions
    transactions_list = Transaction.objects.all().order_by('-created_at')
    
    # Handle search
    search_query = request.GET.get('search', '')
    if search_query:
        transactions_list = transactions_list.filter(
            Q(user__username__icontains=search_query) | 
            Q(user__email__icontains=search_query) |
            Q(description__icontains=search_query)
        )
    
    # Handle type filter
    type_filter = request.GET.get('type', '')
    if type_filter:
        transactions_list = transactions_list.filter(transaction_type=type_filter)
    
    # Pagination
    paginator = Paginator(transactions_list, 20)  # Show 20 transactions per page
    page = request.GET.get('page')
    transactions = paginator.get_page(page)
    
    context = {
        'transactions': transactions,
        'type_filter': type_filter,
        'search_query': search_query,
    }
    
    return render(request, 'admin_panel/transactions.html', context)

@staff_member_required
def admin_export_transactions(request):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="transactions.csv"'
    
    writer = csv.writer(response)
    writer.writerow(['ID', 'User', 'Amount', 'Type', 'Description', 'Created At'])
    
    transactions = Transaction.objects.all().order_by('-created_at')
    
    for transaction in transactions:
        writer.writerow([
            transaction.id,
            transaction.user.username,
            transaction.amount,
            transaction.transaction_type,
            transaction.description,
            transaction.created_at
        ])
    
    return response

@staff_member_required
def admin_settings(request):
    settings = SiteSettings.get_settings()
    
    context = {
        'settings': settings,
    }
    
    return render(request, 'admin_panel/settings.html', context)

@staff_member_required
@require_POST
def admin_save_settings(request):
    settings = SiteSettings.get_settings()
    
    # Update settings
    settings.site_name = request.POST.get('site_name', settings.site_name)
    settings.site_description = request.POST.get('site_description', settings.site_description)
    settings.contact_email = request.POST.get('contact_email', settings.contact_email)
    settings.support_email = request.POST.get('support_email', settings.support_email)
    settings.support_phone = request.POST.get('support_phone', settings.support_phone)
    
    try:
        settings.markup_percentage = Decimal(request.POST.get('markup_percentage', settings.markup_percentage))
        settings.min_deposit = Decimal(request.POST.get('min_deposit', settings.min_deposit))
        settings.min_withdrawal_amount = Decimal(request.POST.get('min_withdrawal_amount', settings.min_withdrawal_amount))
    except:
        messages.error(request, "Invalid number format for one of the numeric fields")
        return redirect('admin_panel:settings')
    
    # Handle checkbox for maintenance mode
    settings.maintenance_mode = 'maintenance_mode' in request.POST
    
    settings.save()
    
    messages.success(request, "Settings updated successfully!")
    return redirect('admin_panel:settings')

@staff_member_required
def record_provider_payment(request):
    if request.method == 'POST':
        amount = request.POST.get('amount')
        payment_method = request.POST.get('payment_method')
        reference = request.POST.get('reference')
        notes = request.POST.get('notes')
        
        try:
            amount = Decimal(amount)
            
            ProviderPayment.objects.create(
                amount=amount,
                payment_method=payment_method,
                reference=reference,
                notes=notes,
                status='completed'
            )
            
            messages.success(request, f"Provider payment of ₦{amount} recorded successfully!")
            
        except Exception as e:
            messages.error(request, f"Error recording payment: {str(e)}")
        
        return redirect('admin_panel:dashboard')
    
    return render(request, 'admin_panel/record_payment.html')

@staff_member_required
def provider_payment_history(request):
    payments = ProviderPayment.objects.all().order_by('-created_at')
    
    total_paid = payments.filter(status='completed').aggregate(Sum('amount'))['amount__sum'] or Decimal('0.00')
    
    # Calculate amount owed to provider
    total_orders = Order.objects.filter(
        status__in=['completed', 'processing', 'pending']
    )
    
    # Get site settings for markup calculation
    site_settings = SiteSettings.get_settings()
    markup_multiplier = (Decimal('100') + site_settings.markup_percentage) / Decimal('100')
    
    total_wholesale_cost = Decimal('0.00')
    
    for order in total_orders:
        # Calculate the wholesale price (remove the markup)
        wholesale_price = (order.charge / markup_multiplier).quantize(Decimal('0.01'))
        total_wholesale_cost += wholesale_price
    
    amount_owed = total_wholesale_cost - total_paid
    
    context = {
        'payments': payments,
        'total_paid': total_paid,
        'total_wholesale_cost': total_wholesale_cost,
        'amount_owed': amount_owed,
    }
    
    return render(request, 'admin_panel/provider_payment_history.html', context)

@staff_member_required
def admin_check_balance(request):
    # Only allow staff/admin users
    if not request.user.is_staff:
        messages.error(request, "You don't have permission to access this page")
        return redirect('dashboard')
    
    api = SocialMediaAPI(settings.API_KEY)
    response = api.get_balance()
    
    if 'error' in response:
        messages.error(request, f"Error checking API balance: {response['error']}")
        return redirect('admin_panel:dashboard')
    
    balance = response.get('balance', 'Unknown')
    
    # Get pending orders count and cost
    pending_orders = Order.objects.filter(status='pending')
    pending_orders_count = pending_orders.count()
    
    # Get site settings for markup calculation
    site_settings = SiteSettings.get_settings()
    markup_multiplier = (Decimal('100') + site_settings.markup_percentage) / Decimal('100')
    
    # Calculate wholesale cost of pending orders
    pending_orders_cost = Decimal('0.00')
    for order in pending_orders:
        wholesale_price = (order.charge / markup_multiplier).quantize(Decimal('0.01'))
        pending_orders_cost += wholesale_price
    
    return render(request, 'admin_panel/check_balance.html', {
        'api_balance': balance,
        'pending_orders_count': pending_orders_count,
        'pending_orders_cost': pending_orders_cost
    })

@staff_member_required
def test_api_connection(request):
    api = SocialMediaAPI(settings.API_KEY)
    
    # Test the API connection by getting the balance
    response = api.get_balance()
    
    if 'error' in response:
        return JsonResponse({
            'success': False,
            'message': f"API connection failed: {response['error']}"
        })
    
    return JsonResponse({
        'success': True,
        'message': "API connection successful!",
        'balance': response.get('balance', 'Unknown')
    })

@staff_member_required
def adjust_markup(request):
    settings = SiteSettings.get_settings()
    
    if request.method == 'POST':
        markup_percentage = request.POST.get('markup_percentage')
        
        try:
            markup_percentage = Decimal(markup_percentage)
            
            if markup_percentage < 0:
                messages.error(request, "Markup percentage cannot be negative.")
                return redirect('admin_panel:adjust_markup')
            
            settings.markup_percentage = markup_percentage
            settings.save()
            
            messages.success(request, f"Markup percentage updated to {markup_percentage}%")
            
            # Trigger service sync to update prices
            from django.core.management import call_command
            call_command('sync_services')
            
            messages.info(request, "Service prices have been updated with the new markup.")
            
        except Exception as e:
            messages.error(request, f"Error updating markup: {str(e)}")
        
        return redirect('admin_panel:dashboard')
    
    context = {
        'settings': settings,
    }
    
    return render(request, 'admin_panel/adjust_markup.html', context)
