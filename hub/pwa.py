import hashlib
import json
from django.conf import settings
from django.http import JsonResponse, HttpResponse
from django.shortcuts import render
from django.templatetags.static import static
from django.views.decorators.http import require_GET
from django.views.decorators.cache import never_cache

ASSETS = ['pwa.css', 'pwa.js', 'theme-init.js', 'theme.js', 'theme.css', 'icon-192.png', 'icon-512.png', 'icon-maskable.png']

@require_GET
@never_cache
def worker(request):
    root = settings.BASE_DIR
    source = (root / 'templates/pwa/sw.js').read_text(encoding='utf-8')
    # Un nouveau cache pour chaque changement de la ressources locales.
    digest = hashlib.sha256(source.encode())
    for name in ASSETS:
        digest.update((root / 'static/hub' / name).read_bytes())
    source = source.replace('__REVISION__', digest.hexdigest()[:16]).replace('__ASSETS__', json.dumps([static('hub/' + n) for n in ASSETS]))
    response = HttpResponse(source, content_type='text/javascript; charset=utf-8')
    response['Service-Worker-Allowed'] = '/'
    return response

@require_GET
def manifest(request):
    from .models import HubAppearance
    appearance = HubAppearance.current()
    name = appearance.site_name or "Gaboma Hub"
    return JsonResponse({'id': '/', 'name': name, 'short_name': name[:12],
        'description': appearance.meta_description or "Découvrez les applications des créateurs gabonais.",
        'lang': 'fr', 'start_url': '/', 'scope': '/', 'display': 'standalone',
        'background_color': '#101827', 'theme_color': '#235acb',
        'icons': [{'src': static('hub/icon-192.png'), 'sizes': '192x192', 'type': 'image/png', 'purpose': 'any'},
                  {'src': static('hub/icon-512.png'), 'sizes': '512x512', 'type': 'image/png', 'purpose': 'any'},
                  {'src': static('hub/icon-maskable.png'), 'sizes': '512x512', 'type': 'image/png', 'purpose': 'maskable'}]},
        content_type='application/manifest+json')

@require_GET
def install(request):
    return render(request, 'pwa/install.html')
