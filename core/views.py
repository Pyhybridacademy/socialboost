from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.conf import settings
from django.http import JsonResponse
from django.db.models import Sum, Q, Count
from django.utils import timezone
from django.views.decorators.http import require_POST
from django.contrib.auth.models import User
from django.contrib.auth import login, authenticate, update_session_auth_hash
from django.contrib.auth.forms import PasswordChangeForm
from django.core.paginator import Paginator
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.admin.views.decorators import staff_member_required
from .models import Order, Transaction, Service, SiteSettings, ProviderPayment
from django.contrib.auth import logout
from django.shortcuts import render, redirect
from django.contrib import messages

from .models import Service, Order, UserBalance, Transaction
from .api_client import SocialMediaAPI
from .forms import UserRegistrationForm, OrderForm, AddFundsForm
from decimal import Decimal, InvalidOperation
import json
from .payment import PaystackPaymentGateway
import uuid
from django.urls import reverse
from django.http import HttpResponseRedirect
from decimal import Decimal

import logging
logger = logging.getLogger(__name__)

# Home page
def index(request):
    # Get popular services for the homepage
    popular_services = Service.objects.filter(is_active=True).order_by('-id')[:6]
    return render(request, 'index.html', {'popular_services': popular_services})

# Services listing
def services(request):
    # Get all active services
    services_list = Service.objects.filter(is_active=True)
    
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
    
    # Handle sorting
    sort_by = request.GET.get('sort', 'newest')
    if sort_by == 'price_low':
        services_list = services_list.order_by('rate')
    elif sort_by == 'price_high':
        services_list = services_list.order_by('-rate')
    else:  # newest
        services_list = services_list.order_by('-id')
    
    # Get all unique categories for the filter dropdown
    categories = Service.objects.filter(is_active=True).values_list('category', flat=True).distinct()
    
    # Pagination with error handling
    paginator = Paginator(services_list, 12)  # Show 12 services per page
    page = request.GET.get('page', 1)
    
    try:
        page = int(page)
        if page < 1:
            page = 1
    except ValueError:
        page = 1
    
    try:
        services = paginator.page(page)
    except (EmptyPage, InvalidPage):
        # If the page is out of range, deliver the last page
        services = paginator.page(paginator.num_pages)
    
    context = {
        'services': services,
        'categories': categories,
        'selected_category': selected_category,
        'sort_by': sort_by,
        'search_query': search_query,
    }
    
    return render(request, 'services.html', context)

# Services by category
def services_by_category(request):
    # Get all active services
    services_list = Service.objects.filter(is_active=True)
    
    # Handle search
    search_query = request.GET.get('search', '')
    if search_query:
        services_list = services_list.filter(
            Q(name__icontains=search_query) | 
            Q(description__icontains=search_query) |
            Q(category__icontains=search_query)
        )
    
    # Handle sorting
    sort_by = request.GET.get('sort', 'newest')
    if sort_by == 'price_low':
        services_list = services_list.order_by('rate')
    elif sort_by == 'price_high':
        services_list = services_list.order_by('-rate')
    else:  # newest
        services_list = services_list.order_by('-id')
    
    # Get all unique categories
    categories = Service.objects.filter(is_active=True).values_list('category', flat=True).distinct()
    
    # Group services by category
    services_by_category = {}
    for category in categories:
        services_by_category[category] = services_list.filter(category=category)
    
    # Pagination for all services
    paginator = Paginator(services_list, 12)  # Show 12 services per page
    page = request.GET.get('page')
    services = paginator.get_page(page)
    
    context = {
        'services': services,
        'categories': categories,
        'services_by_category': services_by_category,
        'sort_by': sort_by,
        'search_query': search_query,
    }
    
    return render(request, 'services_by_category.html', context)

# Service detail and order form
def service_detail(request, service_id):
    service = get_object_or_404(Service, id=service_id, is_active=True)
    
    # Get user balance
    user_balance = UserBalance.objects.get_or_create(user=request.user)[0]
    
    # Calculate initial price based on minimum quantity
    # Convert to Decimal to avoid float/Decimal multiplication error
    min_quantity = Decimal(str(service.min_quantity))
    initial_price = (min_quantity / Decimal('1000')) * service.rate
    
    context = {
        'service': service,
        'user_balance': user_balance,
        'initial_price': initial_price,
    }
    
    return render(request, 'order.html', context)
# Process order
# Fix the create_order view to use the correct field name
@login_required
@require_POST
def create_order(request):
    service_id = request.POST.get('service')
    link = request.POST.get('link')
    quantity_str = request.POST.get('quantity')
    comments = request.POST.get('comments', '')
    
    # Check if quantity is provided
    if not quantity_str:
        messages.error(request, "Quantity is required")
        return redirect('service_detail', service_id=service_id)
    
    try:
        quantity = int(quantity_str)
    except ValueError:
        messages.error(request, "Quantity must be a valid number")
        return redirect('service_detail', service_id=service_id)
    
    service = get_object_or_404(Service, id=service_id, is_active=True)
    
    # Validate quantity
    if quantity < service.min_quantity or quantity > service.max_quantity:
        messages.error(request, f"Quantity must be between {service.min_quantity} and {service.max_quantity}")
        return redirect('service_detail', service_id=service.id)
    
    # Calculate charge - ensure proper Decimal handling
    try:
        # Convert to Decimal to avoid float precision issues
        quantity_decimal = Decimal(str(quantity))
        charge = (service.rate * quantity_decimal / Decimal('1000')).quantize(Decimal('0.01'))
        
        logger.info(f"Order calculation - Service: {service.name}, Rate: {service.rate}, Quantity: {quantity}, Charge: {charge}")
    except (InvalidOperation, TypeError) as e:
        logger.error(f"Error calculating charge: {str(e)} - Service rate: {service.rate}, Quantity: {quantity}")
        messages.error(request, "Error calculating order price. Please contact support.")
        return redirect('service_detail', service_id=service.id)
    
    # Check user balance
    user_balance = UserBalance.objects.get_or_create(user=request.user)[0]
    
    # Debug information
    logger.info(f"Order attempt - User: {request.user.username}, Balance: {user_balance.balance}, Charge: {charge}")
    
    if user_balance.balance < charge:
        messages.error(request, f"Insufficient balance. You need ₦{charge} but your balance is ₦{user_balance.balance}.")
        return redirect('add_funds')
    
    # Create order in our database first
    try:
        order = Order.objects.create(
            user=request.user,
            service=service,
            link=link,
            quantity=quantity,
            status='pending',
            charge=charge,  # Use charge instead of price
            comments=comments
        )
    except Exception as e:
        logger.error(f"Error creating order: {str(e)}")
        messages.error(request, f"Error creating order: {str(e)}")
        return redirect('service_detail', service_id=service.id)
    
    # Deduct from user balance
    user_balance.balance -= charge
    user_balance.save()
    
    # Record the transaction
    Transaction.objects.create(
        user=request.user,
        amount=charge,  # Use positive amount for consistency
        transaction_type='order',  # Use transaction_type instead of type
        description=f"Payment for order #{order.id} - {service.name}"
    )
    
    # Submit order to API provider
    try:
        api = SocialMediaAPI(settings.API_KEY)
        response = api.create_order(
            service.service_id,
            link,
            quantity
        )
        
        logger.info(f"API response for order #{order.id}: {response}")
        
        if 'error' in response:
            # Handle error - refund the user
            order.status = 'error'  # Use 'error' to match your STATUS_CHOICES
            order.save()
            
            user_balance.balance += charge
            user_balance.save()
            
            Transaction.objects.create(
                user=request.user,
                amount=charge,  # Positive amount for refund
                transaction_type='refund',  # Use transaction_type instead of type
                description=f"Refund for failed order #{order.id} - {response.get('error', 'Unknown error')}"
            )
            
            messages.error(request, f"Order failed: {response.get('error', 'Unknown error')}")
            return redirect('service_detail', service_id=service.id)
        
        # Update order with provider's order ID
        if 'order' in response:
            order.order_id = response['order']
            order.status = 'processing'
            order.save()
            
            messages.success(request, f"Order placed successfully! Order ID: {order.id}")
            return redirect('order_confirmation', order_id=order.id)
        else:
            # Unexpected response
            logger.error(f"Unexpected API response for order #{order.id}: {response}")
            messages.error(request, "Unexpected response from service provider. Please contact support.")
            return redirect('dashboard')
            
    except Exception as e:
        # Handle any exceptions during API call
        logger.error(f"Exception during API call for order #{order.id}: {str(e)}")
        
        # Update order status
        order.status = 'error'  # Use 'error' to match your STATUS_CHOICES
        order.save()
        
        # Refund the user
        user_balance.balance += charge
        user_balance.save()
        
        Transaction.objects.create(
            user=request.user,
            amount=charge,
            transaction_type='refund',  # Use transaction_type instead of type
            description=f"Refund for failed order #{order.id} - API error"
        )
        
        messages.error(request, f"Order failed: {str(e)}")
        return redirect('service_detail', service_id=service.id)
    

# Order confirmation page
@login_required
def order_confirmation(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)
    return render(request, 'order_confirmation.html', {'order': order})

# Order status page
@login_required
def order_status(request, order_id=None):
    if order_id:
        # Single order view
        order = get_object_or_404(Order, id=order_id, user=request.user)
        
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
        
        return render(request, 'order_detail.html', {'order': order})
    else:
        # All orders view
        orders = Order.objects.filter(user=request.user).order_by('-created_at')
        
        # Pagination
        paginator = Paginator(orders, 10)  # Show 10 orders per page
        page = request.GET.get('page')
        orders_page = paginator.get_page(page)
        
        return render(request, 'order_status.html', {'orders': orders_page})

# User dashboard
@login_required
def dashboard(request):
    # Get user's recent orders
    recent_orders = Order.objects.filter(user=request.user).order_by('-created_at')[:5]
    
    # Get user's balance
    user_balance = UserBalance.objects.get_or_create(user=request.user)[0]
    
    # Get recent transactions
    recent_transactions = Transaction.objects.filter(user=request.user).order_by('-created_at')[:5]
    
    # Calculate statistics
    total_orders = Order.objects.filter(user=request.user).count()
    completed_orders = Order.objects.filter(user=request.user, status='completed').count()
    pending_orders = Order.objects.filter(user=request.user, status='pending').count()
    processing_orders = Order.objects.filter(user=request.user, status='processing').count()
    
    context = {
        'recent_orders': recent_orders,
        'user_balance': user_balance,
        'recent_transactions': recent_transactions,
        'total_orders': total_orders,
        'completed_orders': completed_orders,
        'pending_orders': pending_orders,
        'processing_orders': processing_orders,
    }
    
    return render(request, 'dashboard.html', context)

# User profile
@login_required
def profile(request):
    user = request.user
    user_balance = UserBalance.objects.get_or_create(user=user)[0]
    
    # Calculate statistics
    total_orders = Order.objects.filter(user=user).count()
    completed_orders = Order.objects.filter(user=user, status='completed').count()
    total_spent = Order.objects.filter(user=user).aggregate(Sum('charge'))['charge__sum'] or 0
    
    if request.method == 'POST':
        if 'update_profile' in request.POST:
            # Update profile information
            user.first_name = request.POST.get('first_name', '')
            user.last_name = request.POST.get('last_name', '')
            user.email = request.POST.get('email', '')
            user.save()
            messages.success(request, "Profile updated successfully!")
            
        elif 'change_password' in request.POST:
            # Change password
            current_password = request.POST.get('current_password')
            new_password = request.POST.get('new_password')
            confirm_password = request.POST.get('confirm_password')
            
            if not user.check_password(current_password):
                messages.error(request, "Current password is incorrect.")
            elif new_password != confirm_password:
                messages.error(request, "New passwords do not match.")
            else:
                user.set_password(new_password)
                user.save()
                update_session_auth_hash(request, user)  # Keep user logged in
                messages.success(request, "Password changed successfully!")
    
    context = {
        'user': user,
        'user_balance': user_balance,
        'total_orders': total_orders,
        'completed_orders': completed_orders,
        'total_spent': total_spent,
    }
    
    return render(request, 'profile.html', context)

# Add funds page
# Add these imports at the top of your views.py file


# Update the add_funds and process_payment views, and add paystack callback view

@login_required
def add_funds(request):
    user_balance = UserBalance.objects.get_or_create(user=request.user)[0]
    form = AddFundsForm()
    
    return render(request, 'add_funds.html', {
        'user_balance': user_balance,
        'form': form,
        'paystack_public_key': settings.PAYSTACK_PUBLIC_KEY
    })

@login_required
@require_POST
def process_payment(request):
    form = AddFundsForm(request.POST)
    
    if form.is_valid():
        amount = form.cleaned_data['amount']
        payment_method = form.cleaned_data['payment_method']
        
        # Generate a unique reference for this transaction
        reference = f"sb-{uuid.uuid4().hex[:10]}"
        
        # Store transaction reference in session for verification later
        request.session['payment_reference'] = reference
        request.session['payment_amount'] = str(amount)
        
        # Create metadata for the transaction
        metadata = {
            'user_id': request.user.id,
            'payment_for': 'account_funding',
            'payment_method': payment_method
        }
        
        # Initialize transaction with Paystack
        paystack = PaystackPaymentGateway()
        response = paystack.initialize_transaction(
            request=request,
            amount=amount,
            email=request.user.email,
            reference=reference,
            metadata=metadata
        )
        
        if response['success']:
            # Redirect to Paystack payment page
            return HttpResponseRedirect(response['authorization_url'])
        else:
            # Payment initialization failed
            messages.error(request, f"Payment initialization failed: {response.get('error', 'Unknown error')}")
            return redirect('add_funds')
    else:
        messages.error(request, "Please enter a valid amount")
        return redirect('add_funds')

@login_required
def paystack_callback(request):
    """Handle Paystack payment callback"""
    reference = request.GET.get('reference')
    
    if not reference:
        messages.error(request, "No reference supplied")
        return redirect('add_funds')
    
    # Verify the transaction with Paystack
    paystack = PaystackPaymentGateway()
    response = paystack.verify_transaction(reference)
    
    if response['success']:
        # Get the expected amount from session
        expected_amount = Decimal(request.session.get('payment_amount', '0'))
        
        # Verify that the amount paid matches the expected amount
        if response['amount'] == expected_amount:
            # Update user balance
            user_balance = UserBalance.objects.get_or_create(user=request.user)[0]
            user_balance.balance += expected_amount
            user_balance.save()
            
            # Record the transaction
            Transaction.objects.create(
                user=request.user,
                amount=expected_amount,
                transaction_type='deposit',
                description=f"Deposit to account via Paystack (Ref: {reference})"
            )
            
            # Clear session data
            if 'payment_reference' in request.session:
                del request.session['payment_reference']
            if 'payment_amount' in request.session:
                del request.session['payment_amount']
            
            messages.success(request, f"₦{expected_amount} added to your account successfully!")
            return redirect('dashboard')
        else:
            messages.error(request, "Amount paid does not match expected amount")
            return redirect('add_funds')
    else:
        messages.error(request, f"Payment verification failed: {response.get('error', 'Unknown error')}")
        return redirect('add_funds')
    
# Admin view to check API balance
@login_required
def admin_check_balance(request):
    # Only allow staff/admin users
    if not request.user.is_staff:
        messages.error(request, "You don't have permission to access this page")
        return redirect('dashboard')
    
    api = SocialMediaAPI(settings.API_KEY)
    response = api.get_balance()
    
    if 'error' in response:
        messages.error(request, f"Error checking API balance: {response['error']}")
        return redirect('admin_dashboard')
    
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
    
    return render(request, 'admin/check_balance.html', {
        'api_balance': balance,
        'pending_orders_count': pending_orders_count,
        'pending_orders_cost': pending_orders_cost
    })

# Update the register view to use the form
def register(request):
    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            
            # Create user balance
            UserBalance.objects.create(user=user, balance=0)
            
            # Log the user in
            login(request, user)
            
            messages.success(request, "Registration successful! Welcome to SocialBoost.")
            return redirect('dashboard')
    else:
        form = UserRegistrationForm()
    
    return render(request, 'register.html', {'form': form})

def user_login(request):
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(request, username=username, password=password)  # Pass request to authenticate
            if user is not None:
                login(request, user)
                messages.success(request, f"Welcome back, {user.username}!")
                return redirect('dashboard')
            else:
                messages.error(request, "Invalid username or password.")
        else:
            messages.error(request, "Invalid username or password.")  # Consistent error message
    else:
        form = AuthenticationForm()

    return render(request, 'login.html', {'form': form})


@staff_member_required
def admin_dashboard(request):
    # Get total customer payments
    # Make sure to use transaction_type consistently
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
    
    return render(request, 'admin/dashboard.html', context)

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
        
        return redirect('admin_dashboard')
    
    return render(request, 'admin/record_payment.html')

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
        wholesale_price = (order.price / markup_multiplier).quantize(Decimal('0.01'))
        total_wholesale_cost += wholesale_price
    
    amount_owed = total_wholesale_cost - total_paid
    
    context = {
        'payments': payments,
        'total_paid': total_paid,
        'total_wholesale_cost': total_wholesale_cost,
        'amount_owed': amount_owed,
    }
    
    return render(request, 'admin/provider_payment_history.html', context)

@staff_member_required
def adjust_markup(request):
    settings = SiteSettings.get_settings()
    
    if request.method == 'POST':
        markup_percentage = request.POST.get('markup_percentage')
        
        try:
            markup_percentage = Decimal(markup_percentage)
            
            if markup_percentage < 0:
                messages.error(request, "Markup percentage cannot be negative.")
                return redirect('adjust_markup')
            
            settings.markup_percentage = markup_percentage
            settings.save()
            
            messages.success(request, f"Markup percentage updated to {markup_percentage}%")
            
            # Trigger service sync to update prices
            from django.core.management import call_command
            call_command('sync_services')
            
            messages.info(request, "Service prices have been updated with the new markup.")
            
        except Exception as e:
            messages.error(request, f"Error updating markup: {str(e)}")
        
        return redirect('admin_dashboard')
    
    context = {
        'settings': settings,
    }
    
    return render(request, 'admin/adjust_markup.html', context)

# Add these error handler views to your existing views.py file

def bad_request(request, exception=None):
    return render(request, 'errors/400.html', status=400)

def permission_denied(request, exception=None):
    return render(request, 'errors/403.html', status=403)

def page_not_found(request, exception=None):
    return render(request, 'errors/404.html', status=404)

def server_error(request):
    return render(request, 'errors/500.html', status=500)

def user_logout(request):
    # Explicitly log the user out
    logout(request)
    
    # Add a success message
    messages.success(request, "You have been successfully logged out.")
    
    # Render the logout template
    return render(request, 'registration/logged_out.html')