from django import forms
from django.contrib import admin, messages
from django.contrib.admin.views.main import ChangeList
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Count, Exists, OuterRef
from django.http import HttpResponseForbidden, HttpResponseRedirect, JsonResponse
from django.urls import reverse
from django.utils import timezone
from django.utils.html import format_html
from .models import Application, Category, CatalogueFilter, Favorite, HeroSlide, Payment, PaymentEvent, Review, HubAppearance, Advertisement, covering_payments
from .images import ApplicationImagesMixin, PublicImageField
from .payments.services import verify_payment

admin.site.site_header = "Gaboma Hub · Administration"
admin.site.site_title = "Gaboma Hub"
admin.site.index_title = "Applications, modération et paiements"


def console_badge(text, tone="soft"):
    return format_html('<span class="console-pill is-{}">{}</span>', tone, text)


class AppearanceForm(forms.ModelForm):
    logo = PublicImageField(label="Logo du Hub", required=False,
        help_text="JPG, PNG ou WebP · 5 Mo maximum. Format carré conseillé : 512 × 512. Il remplace le symbole en haut du site.")
    hero_background = PublicImageField(label="Image de fond du Hero", required=False,
        help_text="JPG, PNG ou WebP · 5 Mo maximum. Format paysage conseillé : 1920 × 1080. Utilisée seulement s'il n'y a aucune image de carrousel.")
    android_app = forms.FileField(label="Application Android", required=False,
        widget=forms.ClearableFileInput(attrs={"accept": ".apk"}),
        help_text="Fichier .apk · 80 Mo maximum. Sur Android, ce fichier est proposé à la place de l'application web.")
    ios_app = forms.FileField(label="Application Apple", required=False,
        widget=forms.ClearableFileInput(attrs={"accept": ".ipa"}),
        help_text="Fichier .ipa · 80 Mo maximum. Sur iPhone, ce fichier est proposé à la place de l'ajout à l'écran d'accueil.")
    class Meta:
        model = HubAppearance
        fields = "__all__"

    def _native_file(self, upload, extension, label):
        if not upload:
            return upload
        name = (getattr(upload, "name", "") or "").lower()
        if not name.endswith(extension):
            raise forms.ValidationError(f"Déposez un fichier {label} ({extension}).")
        size = getattr(upload, "size", 0) or 0
        if size > 80 * 1024 * 1024:
            raise forms.ValidationError("Le fichier doit peser au maximum 80 Mo.")
        return upload

    def clean_android_app(self):
        return self._native_file(self.cleaned_data.get("android_app"), ".apk", "Android")

    def clean_ios_app(self):
        return self._native_file(self.cleaned_data.get("ios_app"), ".ipa", "Apple")

class HubLogoForm(forms.Form):
    logo = PublicImageField(label="Logo du Hub", widget=forms.FileInput(attrs={"accept": "image/png,image/jpeg,image/webp"}))

class HeroSlideForm(forms.ModelForm):
    image = PublicImageField(label="Image", help_text="JPG, PNG ou WebP · 5 Mo maximum. Format paysage conseillé : 1600 × 900. Les images défilent dans le hero.")
    class Meta:
        model = HeroSlide
        fields = "__all__"

class HeroSlideInline(admin.StackedInline):
    model = HeroSlide
    form = HeroSlideForm
    extra = 1
    fields = ["image", "alt", "order", "is_active"]

@admin.register(HubAppearance)
class AppearanceAdmin(admin.ModelAdmin):
    form = AppearanceForm
    list_display = ["__str__", "site_name", "fee_badge", "showcase_badge", "updated_short"]
    readonly_fields = ["updated_at"]
    @admin.display(description="Tarif créateur")
    def fee_badge(self, obj):
        return console_badge(f"{obj.submission_fee} FCFA / an", "blue")
    @admin.display(description="Vitrine & rails")
    def showcase_badge(self, obj):
        return console_badge("Vitrine active" if obj.showcase_enabled else "Vitrine masquée", "ok" if obj.showcase_enabled else "muted")
    @admin.display(description="Mis à jour", ordering="updated_at")
    def updated_short(self, obj):
        return timezone.localtime(obj.updated_at).strftime("%d %b %Y · %H:%M") if obj.updated_at else "—"
    inlines = [HeroSlideInline]

    def get_urls(self):
        from django.urls import path
        return [path("logo/", self.admin_site.admin_view(self.upload_logo), name="hub_hubappearance_logo")] + super().get_urls()

    def upload_logo(self, request):
        if request.method != "POST":
            return HttpResponseRedirect(reverse("admin:index"))
        if not request.user.has_perm("hub.change_hubappearance"):
            return HttpResponseForbidden("Vous ne pouvez pas modifier le logo.")
        form = HubLogoForm(request.POST, request.FILES)
        if form.is_valid():
            appearance = HubAppearance.objects.first() or HubAppearance()
            appearance.logo = form.cleaned_data["logo"]
            appearance.save()
            messages.success(request, "Le logo du Hub est enregistré. Il apparaît en haut du site.")
        else:
            messages.error(request, "Le logo n'a pas été enregistré. Utilisez un JPG, PNG ou WebP de 5 Mo maximum.")
        return HttpResponseRedirect(reverse("admin:index"))
    fieldsets = [
        ("Identité", {"fields": ["logo", ("site_name", "art_caption"), "document_title", "meta_description"], "description": "Ces textes sont utilisés sur le site public. Les clés de paiement restent dans la configuration du serveur."}),
        ("Texte de l'accueil", {"fields": ["hero_badge", ("hero_title", "hero_subtitle"), "hero_description", ("hero_primary_label", "hero_secondary_label"), "territory_line"]}),
        ("Répertoire", {"fields": [("catalogue_kicker", "catalogue_title"), "catalogue_note", ("rail_new_title", "rail_new_subtitle"), ("rail_rated_title", "rail_rated_subtitle"), ("rail_follow_title", "rail_follow_subtitle"), ("showcase_enabled", "discovery_enabled")], "description": "Les cartes de filtre se gèrent dans Filtres d'accueil. Les carrousels se masquent sans effacer leurs titres."}),
        ("Créateurs", {"fields": [("creator_kicker", "submission_fee"), ("creator_title", "creator_emphasis"), "creator_text"], "description": "L'abonnement dure un an à compter de la confirmation du paiement. Le tarif s'applique aux nouvelles souscriptions et aux renouvellements. Le même montant se règle aussi depuis Paiements mobiles."}),
        ("Contact et pied de page", {"fields": [("footer_lead", "footer_colophon"), ("support_email", "support_phone", "whatsapp_number"), ("facebook_url", "instagram_url"), ("tiktok_url", "linkedin_url", "x_url")], "description": "Un lien n'apparaît dans le pied de page que s'il est renseigné."}),
        ("Applications mobiles", {"fields": ["android_app", "ios_app"], "description": "Déposez l'application Android (.apk) et l'application Apple (.ipa) si elles existent. Sans fichier pour le téléphone du visiteur, un clic sur Installer lance l'application web."}),
        ("Visuels", {"fields": ["hero_background", "hero_background_enabled"], "description": "Ajoutez les images du carrousel dans le bloc Images du hero, sous ce formulaire. Sans image active, le fond unique ci-dessus est affiché."}),
        ("Suivi", {"fields": ["updated_at"]}),
    ]
    def has_add_permission(self, request):
        return super().has_add_permission(request) and not HubAppearance.objects.exists()
    def has_delete_permission(self, request, obj=None): return False

class AdvertisementForm(forms.ModelForm):
    image = PublicImageField(label="Visuel publicitaire", help_text="JPG, PNG ou WebP · 5 Mo maximum. Vitrine : format paysage 1200 × 700 px. Autres emplacements : 1600 × 500 px. Le visuel entier reste visible sur mobile.")
    class Meta:
        model = Advertisement
        fields = "__all__"

@admin.register(Advertisement)
class AdvertisementAdmin(admin.ModelAdmin):
    form = AdvertisementForm
    list_display = ["title", "visual_preview", "placement_badge", "sponsor_label", "schedule_label", "is_active", "order"]
    list_display_links = ["title"]
    readonly_fields = ["visual_preview"]
    @admin.display(description="Aperçu")
    def visual_preview(self, obj):
        if not obj or not obj.image:
            return console_badge("Aucun visuel", "muted")
        return format_html('<img src="{}" alt="Aperçu" class="console-thumb">', obj.image.url)
    @admin.display(description="Emplacement", ordering="placement")
    def placement_badge(self, obj):
        tone = "blue" if obj.placement == "hero" else "soft"
        return console_badge(obj.get_placement_display(), tone)
    @admin.display(description="Annonceur", ordering="sponsor")
    def sponsor_label(self, obj):
        return obj.sponsor or "Gaboma Hub"
    @admin.display(description="Période")
    def schedule_label(self, obj):
        if not obj.starts_at and not obj.ends_at:
            return console_badge("Permanente", "ok")
        start = timezone.localtime(obj.starts_at).strftime("%d/%m/%Y") if obj.starts_at else "Dès maintenant"
        end = timezone.localtime(obj.ends_at).strftime("%d/%m/%Y") if obj.ends_at else "Sans fin"
        return f"{start} → {end}"
    list_filter = ["is_active", "placement"]
    search_fields = ["title", "sponsor"]
    list_editable = ["is_active", "order"]
    fieldsets = [("Contenu", {"fields": [("title", "sponsor"), "image", "visual_preview", "target_url"]}),
        ("Diffusion", {"fields": [("placement", "order"), "is_active", ("starts_at", "ends_at")],
        "description": "Laisser les dates vides pour une diffusion sans limite. Une annonce doit être activée pour apparaître."})]

class AdminApplicationForm(ApplicationImagesMixin, forms.ModelForm):
    logo = ApplicationImagesMixin.logo
    banner = ApplicationImagesMixin.banner
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["logo"].required = not bool(self.instance.pk)
        self.fields["banner"].required = not bool(self.instance.pk)
    class Meta:
        model = Application
        fields = "__all__"
    def clean(self):
        cleaned = super().clean()
        if not self.instance.pk:
            self.instance.is_admin_added = True
        return cleaned

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ["name", "slug", "apps_count", "order"]
    list_editable = ["order"]
    search_fields = ["name", "slug"]
    prepopulated_fields = {"slug": ("name",)}
    def get_queryset(self, request):
        return super().get_queryset(request).annotate(_apps_count=Count("application"))
    @admin.display(description="Applications", ordering="_apps_count")
    def apps_count(self, obj):
        count = getattr(obj, "_apps_count", 0)
        return console_badge(f"{count} app{'s' if count > 1 else ''}", "blue" if count else "muted")

@admin.register(CatalogueFilter)
class CatalogueFilterAdmin(admin.ModelAdmin):
    list_display = ["label", "category", "tone_badge", "icon", "order", "is_active"]
    list_editable = ["order", "is_active"]
    list_filter = ["is_active", "tone"]
    search_fields = ["label", "category__name"]
    autocomplete_fields = ["category"]
    @admin.display(description="Couleur", ordering="tone")
    def tone_badge(self, obj):
        tones = {"mint": "ok", "blue": "blue", "gold": "warn", "ice": "soft"}
        return console_badge(obj.get_tone_display(), tones.get(obj.tone, "soft"))
    fieldsets = [("Carte de l'accueil", {"fields": [("label", "category"), ("icon", "tone"), ("order", "is_active")],
        "description": "Un clic sur la carte ouvre le répertoire filtré sur la catégorie choisie. Décochez la carte pour la retirer sans supprimer la catégorie."})]

class PaymentCoverageFilter(admin.SimpleListFilter):
    title = "abonnement"
    parameter_name = "abonnement"

    def lookups(self, request, model_admin):
        return (("jour", "À jour"), ("regler", "À régler"), ("offert", "Offert"))

    def queryset(self, request, queryset):
        if self.value() == "offert":
            return queryset.filter(is_admin_added=True)
        if self.value() == "jour":
            return queryset.filter(is_admin_added=False, payment_ok=True)
        if self.value() == "regler":
            return queryset.filter(is_admin_added=False, payment_ok=False)
        return queryset


class PageSizeChangeList(ChangeList):
    """Honours ?per_page=25|50|100 without treating it as a model filter."""

    def get_filters_params(self, params=None):
        lookup = super().get_filters_params(params)
        lookup.pop("per_page", None)
        return lookup

    def get_results(self, request):
        raw = request.GET.get("per_page", "")
        if raw in {"25", "50", "100"}:
            self.list_per_page = int(raw)
        super().get_results(request)


class QuickCategoryForm(forms.Form):
    name = forms.CharField(label="Nom", max_length=60)


class QuickDepositorForm(forms.Form):
    username = forms.CharField(label="Identifiant", max_length=150)
    first_name = forms.CharField(label="Prénom", max_length=150, required=False)
    last_name = forms.CharField(label="Nom", max_length=150, required=False)
    email = forms.EmailField(label="E-mail", required=False)
    password = forms.CharField(label="Mot de passe", widget=forms.PasswordInput, help_text="Au moins 8 caractères.")


def quick_related(request, kind):
    """Small add form for a category or a depositor, rendered inside the admin sheet."""
    from django.contrib.auth.password_validation import validate_password
    from django.shortcuts import render
    from django.utils.text import slugify

    if kind == "categorie":
        if not request.user.has_perm("hub.add_category"):
            return HttpResponseForbidden("Permission refusée.")
        form = QuickCategoryForm(request.POST or None)
        title, kicker = "Nouvelle catégorie", "Catégorie"
    elif kind == "deposant":
        if not request.user.has_perm("auth.add_user"):
            return HttpResponseForbidden("Permission refusée.")
        form = QuickDepositorForm(request.POST or None)
        title, kicker = "Nouveau déposant", "Déposant"
    else:
        return HttpResponseForbidden("Formulaire inconnu.")

    if request.method == "POST" and form.is_valid():
        if kind == "categorie":
            name = form.cleaned_data["name"].strip()
            if Category.objects.filter(name__iexact=name).exists():
                form.add_error("name", "Cette catégorie existe déjà.")
            else:
                base = (slugify(name) or "categorie")[:50]
                slug, n = base, 2
                while Category.objects.filter(slug=slug).exists():
                    slug = f"{base[:46]}-{n}"
                    n += 1
                category = Category.objects.create(name=name, slug=slug)
                return JsonResponse({"ok": True, "value": str(category.pk), "label": category.name})
        else:
            User = get_user_model()
            username = form.cleaned_data["username"].strip()
            if User.objects.filter(username__iexact=username).exists():
                form.add_error("username", "Cet identifiant est déjà utilisé.")
            else:
                try:
                    validate_password(form.cleaned_data["password"], User(username=username, email=form.cleaned_data["email"]))
                except ValidationError as exc:
                    form.add_error("password", exc)
                else:
                    user = User.objects.create_user(
                        username=username,
                        email=form.cleaned_data["email"],
                        password=form.cleaned_data["password"],
                        first_name=form.cleaned_data["first_name"],
                        last_name=form.cleaned_data["last_name"],
                    )
                    return JsonResponse({"ok": True, "value": str(user.pk), "label": user.get_username()})
    if request.method == "POST" and request.headers.get("X-Requested-With") == "fetch":
        return JsonResponse({"ok": False, "errors": {key: list(value) for key, value in form.errors.items()}}, status=400)

    return render(request, "admin/hub/quick_related.html", {"form": form, "title": title, "kicker": kicker})


@admin.register(Application)
class ApplicationAdmin(admin.ModelAdmin):
    list_per_page = 50
    list_max_show_all = 100
    list_select_related = ['category', 'submitted_by']
    date_hierarchy = 'created_at'
    show_full_result_count = False
    search_help_text = "Rechercher par nom, adresse web ou créateur."

    def get_changelist(self, request, **kwargs):
        return PageSizeChangeList

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(payment_ok=Exists(
            covering_payments(OuterRef("pk"), OuterRef("fee_amount"))
        ))

    def get_urls(self):
        from django.urls import path
        from .admin_workflow import publication_notices, workflow
        from functools import partial
        return [
            path('notifications/', self.admin_site.admin_view(partial(publication_notices, self)), name='hub_application_notices'),
            path('rapide/categorie/', self.admin_site.admin_view(partial(quick_related, kind='categorie')), name='hub_application_quick_category'),
            path('rapide/deposant/', self.admin_site.admin_view(partial(quick_related, kind='deposant')), name='hub_application_quick_depositor'),
            path('suivi/', self.admin_site.admin_view(partial(workflow, self)), name='hub_application_workflow'),
            path('suivi/<int:object_id>/', self.admin_site.admin_view(partial(workflow, self)), name='hub_application_workflow_detail'),
        ] + super().get_urls()
    form = AdminApplicationForm
    list_display = ["name", "category", "status_badge", "creator_display", "funding_badge", "created_short"]
    list_filter = ["status", "is_admin_added", "category", PaymentCoverageFilter]

    def changelist_view(self, request, extra_context=None):
        context = extra_context or {}
        context.update(self.directory_context(request))
        return super().changelist_view(request, extra_context=context)

    def directory_context(self, request):
        params = request.GET.copy()
        params.pop("p", None)

        def href(**updates):
            query = params.copy()
            for key, value in updates.items():
                if value is None:
                    query.pop(key, None)
                else:
                    query[key] = value
            encoded = query.urlencode()
            return f"?{encoded}" if encoded else "?"

        current = params.get("status__exact", "")
        counts = {row["status"]: row["n"] for row in Application.objects.values("status").annotate(n=Count("pk"))}
        chips = [{"label": "Toutes", "count": sum(counts.values()), "href": href(status__exact=None), "current": not current}]
        for value, label in Application.Status.choices:
            chips.append({"label": label, "count": counts.get(value, 0), "href": href(status__exact=value), "current": current == value})
        return {
            "directory_chips": chips,
            "directory_categories": Category.objects.order_by("order", "name"),
            "directory_category": params.get("category__id__exact", ""),
            "directory_plan": params.get("abonnement", ""),
        }
    search_fields = ["name", "website_url", "submitted_by__username", "creator_name"]
    prepopulated_fields = {"slug": ("name",)}
    readonly_fields = ["public_id", "is_admin_added", "fee_amount", "reviewed_by", "reviewed_at", "created_at", "updated_at", "payment_confirmed", "logo_preview"]
    fieldsets = [
        ("Identité & catégorie", {"description": "Le nom, la catégorie et le résumé que verront les visiteurs.", "fields": [("name", "slug"), ("category", "status"), "description", "about"]}),
        ("Visuels & liens", {"description": "Ajoutez ou remplacez le logo et la bannière. Le logo est aussi demandé lors d'une soumission publique.", "fields": [("logo", "logo_preview"), "banner", "website_url", ("color", "icon")]}),
        ("Créateur & modération", {"description": "Qui porte le projet, et le message à lui laisser.", "fields": [("creator_name", "creator_city"), "submitted_by", "moderation_note"]}),
        ("Suivi & paiement", {"description": "Ces informations se remplissent toutes seules.", "fields": [("is_admin_added", "payment_confirmed", "fee_amount"), ("reviewed_by", "reviewed_at"), ("created_at", "updated_at"), "public_id"]}),
    ]
    def get_fieldsets(self, request, obj=None):
        fieldsets = super().get_fieldsets(request, obj)
        if obj is None:
            return [item for item in fieldsets if item[0] != "Suivi & paiement"]
        return fieldsets
    actions = ["approve_applications", "request_corrections", "archive_applications"]
    @admin.display(description="Aperçu du logo")
    def logo_preview(self, obj):
        if not obj or not getattr(obj, "logo", None):
            return "Aucun logo pour le moment."
        return format_html('<img src="{}" alt="" class="console-thumb console-logo-preview">', obj.logo.url)

    @admin.display(boolean=True, description="Paiement confirmé")
    def payment_confirmed(self, obj): return obj.paid
    @admin.display(description="Statut", ordering="status")
    def status_badge(self, obj):
        tones = {"published": "ok", "review": "blue", "draft": "warn", "rejected": "danger", "archived": "muted"}
        return console_badge(obj.get_status_display(), tones.get(obj.status, "soft"))
    @admin.display(description="Créateur", ordering="submitted_by__username")
    def creator_display(self, obj):
        if obj.creator_name:
            return obj.creator_name
        if obj.submitted_by:
            return obj.submitted_by.get_short_name() or obj.submitted_by.username
        return "Administration"
    @admin.display(description="Accès & paiement")
    def funding_badge(self, obj):
        paid = obj.payment_ok if hasattr(obj, "payment_ok") else obj.paid
        if obj.is_admin_added:
            return console_badge("Offert · Admin", "soft")
        if paid:
            return console_badge(f"À jour · {obj.fee_amount} FCFA / an", "ok")
        return console_badge(f"À régler · {obj.fee_amount} FCFA / an", "warn")
    @admin.display(description="Ajoutée le", ordering="created_at")
    def created_short(self, obj):
        return timezone.localtime(obj.created_at).strftime("%d %b %Y · %H:%M") if obj.created_at else "—"
    def get_changeform_initial_data(self, request):
        return {"status": Application.Status.PUBLISHED}
    def save_model(self, request, obj, form, change):
        if not change:
            obj.is_admin_added = True
            if not obj.submitted_by_id: obj.submitted_by = request.user
        if obj.status in [Application.Status.PUBLISHED, Application.Status.REJECTED, Application.Status.ARCHIVED]:
            obj.reviewed_by, obj.reviewed_at = request.user, timezone.now()
        obj.full_clean()
        super().save_model(request, obj, form, change)
    @admin.action(description="Publier les applications sélectionnées après contrôle du paiement")
    def approve_applications(self, request, queryset):
        count = 0
        for item in queryset:
            try:
                with transaction.atomic():
                    locked = Application.objects.select_for_update().get(pk=item.pk)
                    locked.approve(request.user)
                count += 1
            except ValidationError:
                self.message_user(request, f"{item.name} : paiement non confirmé, publication refusée.", level=messages.ERROR)
        self.message_user(request, f"{count} application(s) publiée(s).")
    @admin.action(description="Demander des corrections aux déposants")
    def request_corrections(self, request, queryset):
        queryset.update(status=Application.Status.REJECTED, reviewed_by=request.user, reviewed_at=timezone.now(), moderation_note="Merci de corriger votre fiche avant de la soumettre à nouveau. Contactez l'administration pour les précisions et le suivi du paiement.")
    @admin.action(description="Archiver les applications sélectionnées")
    def archive_applications(self, request, queryset):
        queryset.update(status=Application.Status.ARCHIVED, reviewed_by=request.user, reviewed_at=timezone.now())

@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_per_page = 25
    list_select_related = ['application', 'user', 'manual_confirmed_by']
    date_hierarchy = 'created_at'
    show_full_result_count = False
    search_help_text = "Référence Hub, justificatif, transaction, application ou payeur. Ouvrez le dossier pour valider manuellement."

    list_display = ["reference", "application", "user", "amount_badge", "payment_status_badge", "coverage_short", "verified_short", "submission_link"]
    list_filter = ["status", ("manual_confirmed_by", admin.RelatedOnlyFieldListFilter)]
    search_fields = ["reference", "manual_reference", "provider_transaction_id", "application__name", "user__username", "user__email"]
    readonly_fields = [field.name for field in Payment._meta.fields] + ["submission_link"]
    @admin.display(description="Montant", ordering="amount")
    def amount_badge(self, obj):
        return format_html("<strong>{} FCFA</strong>", f"{int(obj.amount):,}".replace(",", "\u202f"))
    @admin.display(description="Statut", ordering="status")
    def payment_status_badge(self, obj):
        tones = {"success": "ok", "pending": "warn", "failed": "danger", "cancelled": "muted"}
        return console_badge(obj.get_status_display(), tones.get(obj.status, "soft"))
    @admin.display(description="Couverture", ordering="valid_until")
    def coverage_short(self, obj):
        if obj.status != Payment.Status.SUCCESS or not obj.valid_until:
            return console_badge("—", "muted")
        if obj.valid_until <= timezone.now():
            return console_badge("Expiré", "warn")
        return timezone.localtime(obj.valid_until).strftime("Jusqu'au %d/%m/%Y")
    def changelist_view(self, request, extra_context=None):
        if request.method == "POST" and "set_submission_fee" in request.POST:
            if not request.user.has_perm("hub.change_hubappearance"):
                self.message_user(request, "Vous ne pouvez pas modifier le tarif de l'abonnement.", level=messages.ERROR)
            else:
                raw = (request.POST.get("submission_fee") or "").strip()
                try:
                    fee = int(raw)
                except ValueError:
                    fee = 0
                if fee < 1 or fee > 1000000:
                    self.message_user(request, "Le tarif annuel doit être compris entre 1 et 1 000 000 FCFA.", level=messages.ERROR)
                else:
                    if not HubAppearance.objects.filter(pk=1).update(submission_fee=fee, updated_at=timezone.now()):
                        HubAppearance.objects.create(submission_fee=fee)
                    self.message_user(request, f"Abonnement annuel fixé à {fee} FCFA.")
            return HttpResponseRedirect(request.path)
        extra_context = extra_context or {}
        extra_context["show_annual_fee"] = True
        extra_context["annual_fee"] = HubAppearance.current().submission_fee
        extra_context["can_edit_annual_fee"] = request.user.has_perm("hub.change_hubappearance")
        return super().changelist_view(request, extra_context=extra_context)
    @admin.display(description="Confirmation", ordering="verified_at")
    def verified_short(self, obj):
        if obj.verified_at:
            mode = "Manuelle" if obj.manual_reference else "Serveur"
            return f"{mode} · {timezone.localtime(obj.verified_at).strftime('%d/%m/%Y %H:%M')}"
        return console_badge("En attente", "warn")
    @admin.display(description="Dossier de soumission")
    def submission_link(self, obj):
        return format_html('<a class="console-inline-btn" href="{}">Examiner le dossier →</a>', reverse('admin:hub_application_workflow_detail', args=[obj.application_id]))
    actions = ["verify_selected"]
    def has_add_permission(self, request): return False
    def has_delete_permission(self, request, obj=None): return False
    @admin.action(description="Revérifier les paiements auprès de l'API Paiement Mobile")
    def verify_selected(self, request, queryset):
        for payment in queryset[:30]:
            self.message_user(request, f"{payment.reference} : {verify_payment(payment)}")

@admin.register(PaymentEvent)
class PaymentEventAdmin(admin.ModelAdmin):
    list_display = ["reference_label", "signature_badge", "result", "received_short"]
    list_filter = ["signature_valid"]
    search_fields = ["reference", "result"]
    readonly_fields = [field.name for field in PaymentEvent._meta.fields]
    @admin.display(description="Référence", ordering="reference")
    def reference_label(self, obj):
        return obj.reference or "Webhook sans référence"
    @admin.display(description="Signature HMAC", ordering="signature_valid")
    def signature_badge(self, obj):
        return console_badge("Signature valide", "ok") if obj.signature_valid else console_badge("Signature rejetée", "danger")
    @admin.display(description="Reçu le", ordering="received_at")
    def received_short(self, obj):
        return timezone.localtime(obj.received_at).strftime("%d/%m/%Y · %H:%M:%S")
    def has_add_permission(self, request): return False
    def has_delete_permission(self, request, obj=None): return False

@admin.register(Favorite)
class FavoriteAdmin(admin.ModelAdmin):
    list_display = ["application", "user", "created_short"]
    list_select_related = ["application", "user"]
    search_fields = ["user__username", "application__name"]
    @admin.display(description="Enregistré le", ordering="created_at")
    def created_short(self, obj):
        return timezone.localtime(obj.created_at).strftime("%d %b %Y · %H:%M")

@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ["application", "user", "stars_badge", "comment_excerpt", "visibility_badge", "updated_short"]
    list_select_related = ["application", "user"]
    list_filter = ["is_visible", "rating"]
    search_fields = ["application__name", "user__username", "comment"]
    readonly_fields = ["application", "user", "rating", "comment", "created_at", "updated_at"]
    fieldsets = [("Avis publié", {"fields": [("application", "user"), ("rating", "is_visible"), "comment", ("created_at", "updated_at")]})]
    actions = ["hide_reviews", "show_reviews"]
    def has_add_permission(self, request): return False
    @admin.display(description="Note", ordering="rating")
    def stars_badge(self, obj):
        return format_html('<span class="console-stars" aria-label="{} sur 5">{} <strong>{}/5</strong></span>', obj.rating, "★" * obj.rating + "☆" * (5 - obj.rating), obj.rating)
    @admin.display(description="Commentaire")
    def comment_excerpt(self, obj):
        if not obj.comment:
            return "Sans commentaire"
        return obj.comment[:90] + ("…" if len(obj.comment) > 90 else "")
    @admin.display(description="Visibilité", ordering="is_visible")
    def visibility_badge(self, obj):
        return console_badge("Visible sur le Hub", "ok") if obj.is_visible else console_badge("Masqué", "muted")
    @admin.display(description="Mis à jour", ordering="updated_at")
    def updated_short(self, obj):
        return timezone.localtime(obj.updated_at).strftime("%d %b %Y · %H:%M")
    @admin.action(description="Masquer les avis sélectionnés")
    def hide_reviews(self, request, queryset): queryset.update(is_visible=False)
    @admin.action(description="Rendre visibles les avis sélectionnés")
    def show_reviews(self, request, queryset): queryset.update(is_visible=True)


User = get_user_model()
try:
    admin.site.unregister(User)
except admin.sites.NotRegistered:
    pass


@admin.register(User)
class HubUserAdmin(BaseUserAdmin):
    list_display = ["username", "email_display", "role_badge", "submissions_badge", "last_login_short"]
    def get_queryset(self, request):
        return super().get_queryset(request).annotate(_apps=Count("submissions"))
    @admin.display(description="E-mail", ordering="email")
    def email_display(self, obj):
        return obj.email or "Non renseigné"
    @admin.display(description="Rôle", ordering="is_staff")
    def role_badge(self, obj):
        if obj.is_superuser:
            return console_badge("Super-admin", "blue")
        if obj.is_staff:
            return console_badge("Équipe Hub", "ok")
        return console_badge("Créateur / Membre", "soft")
    @admin.display(description="Applications", ordering="_apps")
    def submissions_badge(self, obj):
        count = getattr(obj, "_apps", 0)
        return f"{count} dossier{'s' if count > 1 else ''}" if count else "—"
    @admin.display(description="Dernière connexion", ordering="last_login")
    def last_login_short(self, obj):
        return timezone.localtime(obj.last_login).strftime("%d/%m/%Y %H:%M") if obj.last_login else "Jamais connecté"
