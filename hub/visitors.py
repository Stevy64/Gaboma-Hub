"""Anonymous browser counter: no IP, account, or browsing history stored."""
import hashlib
import uuid
from django.conf import settings
from .models import HubVisitor

COOKIE = 'hub_visitor'
SALT = 'hub.visitor.v1'

def visitor_stats(request):
    token = request.get_signed_cookie(COOKIE, default='', salt=SALT, max_age=31536000)
    try:
        token = str(uuid.UUID(token))
    except (ValueError, TypeError, AttributeError):
        token = str(uuid.uuid4())
    agent = request.headers.get('User-Agent', '').lower()
    excluded = request.user.is_staff or any(word in agent for word in ('bot', 'crawler', 'spider', 'headless', 'uptime'))
    if not excluded:
        HubVisitor.objects.get_or_create(fingerprint=hashlib.sha256(token.encode()).hexdigest())
    return HubVisitor.objects.count(), None if excluded else token

def set_visitor_cookie(response, token):
    if token:
        response.set_signed_cookie(COOKIE, token, salt=SALT, max_age=31536000,
                                   httponly=True, secure=settings.SESSION_COOKIE_SECURE, samesite='Lax')
    return response
