from core.models import SiteSettings

def site_settings(request):
    """
    Add site settings to the template context for all templates.
    """
    try:
        settings = SiteSettings.get_settings()
        return {'site_settings': settings}
    except Exception as e:
        # Provide fallback values if there's an error
        return {
            'site_settings': {
                'site_name': 'SocialBoost',
                'site_description': 'Social Media Marketing Platform',
                'contact_email': 'contact@example.com',
                'support_email': 'support@example.com',
                'markup_percentage': 20.00,
                'min_deposit': 500.00,
                'min_withdrawal_amount': 1000.00,
                'maintenance_mode': False
            }
        }
