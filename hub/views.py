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

@require_GET
def home(request):
    visitor_count, visitor_token = visitor_stats(request)
    available_count = Application.objects.filter(status=Application.Status.PUBLISHED).exclude(website_url="").count()
    appearance = request.hub_appearance = HubAppearance.current()
    apps = Application.objects.filter(status=Application.Status.PUBLISHED).select_related("category").annotate(
        average_rating=Avg("reviews__rating", filter=Q(reviews__is_visible=True)),
        review_count=Count("reviews", filter=Q(reviews__is_visible=True)))
    query = request.GET.get("q", "").strip()[:120]
    category = request.GET.get("categorie", "")[:60]
    favorites_only = request.GET.get("vue") == "favoris"
    spotlight, discovery_rails = [], []
    if not query and not category and not favorites_only:
        available = list(apps.exclude(website_url="").order_by("-created_at")[:8])
        spotlight = available[:3]
        discovery_rails = [
            {"id": "available-apps", "title": "Nouvellement ajoutées", "subtitle": "Des apps à ouvrir, dès maintenant.", "icon": "sparkles", "apps": available},
            {"id": "upcoming-apps", "title": "Les projets à suivre", "subtitle": "Les projets dont le lien reste à compléter.", "icon": "clock", "apps": list(apps.filter(website_url="").order_by("-created_at")[:8])},
        ]
        rated_apps = list(apps.filter(review_count__gt=0).order_by("-average_rating", "-review_count")[:8])
        if rated_apps:
            discovery_rails.insert(1, {"id": "rated-apps", "title": "Appréciées par la communauté", "subtitle": "Le classement selon vos avis.", "icon": "star", "apps": rated_apps})
    sort = request.GET.get("tri", "recent")
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
    favorites = set(Favorite.objects.filter(user=request.user).values_list("application_id", flat=True)) if request.user.is_authenticated else set()
    if query: apps = apps.filter(Q(name__icontains=query) | Q(description__icontains=query) | Q(category__name__icontains=query))
    if category: apps = apps.filter(category__slug=category)
    if favorites_only: apps = apps.filter(pk__in=favorites)
    total = apps.count()
    apps = apps.order_by("-average_rating", "-review_count", "name") if sort == "rating" else apps.order_by("-created_at", "name")
    response = render(request, "hub/home.html", {"visitor_count": visitor_count, "available_count": available_count,"applications": apps, "total": total, "favorite_ids": favorites,
        "query": query, "selected_category": category, "favorites_only": favorites_only, "categories": Category.objects.all(), "spotlight": spotlight, "sort": sort,
        "layout": layout, "layout_urls": layout_urls, "appearance": appearance, "discovery_rails": discovery_rails if appearance.discovery_enabled else [],
        "showcase_ads": [ad for ad in ads if ad.placement == Advertisement.Placement.HERO],
        "discovery_ads": [ad for ad in ads if ad.placement == Advertisement.Placement.DISCOVERY],
        "catalogue_ads": [ad for ad in ads if ad.placement == Advertisement.Placement.CATALOGUE]})
    return set_visitor_cookie(response, visitor_token)

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
def edit_submission(request, public_id):
    app = get_object_or_404(Application, public_id=public_id, submitted_by=request.user, status__in=[Application.Status.DRAFT, Application.Status.REJECTED])
    if app.payments.filter(status=Payment.Status.PENDING).exists():
        messages.info(request, "Terminez la vérification du paiement avant de modifier cette fiche.")
        return redirect("hub:submission", public_id=app.public_id)
    form = ApplicationForm(request.POST or None, request.FILES or None, instance=app)
    if request.method == "POST" and form.is_valid():
        app = form.save(commit=False)
        app.status = Application.Status.REVIEW if app.paid else Application.Status.DRAFT
        app.moderation_note = ""
        app.save()
        messages.success(request, "Fiche mise à jour. Une fiche déjà payée est renvoyée en validation sans nouveau paiement.")
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
