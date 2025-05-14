from django.core.management.base import BaseCommand
from django.conf import settings
from core.models import Order
from core.api_client import SocialMediaAPI
import logging
import sys
import re

logger = logging.getLogger(__name__)

# Function to strip emoji characters from strings
def strip_emoji(text):
    if text is None:
        return ""
    # This regex pattern will match most emoji characters
    emoji_pattern = re.compile(
        "["
        "\U0001F600-\U0001F64F"  # emoticons
        "\U0001F300-\U0001F5FF"  # symbols & pictographs
        "\U0001F680-\U0001F6FF"  # transport & map symbols
        "\U0001F700-\U0001F77F"  # alchemical symbols
        "\U0001F780-\U0001F7FF"  # Geometric Shapes
        "\U0001F800-\U0001F8FF"  # Supplemental Arrows-C
        "\U0001F900-\U0001F9FF"  # Supplemental Symbols and Pictographs
        "\U0001FA00-\U0001FA6F"  # Chess Symbols
        "\U0001FA70-\U0001FAFF"  # Symbols and Pictographs Extended-A
        "\U00002702-\U000027B0"  # Dingbats
        "\U000024C2-\U0001F251" 
        "]+", flags=re.UNICODE)
    return emoji_pattern.sub(r'', text)

class Command(BaseCommand):
    help = 'Update the status of processing orders'

    def handle(self, *args, **options):
        # Check if we're running on Windows
        is_windows = sys.platform.startswith('win')
        
        # Get all processing orders
        processing_orders = Order.objects.filter(status='processing')
        
        if not processing_orders.exists():
            self.stdout.write(self.style.SUCCESS('No processing orders to update'))
            return
        
        # Get order IDs
        order_ids = [order.order_id for order in processing_orders if order.order_id]
        
        if not order_ids:
            self.stdout.write(self.style.SUCCESS('No order IDs to check'))
            return
        
        # Check status in batches of 100 (or whatever the API supports)
        batch_size = 100
        updated_count = 0
        
        for i in range(0, len(order_ids), batch_size):
            batch = order_ids[i:i+batch_size]
            
            api = SocialMediaAPI(settings.API_KEY)
            response = api.get_multiple_order_status(batch)
            
            if 'error' in response:
                self.stdout.write(self.style.ERROR(f"Error checking order statuses: {response['error']}"))
                continue
            
            # Update order statuses
            for order_id, status_data in response.items():
                try:
                    order = Order.objects.get(order_id=order_id)
                    
                    # Map API status to our status
                    status_mapping = {
                        'Pending': 'pending',
                        'In progress': 'processing',
                        'Completed': 'completed',
                        'Canceled': 'canceled',
                        'Error': 'error'
                    }
                    
                    new_status = status_mapping.get(status_data.get('status'), order.status)
                    
                    if new_status != order.status:
                        order.status = new_status
                        order.save()
                        updated_count += 1
                        
                        # Clean service name for logging if needed
                        service_name = order.service.name
                        clean_name = strip_emoji(service_name) if is_windows else service_name
                        
                        log_msg = f"Updated order #{order.id} ({clean_name}) status to {new_status}"
                        logger.info(log_msg)
                        self.stdout.write(self.style.SUCCESS(log_msg))
                except Order.DoesNotExist:
                    logger.warning(f"Order with provider ID {order_id} not found in database")
        
        self.stdout.write(self.style.SUCCESS(f"Updated {updated_count} order statuses"))