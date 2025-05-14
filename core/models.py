from django.db import models
from django.contrib.auth.models import User
from decimal import Decimal, InvalidOperation

class Service(models.Model):
    service_id = models.IntegerField(unique=True)
    name = models.CharField(max_length=255)
    category = models.CharField(max_length=100)
    rate = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    min_quantity = models.IntegerField()
    max_quantity = models.IntegerField()
    description = models.TextField()
    is_active = models.BooleanField(default=True)
    
    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        # Ensure rate is a valid Decimal
        try:
            self.rate = Decimal(str(self.rate)).quantize(Decimal('0.01'))
        except (InvalidOperation, TypeError):
            self.rate = Decimal('0.00')
        
        super().save(*args, **kwargs)

class Order(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('canceled', 'Canceled'),
        ('error', 'Error'),
    )
    
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    service = models.ForeignKey(Service, on_delete=models.CASCADE)
    order_id = models.CharField(max_length=100, blank=True, null=True)  # From API provider
    link = models.URLField()
    quantity = models.IntegerField()
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default='pending')
    charge = models.DecimalField(max_digits=10, decimal_places=2)
    comments = models.TextField(blank=True, null=True) 
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Order {self.id} - {self.service.name}"
    
class UserBalance(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    balance = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    def __str__(self):
        return f"{self.user.username}'s balance: ${self.balance}"

# Add a Transaction model to track payments and withdrawals
class Transaction(models.Model):
    TRANSACTION_TYPES = (
        ('deposit', 'Deposit'),
        ('withdrawal', 'Withdrawal'),
        ('order', 'Order Payment'),
        ('refund', 'Refund'),
    )
    
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    transaction_type = models.CharField(max_length=20, choices=TRANSACTION_TYPES)
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.transaction_type} - ${self.amount} - {self.user.username}"
    

class ProviderPayment(models.Model):
    PAYMENT_STATUS = (
        ('pending', 'Pending'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    )
    
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    reference = models.CharField(max_length=100, blank=True, null=True)
    payment_method = models.CharField(max_length=50)
    status = models.CharField(max_length=20, choices=PAYMENT_STATUS, default='pending')
    notes = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Provider Payment #{self.id} - ₦{self.amount}"

class SiteSettings(models.Model):
    site_name = models.CharField(max_length=100, default="SocialBoost")
    site_description = models.TextField(blank=True, default="Social Media Marketing Platform")
    contact_email = models.EmailField(default='contact@yoursite.com')
    support_email = models.EmailField(default='support@yoursite.com')
    support_phone = models.CharField(max_length=20, blank=True, null=True)
    markup_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('20.00'))
    min_deposit = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('500.00'))
    min_withdrawal_amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('1000.00'))
    maintenance_mode = models.BooleanField(default=False)

    def __str__(self):
        return "Site Settings"
    
    @classmethod
    def get_settings(cls):
        settings, created = cls.objects.get_or_create(pk=1)
        return settings
