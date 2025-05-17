from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth.models import User
from .models import Order

class FancyTextInput(forms.TextInput):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault('attrs', {}).update({
            'class': 'w-full px-5 py-3 rounded-lg font-medium border-2 border-gray-200 placeholder-gray-400 text-sm focus:outline-none focus:border-primary-500 focus:ring-0 transition-all duration-300',
        })
        super().__init__(*args, **kwargs)

class FancyEmailInput(forms.EmailInput):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault('attrs', {}).update({
            'class': 'w-full px-5 py-3 rounded-lg font-medium border-2 border-gray-200 placeholder-gray-400 text-sm focus:outline-none focus:border-primary-500 focus:ring-0 transition-all duration-300',
        })
        super().__init__(*args, **kwargs)

class FancyPasswordInput(forms.PasswordInput):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault('attrs', {}).update({
            'class': 'w-full px-5 py-3 rounded-lg font-medium border-2 border-gray-200 placeholder-gray-400 text-sm focus:outline-none focus:border-primary-500 focus:ring-0 transition-all duration-300',
        })
        super().__init__(*args, **kwargs)

class UserRegistrationForm(UserCreationForm):
    email = forms.EmailField(
        required=True,
        widget=FancyEmailInput(attrs={
            'placeholder': 'your@email.com',
            'data-aos': 'fade-up',
            'data-aos-delay': '100'
        })
    )
    first_name = forms.CharField(
        required=False,
        widget=FancyTextInput(attrs={
            'placeholder': 'First Name',
            'data-aos': 'fade-up',
            'data-aos-delay': '150'
        })
    )
    last_name = forms.CharField(
        required=False,
        widget=FancyTextInput(attrs={
            'placeholder': 'Last Name',
            'data-aos': 'fade-up',
            'data-aos-delay': '200'
        })
    )
    
    class Meta:
        model = User
        fields = ('username', 'email', 'first_name', 'last_name', 'password1', 'password2')
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].widget = FancyTextInput(attrs={
            'placeholder': 'Username',
            'data-aos': 'fade-up',
            'data-aos-delay': '50'
        })
        self.fields['password1'].widget = FancyPasswordInput(attrs={
            'placeholder': 'Password',
            'data-aos': 'fade-up',
            'data-aos-delay': '250'
        })
        self.fields['password2'].widget = FancyPasswordInput(attrs={
            'placeholder': 'Confirm Password',
            'data-aos': 'fade-up',
            'data-aos-delay': '300'
        })

class UserLoginForm(AuthenticationForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].widget = FancyTextInput(attrs={
            'placeholder': 'Username or Email',
            'data-aos': 'fade-up',
            'data-aos-delay': '50'
        })
        self.fields['password'].widget = FancyPasswordInput(attrs={
            'placeholder': 'Password',
            'data-aos': 'fade-up',
            'data-aos-delay': '100'
        })


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