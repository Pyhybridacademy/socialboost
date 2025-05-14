from decimal import Decimal
from django.contrib import admin
from .models import ProviderPayment, Service, Order, SiteSettings, UserBalance, Transaction

@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'rate', 'min_quantity', 'max_quantity', 'is_active')
    list_filter = ('category', 'is_active')
    search_fields = ('name', 'description')

@admin.register(UserBalance)
class UserBalanceAdmin(admin.ModelAdmin):
    list_display = ('user', 'balance')
    search_fields = ('user__username',)

@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ('user', 'amount', 'transaction_type', 'created_at')
    list_filter = ('transaction_type', 'created_at')
    search_fields = ('user__username', 'description')
    readonly_fields = ('created_at',)

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    # Update list_display to use fields that actually exist in your Order model
    # Replace 'price' with 'charge' if that's what your model uses
    list_display = ('id', 'user', 'service', 'quantity', 'charge', 'status', 'created_at', 'get_wholesale_price', 'get_profit')
    list_filter = ('status', 'created_at')
    search_fields = ('user__username', 'service__name', 'link')
    # Remove 'updated_at' if it doesn't exist in your model
    readonly_fields = ('created_at', 'get_wholesale_price', 'get_profit')
    
    def get_wholesale_price(self, obj):
        site_settings = SiteSettings.get_settings()
        markup_multiplier = (Decimal('100') + site_settings.markup_percentage) / Decimal('100')
        # Use 'charge' instead of 'price' if that's what your model uses
        return (obj.charge / markup_multiplier).quantize(Decimal('0.01'))
    
    get_wholesale_price.short_description = 'Wholesale Price'
    
    def get_profit(self, obj):
        wholesale_price = self.get_wholesale_price(obj)
        # Use 'charge' instead of 'price' if that's what your model uses
        return (obj.charge - wholesale_price).quantize(Decimal('0.01'))
    
    get_profit.short_description = 'Profit'

@admin.register(SiteSettings)
class SiteSettingsAdmin(admin.ModelAdmin):
    list_display = ('markup_percentage', 'support_email', 'maintenance_mode')
    
    def has_add_permission(self, request):
        # Only allow one instance of SiteSettings
        if self.model.objects.exists():
            return False
        return super().has_add_permission(request)
    
    def has_delete_permission(self, request, obj=None):
        # Prevent deletion of the settings object
        return False

@admin.register(ProviderPayment)
class ProviderPaymentAdmin(admin.ModelAdmin):
    list_display = ('id', 'amount', 'payment_method', 'reference', 'status', 'created_at')
    list_filter = ('status', 'payment_method', 'created_at')
    search_fields = ('reference', 'notes')
    readonly_fields = ('created_at',)  