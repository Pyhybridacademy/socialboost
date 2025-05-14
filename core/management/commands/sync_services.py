from django.core.management.base import BaseCommand
from django.conf import settings
from core.api_client import SocialMediaAPI
from core.models import Service
import logging
import sys
import re
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

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

# Safe conversion to Decimal
def safe_decimal(value, default=0):
    try:
        if value is None:
            return Decimal(default)
        return Decimal(str(value).replace(',', '.')).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    except (InvalidOperation, ValueError, TypeError):
        return Decimal(default)

class Command(BaseCommand):
    help = 'Synchronize services from the API provider'

    def handle(self, *args, **options):
        # Check if we're running on Windows
        is_windows = sys.platform.startswith('win')
        
        api = SocialMediaAPI(settings.API_KEY)
        response = api.get_services()
        
        if 'error' in response:
            self.stdout.write(self.style.ERROR(f"Error fetching services: {response['error']}"))
            return
        
        # Count for reporting
        created_count = 0
        updated_count = 0
        deactivated_count = 0
        error_count = 0
        
        # Get all current service IDs
        current_service_ids = set(Service.objects.values_list('service_id', flat=True))
        synced_service_ids = set()
        
        for service_data in response:
            try:
                # Safely get service_id
                try:
                    service_id = int(service_data['service'])
                except (ValueError, KeyError, TypeError):
                    logger.error(f"Invalid service ID in data: {service_data}")
                    error_count += 1
                    continue
                
                synced_service_ids.add(service_id)
                
                # Safely get rate and apply markup
                original_rate = safe_decimal(service_data.get('rate', '0'))
                marked_up_rate = (original_rate * Decimal('1.2')).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
                
                # Safely get min and max quantities
                try:
                    min_quantity = int(service_data.get('min', 0))
                except (ValueError, TypeError):
                    min_quantity = 0
                    
                try:
                    max_quantity = int(service_data.get('max', 0))
                except (ValueError, TypeError):
                    max_quantity = 0
                
                # Clean the name for Windows console if needed
                service_name = service_data.get('name', '')
                clean_name = strip_emoji(service_name) if is_windows else service_name
                
                # Get category with fallback
                category = service_data.get('category', 'Uncategorized')
                
                # Get description with fallback
                description = service_data.get('description', '')
                
                service, created = Service.objects.update_or_create(
                    service_id=service_id,
                    defaults={
                        'name': service_name,  # Keep the original name with emoji in the database
                        'category': category,
                        'rate': marked_up_rate,
                        'min_quantity': min_quantity,
                        'max_quantity': max_quantity,
                        'description': description,
                        'is_active': True
                    }
                )
                
                if created:
                    created_count += 1
                    # Use the clean name for logging
                    self.stdout.write(self.style.SUCCESS(f"Created service: {clean_name}"))
                    logger.info(f"Created service: {clean_name}")
                else:
                    updated_count += 1
                    self.stdout.write(self.style.SUCCESS(f"Updated service: {clean_name}"))
                    logger.info(f"Updated service: {clean_name}")
            
            except Exception as e:
                error_count += 1
                logger.error(f"Error processing service: {str(e)}")
                logger.error(f"Service data: {service_data}")
                self.stdout.write(self.style.ERROR(f"Error processing service: {str(e)}"))
        
        # Deactivate services that are no longer available from the provider
        services_to_deactivate = current_service_ids - synced_service_ids
        if services_to_deactivate:
            deactivated_count = Service.objects.filter(service_id__in=services_to_deactivate).update(is_active=False)
            logger.info(f"Deactivated {deactivated_count} services")
        
        self.stdout.write(self.style.SUCCESS(
            f"Service sync complete: {created_count} created, {updated_count} updated, "
            f"{deactivated_count} deactivated, {error_count} errors"
        ))
