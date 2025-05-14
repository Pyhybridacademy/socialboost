import requests
import json
from django.conf import settings
from decimal import Decimal
from django.urls import reverse
from django.contrib.sites.shortcuts import get_current_site

class PaystackPaymentGateway:
    @staticmethod
    def initialize_transaction(request, amount, email, reference=None, metadata=None):
        """
        Initialize a payment transaction with Paystack
        
        Args:
            request: The HTTP request object
            amount: Decimal amount to charge in Naira
            email: Customer email
            reference: Unique transaction reference (optional)
            metadata: Additional metadata for the payment
            
        Returns:
            dict: Transaction details including authorization_url
        """
        try:
            # Convert to kobo for Paystack (100 kobo = 1 Naira)
            amount_kobo = int(amount * 100)
            
            # Get the callback URL
            protocol = 'https' if request.is_secure() else 'http'
            current_site = get_current_site(request)
            callback_url = f"{protocol}://{current_site.domain}{reverse('paystack_callback')}"
            
            # Prepare the payload
            payload = {
                "amount": amount_kobo,
                "email": email,
                "currency": "NGN",
                "callback_url": callback_url,
            }
            
            if reference:
                payload["reference"] = reference
                
            if metadata:
                payload["metadata"] = metadata
            
            # Make the API request
            headers = {
                "Authorization": f"Bearer {settings.PAYSTACK_SECRET_KEY}",
                "Content-Type": "application/json"
            }
            
            response = requests.post(
                "https://api.paystack.co/transaction/initialize",
                headers=headers,
                data=json.dumps(payload)
            )
            
            if response.status_code == 200:
                result = response.json()
                if result["status"]:
                    return {
                        "authorization_url": result["data"]["authorization_url"],
                        "reference": result["data"]["reference"],
                        "success": True
                    }
            
            # If we get here, something went wrong
            return {
                "error": response.json().get("message", "Failed to initialize transaction"),
                "success": False
            }
            
        except Exception as e:
            return {
                "error": str(e),
                "success": False
            }
    
    @staticmethod
    def verify_transaction(reference):
        """
        Verify a transaction with Paystack
        
        Args:
            reference: The transaction reference to verify
            
        Returns:
            dict: Transaction details if successful
        """
        try:
            headers = {
                "Authorization": f"Bearer {settings.PAYSTACK_SECRET_KEY}",
                "Content-Type": "application/json"
            }
            
            response = requests.get(
                f"https://api.paystack.co/transaction/verify/{reference}",
                headers=headers
            )
            
            if response.status_code == 200:
                result = response.json()
                if result["status"] and result["data"]["status"] == "success":
                    # Convert amount from kobo to Naira
                    amount_naira = Decimal(result["data"]["amount"]) / 100
                    
                    return {
                        "success": True,
                        "amount": amount_naira,
                        "reference": reference,
                        "email": result["data"]["customer"]["email"],
                        "transaction_date": result["data"]["transaction_date"]
                    }
            
            # If we get here, verification failed
            return {
                "success": False,
                "error": response.json().get("message", "Transaction verification failed")
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }