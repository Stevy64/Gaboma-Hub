import json
import uuid
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.db.models import Q, Avg, Count
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme
from django.utils.text import slugify
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST
from django.utils import timezone
from .forms import ApplicationForm, SignupForm, ReviewForm
from .models import Application, Category, Favorite, Payment, PaymentEvent, Review, HubAppearance, Advertisement
from .payments.services import PaymentUnavailable, checkout_url_is_safe, normalize_reference, start_checkout, verify_payment
from .visitors import visitor_stats, set_visitor_cookie
from .payments.singpay import singpay_service

CATALOGUE_PAGE_SIZE = 24
RAIL_SIZE = 12
LIST_DEFER = ("about", "moderation_note")

def published_apps():
    return Application.objects.filter(status=Application.Status.PUBLISHED).select_related("category").defer(*LIST_DEFER)

def with_card_stats(apps):
    visible = Q(reviews__is_visible=True)
    return apps.annotate(
        average_rating=Avg("reviews__rating", filter=visible),
        review_count=Count("reviews", filter=visible))

def catalogue_filters(request, apps):
    query = request.GET.get("q", "").strip()[:120]
    category = request.GET.get("categorie", "")[:60]
    favorites_only = request.GET.get("vue") == "favoris"
    sort = "rating" if request.GET.get("tri") == "rating" else "recent"
    if query:
        apps = apps.filter(Q(name__icontains=query) | Q(description__icontains=query) | Q(category__name__icontains=query))
    if category:
        apps = apps.filter(category__slug=category)
    if favorites_only:
        apps = apps.filter(favorite__user=request.user) if request.user.is_authenticated else apps.none()
    return apps, query, category, favorites_only, sort

def requested_page(request):
    try:
        number = int(request.GET.get("page") or 1)
    except (TypeError, ValueError):
        number = 1
    return max(1, number)

def catalogue_window(apps, request, sort):
    """Une page du répertoire, sans noter toute la table."""
    number = requested_page(request)
    start = (number - 1) * CATALOGUE_PAGE_SIZE
    stop = start + CATALOGUE_PAGE_SIZE + 1
    if sort == "rating":
        ordered = with_card_stats(apps).order_by("-average_rating", "-review_count", "name", "pk")
        window = list(ordered[start:stop])
        return window[:CATALOGUE_PAGE_SIZE], len(window) > CATALOGUE_PAGE_SIZE, number
    ids = list(apps.order_by("-created_at", "pk").values_list("pk", flat=True)[start:stop])
    has_next = len(ids) > CATALOGUE_PAGE_SIZE
    ids = ids[:CATALOGUE_PAGE_SIZE]
    rows = with_card_stats(published_apps().filter(pk__in=ids)) if ids else []
    by_id = {app.pk: app for app in rows}
    return [by_id[pk] for pk in ids if pk in by_id], has_next, number

def favorite_ids_for(user, applications):
    if not user.is_authenticated:
        return set()
    ids = [app.pk for app in applications]
    if not ids:
        return set()
    return set(Favorite.objects.filter(user=user, application_id__in=ids).values_list("application_id", flat=True))

def take_ids(apps, limit=RAIL_SIZE):
    found = list(apps.order_by("-created_at", "-pk").values_list("pk", flat=True)[: limit + 1])
    return found[:limit], len(found) > limit

def discovery_rails_for(appearance):
    base = published_apps()
    available_ids, available_more = take_ids(base.exclude(website_url=""))
    upcoming_ids, upcoming_more = take_ids(base.filter(website_url=""))
    rated_ids = list(
        Review.objects.filter(is_visible=True, application__status=Application.Status.PUBLISHED)
        .values("application_id").annotate(score=Avg("rating"), votes=Count("id"))
        .order_by("-score", "-votes", "application_id")
        .values_list("application_id", flat=True)[: RAIL_SIZE + 1])
    rated_more = len(rated_ids) > RAIL_SIZE
    rated_ids = rated_ids[:RAIL_SIZE]
    wanted = list(dict.fromkeys([*available_ids, *upcoming_ids, *rated_ids]))
    by_id = {app.pk: app for app in with_card_stats(base.filter(pk__in=wanted))} if wanted else {}
    def pack(rail_id, title, subtitle, icon, ids, more):
        apps = [by_id[pk] for pk in ids if pk in by_id]
        if not apps:
            return None
        return {"id": rail_id, "title": title, "subtitle": subtitle, "icon": icon, "apps": apps, "more": more}
    rails = [pack("available-apps", appearance.rail_new_title or "Nouvellement ajoutées", appearance.rail_new_subtitle or "Des apps à ouvrir, dès maintenant.", "sparkles", available_ids, available_more)]
    rails.append(pack("rated-apps", appearance.rail_rated_title or "Appréciées par la communauté", appearance.rail_rated_subtitle or "Le classement selon vos avis.", "star", rated_ids, rated_more))
    rails.append(pack("upcoming-apps", appearance.rail_follow_title or "Les projets à suivre", appearance.rail_follow_subtitle or "Les projets dont le lien reste à compléter.", "clock", upcoming_ids, upcoming_more))
    return [rail for rail in rails if rail], [by_id[pk] for pk in available_ids[:3] if pk in by_id]

def catalogue_url(request, number, fragment=False):
    params = request.GET.copy()
    if number:
        params["page"] = number
    else:
        params.pop("page", None)
    base = reverse("hub:catalogue") if fragment else reverse("hub:home")
    query = params.urlencode()
    return f"{base}?{query}" if fragment else f"{'?' + query if query else ''}#applications"

class CataloguePage:
    def __init__(self, number, has_next):
        self.number = number
        self.has_next = has_next
    def next_page_number(self):
        return self.number + 1

@require_GET
def home(request):
    visitor_count, visitor_token = visitor_stats(request)
    available_count = Application.objects.filter(status=Application.Status.PUBLISHED).exclude(website_url="").count()
    appearance = request.hub_appearance = HubAppearance.current()
    apps, query, category, favorites_only, sort = catalogue_filters(request, published_apps())
    spotlight, discovery_rails = [], []
    if not query and not category and not favorites_only and appearance.discovery_enabled:
        discovery_rails, spotlight = discovery_rails_for(appearance)
    layout = request.GET.get("affichage")
    if layout in {"grid", "list"}:
        request.session["catalogue_layout"] = layout
    else:
        layout = request.session.get("catalogue_layout", "grid")
    layout_urls = {}
    for mode in ["grid", "list"]:
        params = request.GET.copy()
        params["affichage"] = mode
        layout_urls[mode] = f"?{params.urlencode()}#applications"
    now = timezone.now()
    ads = list(Advertisement.objects.filter(is_active=True).exclude(image="").filter(
        Q(starts_at__isnull=True) | Q(starts_at__lte=now)).filter(Q(ends_at__isnull=True) | Q(ends_at__gt=now)))
    applications, has_next, number = catalogue_window(apps, request, sort)
    catalogue_page = CataloguePage(number, has_next)
    next_number = catalogue_page.next_page_number() if has_next else None
    shown = [app for rail in discovery_rails for app in rail["apps"]] + applications
    response = render(request, "hub/home.html", {"visitor_count": visitor_count, "available_count": available_count,"applications": applications, "catalogue_page": catalogue_page, "catalogue_next": catalogue_url(request, next_number, fragment=True) if next_number else "", "catalogue_more": catalogue_url(request, next_number) if next_number else "", "total": apps.count(), "favorite_ids": favorite_ids_for(request.user, shown),
        "query": query, "selected_category": category, "favorites_only": favorites_only, "categories": Category.objects.all(), "spotlight": spotlight, "sort": sort,
        "layout": layout, "layout_urls": layout_urls, "appearance": appearance, "discovery_rails": discovery_rails,
        "hero_slides": list(appearance.slides.filter(is_active=True)) if appearance.pk else [],
        "showcase_ads": [ad for ad in ads if ad.placement == Advertisement.Placement.HERO],
        "discovery_ads": [ad for ad in ads if ad.placement == Advertisement.Placement.DISCOVERY],
        "catalogue_ads": [ad for ad in ads if ad.placement == Advertisement.Placement.CATALOGUE]})
    return set_visitor_cookie(response, visitor_token)

@require_GET
def catalogue(request):
    apps, _query, _category, _favorites_only, sort = catalogue_filters(request, published_apps())
    applications, has_next, number = catalogue_window(apps, request, sort)
    next_number = number + 1 if has_next else None
    return render(request, "hub/_catalogue_page.html", {
        "applications": applications, "favorite_ids": favorite_ids_for(request.user, applications),
        "catalogue_next": catalogue_url(request, next_number, fragment=True) if next_number else ""})

@require_GET
def detail(request, slug):
    app = get_object_or_404(Application.objects.select_related("category"), slug=slug, status=Application.Status.PUBLISHED)
    return render(request, "hub/detail.html", detail_context(request, app))

def detail_context(request, app, review_form=None):
    favorite = request.user.is_authenticated and Favorite.objects.filter(user=request.user, application=app).exists()
    reviews = app.reviews.filter(is_visible=True).select_related("user")
    stats = reviews.aggregate(average=Avg("rating"), count=Count("id"))
    distribution = {row["rating"]: row["count"] for row in reviews.order_by().values("rating").annotate(count=Count("id"))}
    bars = [{"rating": i, "count": distribution.get(i, 0), "percent": round(distribution.get(i, 0) * 100 / (stats["count"] or 1))} for i in range(5, 0, -1)]
    own_review = app.reviews.filter(user=request.user).first() if request.user.is_authenticated else None
    return {"application": app, "is_favorite": favorite,
        "review_stats": stats, "review_bars": bars, "review_page": Paginator(reviews, 10).get_page(request.GET.get("page")),
        "own_review": own_review, "review_form": review_form if review_form is not None else ReviewForm(instance=own_review)}

@login_required
@require_POST
def save_review(request, slug):
    app = get_object_or_404(Application, slug=slug, status=Application.Status.PUBLISHED)
    existing = Review.objects.filter(application=app, user=request.user).first()
    if existing and not existing.is_visible:
        messages.info(request, "Votre avis a été masqué par la modération. Contactez l'administration pour son réexamen.")
        return redirect(f"{app.get_absolute_url()}#avis")
    form = ReviewForm(request.POST)
    if form.is_valid():
        Review.objects.update_or_create(application=app, user=request.user, defaults=form.cleaned_data)
        messages.success(request, "Merci ! Votre avis a été enregistré.")
    else:
        return render(request, "hub/detail.html", detail_context(request, app, form), status=400)
    return redirect(f"{app.get_absolute_url()}#avis")

@login_required
@require_POST
def delete_review(request, slug):
    app = get_object_or_404(Application, slug=slug, status=Application.Status.PUBLISHED)
    Review.objects.filter(application=app, user=request.user).delete()
    messages.success(request, "Votre avis a été supprimé.")
    return redirect(f"{app.get_absolute_url()}#avis")

@login_required
@require_POST
def toggle_favorite(request, public_id):
    app = get_object_or_404(Application, public_id=public_id, status=Application.Status.PUBLISHED)
    favorite, created = Favorite.objects.get_or_create(user=request.user, application=app)
    if not created: favorite.delete()
    if request.headers.get("X-Requested-With") == "fetch":
        return JsonResponse({"liked": created})
    next_url = request.POST.get("next", reverse("hub:home"))
    if not url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()}, require_https=request.is_secure()): next_url = reverse("hub:home")
    return redirect(next_url)

def signup(request):
    if request.user.is_authenticated: return redirect("hub:dashboard")
    form = SignupForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        login(request, user)
        messages.success(request, "Votre compte est créé. Bienvenue dans le hub !")
        return redirect("hub:dashboard")
    return render(request, "registration/signup.html", {"form": form})

@login_required
@require_GET
def dashboard(request):
    apps = Application.objects.filter(submitted_by=request.user).select_related("category").prefetch_related("payments").order_by("-created_at")
    return render(request, "hub/dashboard.html", {"applications": apps})

@login_required
def submit_application(request):
    if request.user.is_staff: return redirect("admin:hub_application_add")
    form = ApplicationForm(request.POST or None, request.FILES or None)
    if request.method == "POST" and form.is_valid():
        app = form.save(commit=False)
        app.submitted_by = request.user
        app.fee_amount = HubAppearance.current().submission_fee
        app.slug = f"{slugify(app.name)[:65] or 'application'}-{uuid.uuid4().hex[:10]}"
        app.status = Application.Status.DRAFT
        app.is_admin_added = False
        app.save()
        return redirect("hub:submission", public_id=app.public_id)
    return render(request, "hub/submit.html", {"form": form})

@login_required
@require_GET
def submission(request, public_id):
    app = get_object_or_404(Application.objects.select_related("category"), public_id=public_id, submitted_by=request.user)
    return render(request, "hub/submission.html", {"application": app, "payments": app.payments.all(), "paid": app.paid, "singpay_ready": singpay_service.is_configured})

@login_required
@require_POST
def confirm_submission(request, public_id):
    app = get_object_or_404(Application, public_id=public_id, submitted_by=request.user)
    if request.POST.get("confirm") != "yes":
        messages.error(request, "Cochez la confirmation après avoir relu toutes les informations.")
        return redirect("hub:submission", public_id=app.public_id)
    try:
        app.publish_by_creator()
    except ValidationError as error:
        messages.error(request, " ".join(error.messages))
        return redirect("hub:submission", public_id=app.public_id)
    messages.success(request, "Votre application est publiée sur le Hub.")
    return redirect(f"{reverse('hub:submission', args=[app.public_id])}?published=1")

@login_required
def edit_submission(request, public_id):
    app = get_object_or_404(Application, public_id=public_id, submitted_by=request.user, status__in=[Application.Status.DRAFT, Application.Status.REJECTED])
    if app.payments.filter(status=Payment.Status.PENDING).exists():
        messages.info(request, "Terminez la vérification du paiement avant de modifier cette fiche.")
        return redirect("hub:submission", public_id=app.public_id)
    form = ApplicationForm(request.POST or None, request.FILES or None, instance=app)
    if request.method == "POST" and form.is_valid():
        app = form.save(commit=False)
        app.status = Application.Status.DRAFT
        app.moderation_note = ""
        app.save()
        messages.success(request, "Fiche mise à jour. Relisez-la puis confirmez la publication." if app.paid else "Fiche mise à jour.")
        return redirect("hub:submission", public_id=app.public_id)
    return render(request, "hub/submit.html", {"form": form, "editing": True, "application": app, "submission_fee": app.fee_amount})

@login_required
@require_POST
def checkout(request, public_id):
    app = get_object_or_404(Application, public_id=public_id, submitted_by=request.user)
    if request.POST.get("accept") != "yes":
        messages.error(request, f"Confirmez le montant de {app.fee_amount} FCFA avant de continuer vers Paiement Mobile.")
        return redirect("hub:submission", public_id=app.public_id)
    try:
        payment = start_checkout(app, request.user)
    except PaymentUnavailable as exc:
        return render(request, "hub/payment_unavailable.html", {"application": app, "reason": str(exc)}, status=503)
    except (ValidationError, IntegrityError):
        messages.info(request, "Un paiement ou une validation existe déjà. Vérifiez son état.")
        return redirect("hub:submission", public_id=app.public_id)
    if payment.status == Payment.Status.PENDING and checkout_url_is_safe(payment.checkout_url): return redirect(payment.checkout_url)
    return redirect("hub:payment-return", public_id=payment.public_id)

@login_required
@require_GET
def payment_return(request, public_id):
    payment = get_object_or_404(Payment.objects.select_related("application"), public_id=public_id, user=request.user)
    return render(request, "hub/payment_return.html", {"payment": payment})

@login_required
@require_POST
def check_payment(request, public_id):
    payment = get_object_or_404(Payment, public_id=public_id, user=request.user)
    messages.info(request, verify_payment(payment))
    return redirect("hub:payment-return", public_id=payment.public_id)

@csrf_exempt
@require_POST
def singpay_callback(request):
    if len(request.body) > 65536: return JsonResponse({"ok": False}, status=413)
    try:
        raw = request.body.decode("utf-8")
        payload = json.loads(raw)
    except (UnicodeDecodeError, json.JSONDecodeError): return JsonResponse({"ok": False}, status=400)
    if not isinstance(payload, dict): return JsonResponse({"ok": False}, status=400)
    valid = singpay_service.verify_webhook_signature(raw, request.headers.get("X-Signature", ""), request.headers.get("X-Timestamp", ""))
    ref = normalize_reference(payload.get("reference") or payload.get("order_id") or payload.get("ref"))
    event = PaymentEvent.objects.create(reference=ref[:100], signature_valid=valid, result="reçu" if valid else "signature invalide")
    if not valid: return JsonResponse({"ok": False}, status=400)
    payment = Payment.objects.filter(reference=ref).first() if ref else None
    if not payment:
        provider_id = str(payload.get("transaction_id") or payload.get("id") or payload.get("transactionId") or "").strip()
        payment = Payment.objects.filter(provider_transaction_id=provider_id).first() if provider_id else None
    if not payment:
        event.result = "transaction inconnue"
        event.save(update_fields=["result"])
        return JsonResponse({"ok": True, "matched": False})
    event.result = verify_payment(payment)[:120]
    event.save(update_fields=["result"])
    return JsonResponse({"ok": payment.status != Payment.Status.PENDING}, status=503 if payment.status == Payment.Status.PENDING else 200)
