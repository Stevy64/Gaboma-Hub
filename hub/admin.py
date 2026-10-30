from django import forms
from django.contrib import admin, messages
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone
from django.utils.html import format_html
from .models import Application, Category, Favorite, Payment, PaymentEvent, Review, HubAppearance, Advertisement
from .images import ApplicationImagesMixin, PublicImageField
from .payments.services import verify_payment

admin.site.site_header = "Gaboma Hub · Administration"
admin.site.site_title = "Gaboma Hub"
admin.site.index_title = "Applications, modération et paiements"

class AppearanceForm(forms.ModelForm):
    hero_background = PublicImageField(label="Image de fond du Hero", required=False,
        help_text="JPG, PNG ou WebP · 5 Mo maximum. Format paysage conseillé : 1920 × 1080. Un voile protège la lisibilité du texte.")
    class Meta:
        model = HubAppearance
        fields = "__all__"

@admin.register(HubAppearance)
class AppearanceAdmin(admin.ModelAdmin):
    form = AppearanceForm
    readonly_fields = ["updated_at"]
    fieldsets = [
        ("Tarif de référencement", {"fields": ["submission_fee"], "description": "Le tarif est fixé à la création de chaque fiche. Une modification ne change jamais un paiement déjà engagé."}),
        ("Texte de l'accueil", {"fields": ["hero_badge", "hero_title", "hero_subtitle", "hero_description"]}),
        ("Sections et visuels", {"fields": ["showcase_enabled", "discovery_enabled", "hero_background", "hero_background_enabled"], "description": "Ajoutez vos diapositives dans Publicités, emplacement En vitrine. Sans publicité active, les applications disponibles sont présentées."}),
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
    list_display = ["visual_preview", "title", "sponsor", "placement", "is_active", "starts_at", "ends_at", "order"]
    list_display_links = ["visual_preview", "title"]
    readonly_fields = ["visual_preview"]
    @admin.display(description="Aperçu")
    def visual_preview(self, obj):
        if not obj or not obj.image: return "Aucun visuel"
        return format_html('<img src="{}" alt="Aperçu" style="width:120px;max-height:75px;object-fit:contain;border-radius:8px">', obj.image.url)
    list_filter = ["is_active", "placement"]
    search_fields = ["title", "sponsor"]
    list_editable = ["is_active", "order"]
    fieldsets = [("Contenu", {"fields": ["title", "sponsor", "image", "visual_preview", "target_url"]}),
        ("Diffusion", {"fields": ["placement", "is_active", "starts_at", "ends_at", "order"],
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
    list_display = ["name", "slug", "order"]
    prepopulated_fields = {"slug": ("name",)}

@admin.register(Application)
class ApplicationAdmin(admin.ModelAdmin):
    list_per_page = 25
    list_select_related = ['category', 'submitted_by']
    date_hierarchy = 'created_at'
    show_full_result_count = False
    search_help_text = "Rechercher par nom, adresse web ou créateur."

    def get_urls(self):
        from django.urls import path
        from .admin_workflow import workflow
        from functools import partial
        return [
            path('suivi/', self.admin_site.admin_view(partial(workflow, self)), name='hub_application_workflow'),
            path('suivi/<int:object_id>/', self.admin_site.admin_view(partial(workflow, self)), name='hub_application_workflow_detail'),
        ] + super().get_urls()
    form = AdminApplicationForm
    list_display = ["name", "category", "status", "submitted_by", "is_admin_added", "payment_confirmed", "created_at"]
    list_filter = ["status", "is_admin_added", "category"]
    search_fields = ["name", "website_url", "submitted_by__username"]
    prepopulated_fields = {"slug": ("name",)}
    readonly_fields = ["public_id", "is_admin_added", "fee_amount", "reviewed_by", "reviewed_at", "created_at", "updated_at", "payment_confirmed"]
    actions = ["approve_applications", "request_corrections", "archive_applications"]
    @admin.display(boolean=True, description="Paiement confirmé")
    def payment_confirmed(self, obj): return obj.paid
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

    list_display = ["reference", "application", "user", "amount", "status", "verified_at", "submission_link"]
    list_filter = ["status", ("manual_confirmed_by", admin.RelatedOnlyFieldListFilter)]
    search_fields = ["reference", "manual_reference", "provider_transaction_id", "application__name", "user__username", "user__email"]
    readonly_fields = [field.name for field in Payment._meta.fields] + ["submission_link"]
    @admin.display(description="Dossier de soumission")
    def submission_link(self, obj):
        from django.urls import reverse
        return format_html('<a href="{}">Examiner le dossier →</a>', reverse('admin:hub_application_workflow_detail', args=[obj.application_id]))
    actions = ["verify_selected"]
    def has_add_permission(self, request): return False
    def has_delete_permission(self, request, obj=None): return False
    @admin.action(description="Revérifier les paiements auprès de l'API Paiement Mobile")
    def verify_selected(self, request, queryset):
        for payment in queryset[:30]:
            self.message_user(request, f"{payment.reference} : {verify_payment(payment)}")

@admin.register(PaymentEvent)
class PaymentEventAdmin(admin.ModelAdmin):
    list_display = ["received_at", "reference", "signature_valid", "result"]
    readonly_fields = [field.name for field in PaymentEvent._meta.fields]
    def has_add_permission(self, request): return False
    def has_delete_permission(self, request, obj=None): return False

@admin.register(Favorite)
class FavoriteAdmin(admin.ModelAdmin):
    list_display = ["user", "application", "created_at"]
    search_fields = ["user__username", "application__name"]

@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ["application", "user", "rating", "is_visible", "updated_at"]
    list_filter = ["is_visible", "rating"]
    search_fields = ["application__name", "user__username", "comment"]
    readonly_fields = ["application", "user", "rating", "comment", "created_at", "updated_at"]
    actions = ["hide_reviews", "show_reviews"]
    def has_add_permission(self, request): return False
    @admin.action(description="Masquer les avis sélectionnés")
    def hide_reviews(self, request, queryset): queryset.update(is_visible=False)
    @admin.action(description="Rendre visibles les avis sélectionnés")
    def show_reviews(self, request, queryset): queryset.update(is_visible=True)
