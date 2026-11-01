"""Compte un visiteur unique par navigateur, via un cookie signé."""
from .visitors import set_visitor_cookie, visitor_stats

SKIP_PREFIXES = ("/admin", "/static/", "/media/", "/health/")
SKIP_PATHS = {"/sw.js", "/manifest.webmanifest"}


class UniqueVisitorMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.visitor_count = None
        request.visitor_token = None
        path = request.path
        public_page = request.method == "GET" and path not in SKIP_PATHS and not path.startswith(SKIP_PREFIXES)
        if public_page:
            request.visitor_count, request.visitor_token = visitor_stats(request)
        response = self.get_response(request)
        if request.visitor_token:
            set_visitor_cookie(response, request.visitor_token)
        return response
