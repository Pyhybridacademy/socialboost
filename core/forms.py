from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from .models import Order

class UserRegistrationForm(UserCreationForm):
    email = forms.EmailField(required=True)
    first_name = forms.CharField(required=False)
    last_name = forms.CharField(required=False)
    
    class Meta:
        model = User
        fields = ('username', 'email', 'first_name', 'last_name', 'password1', 'password2')
    
    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        user.first_name = self.cleaned_data['first_name']
        user.last_name = self.cleaned_data['last_name']
        
        if commit:
            user.save()
        
        return user

from django import forms
from .models import Service

class OrderForm(forms.Form):
    quantity = forms.IntegerField(
        min_value=1,
        widget=forms.NumberInput(attrs={'class': 'form-control'})
    )
    link = forms.URLField(
        widget=forms.URLInput(attrs={'class': 'form-control'})
    )
    comments = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3})
    )
    
    def __init__(self, *args, **kwargs):
        service = kwargs.pop('service', None)
        super(OrderForm, self).__init__(*args, **kwargs)
        
        if service:
            self.fields['quantity'].min_value = service.min_quantity
            self.fields['quantity'].max_value = service.max_quantity
            self.fields['quantity'].initial = service.min_quantity
            self.fields['quantity'].widget.attrs.update({
                'min': service.min_quantity,
                'max': service.max_quantity
            })


class AddFundsForm(forms.Form):
    PAYMENT_CHOICES = [
        ('paypal', 'PayPal'),
        ('credit_card', 'Credit Card'),
        ('crypto', 'Cryptocurrency'),
    ]
    
    amount = forms.DecimalField(
        min_value=5.00, 
        decimal_places=2,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter amount',
            'min': '5',
            'step': '0.01'
        })
    )
    payment_method = forms.ChoiceField(
        choices=PAYMENT_CHOICES,
        widget=forms.RadioSelect(attrs={'class': 'form-check-input'})
    )

# Update the AddFundsForm in forms.py

class AddFundsForm(forms.Form):
    PAYMENT_CHOICES = [
        ('card', 'Card Payment'),
        ('bank', 'Bank Transfer'),
        ('ussd', 'USSD'),
    ]
    
    amount = forms.DecimalField(
        min_value=500.00,  # Minimum amount in Naira
        decimal_places=2,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter amount',
            'min': '500',
            'step': '100'
        })
    )
    payment_method = forms.ChoiceField(
        choices=PAYMENT_CHOICES,
        widget=forms.RadioSelect(attrs={'class': 'form-check-input'})
    )