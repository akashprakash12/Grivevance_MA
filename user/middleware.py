from django.shortcuts import redirect
from django.urls import reverse
from django.conf import settings

class TwoFactorAuthMiddleware:
    """
    Middleware to enforce 2FA verification for authenticated users.
    """
    def __init__(self, get_response):
        self.get_response = get_response
        self.exempt_urls = [
            reverse('public_user:account_settings'),
            reverse('public_user:verify_2fa'),
            reverse('public_user:disable_2fa'),
            reverse('public_user:logout'),
            # Add other URLs that shouldn't require 2FA verification
        ]

    def __call__(self, request):
        # Skip middleware for static files
        if request.path.startswith(settings.STATIC_URL):
            return self.get_response(request)

        # Skip if user isn't authenticated or 2FA isn't enabled
        if not request.user.is_authenticated or not request.user.has_2fa_enabled():
            return self.get_response(request)

        # Skip exempt URLs
        if request.path in self.exempt_urls:
            return self.get_response(request)

        # Check if 2FA is verified for this session
        if not request.session.get('2fa_verified', False):
            # Store the original requested path
            request.session['next_url'] = request.path
            return redirect(reverse('public_user:verify_2fa'))

        return self.get_response(request)