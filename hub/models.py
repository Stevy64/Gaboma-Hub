import uuid
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.urls import reverse
from django.utils import timezone
from .validators import validate_application_url
from .images import application_image_path, editorial_image_path
from django.core.validators import MinValueValidator, MaxValueValidator

class HubAppearance(models.Model):
    hero_background = models.ImageField("image de fond du Hero", upload_to=editorial_image_path, blank=True)
    hero_background_enabled = models.BooleanField("activer l'image de fond", default=True)
    submission_fee = models.PositiveIntegerField("tarif de référencement (FCFA)", default=2000, validators=[MinValueValidator(1), MaxValueValidator(1000000)], help_text="Appliqué uniquement aux nouvelles fiches. Les fiches et paiements existants conservent leur tarif.")
    hero_badge = models.CharField("accroche", max_length=80, default="LE NUMÉRIQUE, CÔTÉ GABON.")
    hero_title = models.CharField("titre d'accueil", max_length=80, default="Les apps d’ici.")
    hero_subtitle = models.CharField("titre mis en couleur", max_length=100, default="Pour votre quotidien.")
    hero_description = models.CharField("description d'accueil", max_length=240, default="Découvrez les applications des créateurs gabonais. Vos prochains essentiels sont ici.")
    showcase_enabled = models.BooleanField("afficher la vitrine", default=True)
    discovery_enabled = models.BooleanField("afficher les carrousels de découverte", default=True)
    updated_at = models.DateTimeField("mise à jour", auto_now=True)
    class Meta:
        verbose_name = "paramètres du Hub"
        verbose_name_plural = "paramètres du Hub"
        constraints = [models.CheckConstraint(condition=models.Q(pk=1), name="single_hub_appearance"), models.CheckConstraint(condition=models.Q(submission_fee__gte=1, submission_fee__lte=1000000), name="hub_fee_valid_range")]
    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)
    def __str__(self): return "Accueil, vitrine et tarif"

    @classmethod
    def current(cls):
        return cls.objects.first() or cls()

class Advertisement(models.Model):
    class Placement(models.TextChoices):
        HERO = "hero", "En vitrine — carrousel du Hero"
        DISCOVERY = "discovery", "Sous le Hero, avant les applications"
        CATALOGUE = "catalogue", "Sous le catalogue"
    title = models.CharField("titre", max_length=100)
    sponsor = models.CharField("annonceur", max_length=100, blank=True)
    image = models.ImageField("visuel publicitaire", upload_to=editorial_image_path)
    target_url = models.URLField("lien de destination", max_length=500, blank=True, validators=[validate_application_url])
    placement = models.CharField("emplacement", max_length=12, choices=Placement.choices, default=Placement.DISCOVERY)
    is_active = models.BooleanField("activée", default=False)
    starts_at = models.DateTimeField("début de diffusion", null=True, blank=True)
    ends_at = models.DateTimeField("fin de diffusion", null=True, blank=True)
    order = models.PositiveSmallIntegerField("ordre d'affichage", default=0)
    class Meta:
        verbose_name = "publicité"
        ordering = ["order", "pk"]
        constraints = [models.CheckConstraint(condition=models.Q(starts_at__isnull=True) | models.Q(ends_at__isnull=True) | models.Q(ends_at__gt=models.F("starts_at")), name="ad_end_after_start")]
    def clean(self):
        super().clean()
        if self.starts_at and self.ends_at and self.ends_at <= self.starts_at:
            raise ValidationError({"ends_at": "La fin doit être postérieure au début de diffusion."})
    def __str__(self): return self.title

class Category(models.Model):
    name = models.CharField("nom", max_length=60, unique=True)
    slug = models.SlugField(unique=True)
    order = models.PositiveSmallIntegerField("ordre", default=0)
    class Meta:
        verbose_name = "catégorie"
        ordering = ["order", "name"]
    def __str__(self): return self.name

class Application(models.Model):
    class Status(models.TextChoices):
        DRAFT = "draft", "À finaliser"
        REVIEW = "review", "En validation"
        PUBLISHED = "published", "Publiée"
        REJECTED = "rejected", "À corriger"
        ARCHIVED = "archived", "Archivée"
    class Color(models.TextChoices):
        SKY = "sage", "Bleu ciel"
        AZURE = "purple", "Bleu azur"
        BLUE = "blue", "Bleu profond"
        ORANGE = "sand", "Orange"
        INDIGO = "forest", "Bleu indigo"
    ICONS = [(x, x) for x in ["custom", "market", "chart", "fallaman", "cube", "pass", "event"]]
    public_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    name = models.CharField("nom de l'application", max_length=60)
    slug = models.SlugField(max_length=100, unique=True)
    category = models.ForeignKey(Category, verbose_name="catégorie", on_delete=models.PROTECT)
    description = models.CharField("description courte", max_length=240)
    about = models.TextField("présentation complète", max_length=6000, blank=True)
    creator_name = models.CharField("créateur ou équipe", max_length=100, blank=True)
    creator_city = models.CharField("ville du créateur", max_length=80, blank=True)
    logo = models.ImageField("logo", upload_to=application_image_path, blank=True)
    banner = models.ImageField("bannière", upload_to=application_image_path, blank=True)
    website_url = models.URLField("adresse web", max_length=500, blank=True, validators=[validate_application_url])
    color = models.CharField("couleur", max_length=12, choices=Color.choices, default=Color.SKY)
    icon = models.CharField("icône", max_length=15, choices=ICONS, default="custom")
    submitted_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="submissions", verbose_name="déposant")
    is_admin_added = models.BooleanField("ajout gratuit par l'administration", default=False, editable=False)
    fee_amount = models.PositiveIntegerField("tarif de soumission en FCFA", default=2000, editable=False)
    status = models.CharField("état", max_length=12, choices=Status.choices, default=Status.DRAFT)
    moderation_note = models.TextField("retour de modération", blank=True)
    reviewed_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="reviewed_applications", verbose_name="modérateur")
    reviewed_at = models.DateTimeField("date de décision", null=True, blank=True)
    created_at = models.DateTimeField("créée le", auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    class Meta:
        verbose_name = "application"
        ordering = ["name"]
    def __str__(self): return self.name
    def get_absolute_url(self): return reverse("hub:detail", kwargs={"slug": self.slug})
    @property
    def initials(self): return self.name[:2].upper()
    @property
    def paid(self):
        return bool(self.pk and self.payments.filter(status=Payment.Status.SUCCESS, amount=self.fee_amount, currency="XAF", verified_at__isnull=False).exists())
    @property
    def can_publish(self): return self.is_admin_added or self.paid
    def clean(self):
        super().clean()
        if self.status == self.Status.PUBLISHED and not self.can_publish:
            raise ValidationError({"status": "Un paiement Paiement Mobile confirmé est requis pour une soumission utilisateur."})
        if not self.is_admin_added and not self.website_url:
            raise ValidationError({"website_url": "Renseignez une adresse web publique pour votre soumission."})
    def approve(self, reviewer):
        if not self.can_publish:
            raise ValidationError("Paiement non confirmé : publication impossible.")
        self.status = self.Status.PUBLISHED
        self.reviewed_by = reviewer
        self.reviewed_at = timezone.now()
        self.moderation_note = ""
        self.full_clean()
        self.save(update_fields=["status", "reviewed_by", "reviewed_at", "moderation_note", "updated_at"])

class Review(models.Model):
    application = models.ForeignKey(Application, on_delete=models.CASCADE, related_name="reviews", verbose_name="application")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, verbose_name="auteur")
    rating = models.PositiveSmallIntegerField("note", validators=[MinValueValidator(1), MaxValueValidator(5)])
    comment = models.TextField("avis", max_length=2000, blank=True)
    is_visible = models.BooleanField("visible", default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    class Meta:
        verbose_name = "avis"
        verbose_name_plural = "avis"
        ordering = ["-updated_at"]
        constraints = [models.UniqueConstraint(fields=["user", "application"], name="one_review_per_user_app"),
            models.CheckConstraint(condition=models.Q(rating__gte=1, rating__lte=5), name="rating_between_one_five")]
    @property
    def stars(self): return "★" * self.rating + "☆" * (5 - self.rating)
    def __str__(self): return f"{self.application} · {self.rating}/5"

class Favorite(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    application = models.ForeignKey(Application, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        verbose_name = "favori"
        constraints = [models.UniqueConstraint(fields=["user", "application"], name="unique_user_favorite")]

class Payment(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "En attente de confirmation"
        SUCCESS = "success", "Confirmé"
        FAILED = "failed", "Échoué"
        CANCELLED = "cancelled", "Annulé"
    public_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    application = models.ForeignKey(Application, on_delete=models.PROTECT, related_name="payments", verbose_name="application")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, verbose_name="payeur")
    reference = models.CharField(max_length=70, unique=True, editable=False)
    amount = models.PositiveIntegerField("montant FCFA")
    currency = models.CharField("devise", default="XAF", max_length=3)
    status = models.CharField("état", choices=Status.choices, default=Status.PENDING, max_length=12)
    provider_transaction_id = models.CharField("identifiant Paiement Mobile", max_length=160, unique=True, null=True, blank=True)
    manual_reference = models.CharField("référence du justificatif manuel", max_length=160, unique=True, null=True, blank=True)
    manual_note = models.TextField("motif de validation manuelle", blank=True)
    manual_confirmed_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="manually_confirmed_payments", verbose_name="validé manuellement par")
    checkout_url = models.URLField(max_length=1000, blank=True)
    verified_at = models.DateTimeField("confirmation serveur", null=True, blank=True)
    verification_message = models.CharField("dernier contrôle", max_length=240, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    class Meta:
        verbose_name = "Paiement Mobile"
        verbose_name_plural = "Paiements mobiles"
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(fields=["application"], condition=models.Q(status="pending"), name="one_pending_payment_per_app"),
            models.CheckConstraint(condition=models.Q(amount__gt=0), name="positive_payment_amount"),
        ]
    def __str__(self): return f"{self.reference} · {self.amount} FCFA"

class PaymentEvent(models.Model):
    received_at = models.DateTimeField(auto_now_add=True)
    reference = models.CharField(max_length=100, blank=True)
    signature_valid = models.BooleanField(default=False)
    result = models.CharField(max_length=120)
    class Meta:
        verbose_name = "notification de paiement"
        verbose_name_plural = "notifications de paiement"
        ordering = ["-received_at"]


class HubVisitor(models.Model):
    fingerprint = models.CharField(max_length=64, unique=True, editable=False)
    first_seen = models.DateTimeField(auto_now_add=True)
    class Meta:
        verbose_name = "visiteur anonyme"
