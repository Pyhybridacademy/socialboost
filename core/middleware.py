from django.shortcuts import render
from django.urls import reverse
from django.contrib.auth.models import User
from .models import SiteSettings

class MaintenanceModeMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Get site settings
        settings = SiteSettings.get_settings()
        
        # Check if maintenance mode is enabled
        if settings.maintenance_mode:
            # Allow staff users to access the site
            if request.user.is_authenticated and request.user.is_staff:
                # Add a flag to the request to indicate maintenance mode
                request.maintenance_mode = True
                response = self.get_response(request)
                return response
                
            # Allow access to the login page
            if request.path == reverse('login'):
                response = self.get_response(request)
                return response
                
            # Allow access to static files
            if request.path.startswith('/static/') or request.path.startswith('/media/'):
                response = self.get_response(request)
                return response
                
            # Show maintenance page for all other requests
            context = {
                'site_settings': settings,
            }
            return render(request, 'maintenance.html', context)
        
        # Maintenance mode is not enabled, proceed normally
        response = self.get_response(request)
        return response
