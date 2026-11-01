from django import template
from django.db.models import Count, Q, Sum, Exists, OuterRef
from django.db.models.functions import TruncDate
from datetime import timedelta
from django.contrib.admin.models import LogEntry
from django.urls import reverse
from django.utils import timezone
from django.utils.html import format_html
from django.utils.safestring import mark_safe
register = template.Library()

@register.filter
def fcfa(value):
    return f"{int(value):,}".replace(",", "\u202f") + " FCFA"

# Tracés locaux partagés : aucun script ni téléchargement d'icônes externe.
ICONS = {
    "grid": '<rect x="3" y="3" width="7" height="7" rx="2"/><rect x="14" y="3" width="7" height="7" rx="2"/><rect x="3" y="14" width="7" height="7" rx="2"/><rect x="14" y="14" width="7" height="7" rx="2"/>',
    "user": '<circle cx="12" cy="8" r="3.5"/><path d="M5 21v-2a7 7 0 0 1 14 0v2"/>',
    "lock": '<rect x="5" y="10" width="14" height="11" rx="3"/><path d="M8 10V7a4 4 0 0 1 8 0v3m-4 5v2"/>',
    "mail": '<rect x="3" y="5" width="18" height="14" rx="3"/><path d="m3 7 9 6 9-6"/>',
    "phone": '<path d="M7 3h4l1 4-2 1a12 12 0 0 0 6 6l1-2 4 1v4a2 2 0 0 1-2 2A16 16 0 0 1 5 5a2 2 0 0 1 2-2Z"/>',
    "download": '<path d="M12 4v10m0 0 4-4m-4 4-4-4M5 19h14"/>',
    "link": '<path d="m10 13 4-4m-6 7-1 1a4 4 0 0 1-6-6l4-4a4 4 0 0 1 6 0m2 0 1-1a4 4 0 0 1 6 6l-4 4a4 4 0 0 1-6 0" transform="translate(1 1)"/>',
    "image": '<rect x="3" y="3" width="18" height="18" rx="4"/><circle cx="8" cy="8" r="1.5"/><path d="m3 17 5-5 4 4 4-6 5 7"/>',
    "text": '<path d="M4 5h16M4 10h16M4 15h12M4 20h8"/>',
    "pin": '<path d="M19 10c0 5-7 11-7 11S5 15 5 10a7 7 0 0 1 14 0Z"/><circle cx="12" cy="10" r="2"/>',
    "palette": '<circle cx="8" cy="9" r=".7"/><circle cx="12" cy="6" r=".7"/><circle cx="16" cy="9" r=".7"/><path d="M12 3a9 9 0 1 0 0 18h2a2 2 0 0 0 1-4c-2-1-1-3 1-3h2a3 3 0 0 0 3-3 9 9 0 0 0-9-8Z"/>',
    "check": '<path d="m5 12 4 4L19 6"/>',
    "shield": '<path d="m12 3 8 3v6c0 5-8 9-8 9s-8-4-8-9V6Z"/><path d="m8 12 3 3 5-6"/>',
    "heart": '<path d="M20.8 4.6a5.5 5.5 0 0 0-7.8 0L12 5.7l-1.1-1.1a5.5 5.5 0 0 0-7.8 7.8L12 21l8.8-8.6a5.5 5.5 0 0 0 0-7.8Z"/>',
    "star": '<path d="m12 3 2.8 5.7 6.2.9-4.5 4.4 1.1 6.2L12 17.3l-5.6 2.9 1.1-6.2L3 9.6l6.2-.9Z"/>',
    "plus": '<path d="M12 5v14M5 12h14"/>',
    "arrow": '<path d="M5 12h14m-6-6 6 6-6 6"/>',
    "back": '<path d="M19 12H5m6-6-6 6 6 6"/>',
    "external": '<path d="M7 17 17 7M7 7h10v10"/>',
    "chevron-left": '<path d="m15 5-7 7 7 7"/>',
    "chevron-right": '<path d="m9 5 7 7-7 7"/>',
    "logout": '<path d="M9 4H5v16h4m1-8h11m-4-4 4 4-4 4"/>',
    "login": '<path d="M15 4h4v16h-4M3 12h11m-4-4 4 4-4 4"/>',
    "refresh": '<path d="M20 7v5h-5M4 17v-5h5"/><path d="M6 7a7 7 0 0 1 12-1l2 6M4 12l2 6a7 7 0 0 0 12-1"/>',
    "wallet": '<path d="M19 7V4H6a3 3 0 0 0 0 6h15v10H6a3 3 0 0 1-3-3V7m18 6h-5v4h5"/>',
    "edit": '<path d="m15 4 5 5M4 20l5-1L21 7a2 2 0 0 0-5-4L4 15Z"/>',
    "message": '<path d="M5 4h14a2 2 0 0 1 2 2v10a2 2 0 0 1-2 2H9l-6 4V6a2 2 0 0 1 2-2Z"/><path d="M7 9h10M7 13h6"/>',
    "trash": '<path d="M3 6h18M9 6V3h6v3M5 6l1 15h12l1-15M10 10v7m4-7v7"/>',
    "eye": '<path d="M2 12s4-7 10-7 10 7 10 7-4 7-10 7S2 12 2 12Z"/><circle cx="12" cy="12" r="3"/>',
    "filter": '<path d="M3 5h18M6 12h12M10 19h4"/>',
    "sparkles": '<path d="m12 3 2.5 6.5L21 12l-6.5 2.5L12 21l-2.5-6.5L3 12l6.5-2.5Z"/>',
    "clock": '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>',
    "search": '<circle cx="10" cy="10" r="7"/><path d="m15 15 6 6"/>',
    "bell": '<path d="M6 16V11a6 6 0 1 1 12 0v5l1.5 2h-15L6 16Z"/><path d="M10 19a2 2 0 0 0 4 0"/>',
}

@register.simple_tag
def ui_icon(name):
    return format_html('<svg class="ui-icon" viewBox="0 0 24 24" aria-hidden="true" focusable="false">{}</svg>', mark_safe(ICONS.get(name, ICONS["grid"])))

MODEL_ICONS = {
    "Application": "grid",
    "Category": "filter",
    "Favorite": "heart",
    "Payment": "wallet",
    "PaymentEvent": "clock",
    "Review": "star",
    "HubAppearance": "palette",
    "CatalogueFilter": "filter",
    "Advertisement": "image",
    "HubVisitor": "eye",
    "User": "user",
    "Group": "shield",
}

@register.simple_tag
def model_icon(object_name):
    return ui_icon(MODEL_ICONS.get(object_name, "chevron-right"))

@register.simple_tag
def field_icon(name):
    mapping = {"username": "user", "email": "mail", "name": "grid", "category": "grid", "creator_name": "user", "creator_city": "pin", "description": "text", "about": "text", "website_url": "link", "logo": "image", "banner": "image", "color": "palette", "confirmation": "shield", "comment": "message", "rating": "star"}
    return ui_icon("lock" if "password" in name else mapping.get(name, "text"))


@register.filter
def payment_label(value):
    return str(value).replace("SingPay", "Paiement Mobile").replace("SINGPAY", "PAIEMENT MOBILE")


def _daily_series(qs, date_field, days=14, amount_field=None):
    today = timezone.localdate()
    start = today - timedelta(days=days - 1)
    rows = qs.filter(**{f"{date_field}__date__gte": start}).annotate(d=TruncDate(date_field))
    mapped = {}
    if amount_field:
        for row in rows.values("d").annotate(n=Count("id"), t=Sum(amount_field)):
            mapped[row["d"]] = {"n": row["n"] or 0, "t": row["t"] or 0}
    else:
        for row in rows.values("d").annotate(n=Count("id")):
            mapped[row["d"]] = {"n": row["n"] or 0, "t": 0}
    series = []
    peak = 1
    for i in range(days):
        day = start + timedelta(days=i)
        rec = mapped.get(day, {"n": 0, "t": 0})
        val = int(rec["t"] or 0) if amount_field else rec["n"]
        peak = max(peak, val)
        series.append({"label": day.strftime("%d/%m"), "n": rec["n"], "t": rec["t"] or 0, "val": val})
    for item in series:
        item["pct"] = max(6, int(round((item["val"] / peak) * 100))) if item["val"] else 6
    return series


@register.simple_tag(takes_context=True)
def console_overview(context):
    from hub.models import Application, Payment, Advertisement, Review, HubAppearance, HubVisitor, SubmissionNotice
    user = context["request"].user
    can_apps = user.has_perm("hub.view_application")
    can_pay = user.has_perm("hub.view_payment")
    can_ads = user.has_perm("hub.view_advertisement")
    can_reviews = user.has_perm("hub.view_review")
    can_settings = user.has_perm("hub.view_hubappearance") or user.has_perm("hub.change_hubappearance")
    can_filters = user.has_perm("hub.view_cataloguefilter") or user.has_perm("hub.change_cataloguefilter")

    apps_published = Application.objects.filter(status="published").count() if can_apps else 0
    apps_review = Application.objects.filter(status="review").count() if can_apps else 0
    apps_draft = Application.objects.filter(status="draft").count() if can_apps else 0
    apps_rejected = Application.objects.filter(status="rejected").count() if can_apps else 0

    pay_pending = Payment.objects.filter(status="pending") if can_pay else Payment.objects.none()
    pay_success = Payment.objects.filter(status="success") if can_pay else Payment.objects.none()
    pending_count = pay_pending.count() if can_pay else 0
    pending_amount = (pay_pending.aggregate(total=Sum("amount"))["total"] or 0) if can_pay else 0
    success_count = pay_success.count() if can_pay else 0
    revenue = (pay_success.aggregate(total=Sum("amount"))["total"] or 0) if can_pay else 0
    ads_active = Advertisement.objects.filter(is_active=True).count() if can_ads else 0

    recent_apps = list(
        Application.objects.select_related("category", "submitted_by")
        .annotate(payment_ok=Exists(Payment.objects.filter(application=OuterRef("pk"), status="success", amount=OuterRef("fee_amount"), currency="XAF", verified_at__isnull=False, valid_until__gt=timezone.now())))
        .order_by("-created_at")[:6]
    ) if can_apps else []

    recent_payments = list(
        Payment.objects.select_related("application", "user").order_by("-created_at")[:6]
    ) if can_pay else []

    recent_logs = list(LogEntry.objects.select_related("user", "content_type").order_by("-action_time")[:8]) if user.is_staff else []
    chart_apps = _daily_series(Application.objects.all(), "created_at") if can_apps else []
    chart_payments = _daily_series(Payment.objects.filter(status="success"), "created_at", amount_field="amount") if can_pay else []

    appearance_obj = HubAppearance.objects.first() if can_settings else None
    settings_url = (reverse("admin:hub_hubappearance_change", args=[appearance_obj.pk]) if appearance_obj else reverse("admin:hub_hubappearance_add")) if can_settings else ""

    return {
        "can_apps": can_apps,
        "can_pay": can_pay,
        "can_ads": can_ads,
        "can_reviews": can_reviews,
        "can_settings": can_settings,
        "can_filters": can_filters,
        "apps_published": apps_published,
        "apps_review": apps_review,
        "apps_draft": apps_draft,
        "apps_rejected": apps_rejected,
        "notices_unread": SubmissionNotice.objects.filter(seen_at__isnull=True).count() if can_apps else 0,
        "pending_count": pending_count,
        "pending_amount": pending_amount,
        "success_count": success_count,
        "revenue": revenue,
        "ads_active": ads_active,
        "reviews_count": Review.objects.filter(is_visible=True).count() if can_reviews else 0,
        "recent_apps": recent_apps,
        "recent_payments": recent_payments,
        "recent_logs": recent_logs,
        "chart_apps": chart_apps,
        "chart_payments": chart_payments,
        "settings_url": settings_url,
        "visitor_count": HubVisitor.objects.count() if user.is_staff else 0,
        "can_edit_logo": user.has_perm("hub.change_hubappearance"),
        "logo_url": appearance_obj.logo.url if appearance_obj and appearance_obj.logo else "",
    }


@register.simple_tag(takes_context=True)
def console_metrics(context):
    from django.urls import reverse
    from hub.models import Application, Payment, Advertisement, HubVisitor, SubmissionNotice
    user = context['request'].user
    result = []
    if user.is_staff:
        result.append({'label': 'Visiteurs uniques', 'value': HubVisitor.objects.count(), 'help': 'Un cookie par navigateur', 'icon': 'eye', 'url': reverse('admin:index')})
    if user.has_perm('hub.view_application'):
        result.extend([
            {'label': 'Applications publiées', 'value': Application.objects.filter(status='published').count(), 'help': 'Explorer le catalogue', 'icon': 'grid', 'url': reverse('admin:hub_application_changelist') + '?status__exact=published'},
            {'label': 'Nouvelles publications', 'value': SubmissionNotice.objects.filter(seen_at__isnull=True).count(), 'help': 'Fiches confirmées à lire', 'icon': 'bell', 'url': reverse('admin:hub_application_notices')},
        ])
    if user.has_perm('hub.view_payment'):
        result.append({'label': 'Paiements en attente', 'value': Payment.objects.filter(status='pending').count(), 'help': 'Vérifier les transactions', 'icon': 'wallet', 'url': reverse('admin:hub_application_workflow') + '?stage=pending' if user.has_perm('hub.view_application') else reverse('admin:hub_payment_changelist') + '?status__exact=pending'})
        result.append({'label': 'Paiements confirmés', 'value': Payment.objects.filter(status='success').count(), 'help': 'Suivre les paiements', 'icon': 'shield', 'url': reverse('admin:hub_payment_changelist') + '?status__exact=success'})
    if user.has_perm('hub.view_advertisement'):
        result.append({'label': 'Publicités activées', 'value': Advertisement.objects.filter(is_active=True).count(), 'help': 'Gérer la visibilité', 'icon': 'image', 'url': reverse('admin:hub_advertisement_changelist')})
    return result


@register.simple_tag
def unread_notice_count():
    from hub.models import SubmissionNotice
    return SubmissionNotice.objects.filter(seen_at__isnull=True).count()


@register.filter
def compact_count(value):
    """Compact lower bound, never round up to an unreached threshold."""
    number = max(0, int(value or 0))
    for divisor, suffix in ((1000000000, 'Md'), (1000000, 'M'), (1000, 'k')):
        if number >= divisor:
            tenths = number * 10 // divisor
            whole, decimal = divmod(tenths, 10)
            label = str(whole) + (',' + str(decimal) if decimal else '')
            return label + ' ' + suffix + '+'
    return str(number) + '+'
