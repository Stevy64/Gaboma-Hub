import re
import uuid
from datetime import timedelta
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.urls import reverse
from django.utils import timezone
from .validators import validate_application_url
from .images import application_image_path, editorial_image_path, native_package_path
from django.core.validators import MinValueValidator, MaxValueValidator

class HubAppearance(models.Model):
    logo = models.ImageField("logo du Hub", upload_to=editorial_image_path, blank=True)
    hero_background = models.ImageField("image de fond du Hero", upload_to=editorial_image_path, blank=True)
    hero_background_enabled = models.BooleanField("activer l'image de fond", default=True)
    submission_fee = models.PositiveIntegerField("abonnement annuel (FCFA)", default=2500, validators=[MinValueValidator(1), MaxValueValidator(1000000)], help_text="Montant d'une année de référencement. Il s'applique aux nouvelles souscriptions et aux renouvellements. Un paiement déjà confirmé reste valable un an, pour le montant encaissé.")
    hero_badge = models.CharField("accroche", max_length=80, default="LE GABON NUMÉRIQUE.")
    hero_title = models.CharField("titre d'accueil", max_length=80, default="Les apps d’ici.")
    hero_subtitle = models.CharField("titre mis en couleur", max_length=100, default="Pour votre quotidien.")
    hero_description = models.CharField("description d'accueil", max_length=240, default="Découvrez les applications des créateurs gabonais. Vos prochains essentiels sont ici.")
    hero_primary_label = models.CharField("bouton principal", max_length=40, blank=True, default="Explorer le catalogue")
    hero_secondary_label = models.CharField("bouton créateur", max_length=40, blank=True, default="Référencer mon app")
    territory_line = models.CharField("bandeau local", max_length=120, blank=True, default="Pensé au Gabon. Pour les Gabonais.")
    art_caption = models.CharField("légende de l'illustration", max_length=80, blank=True, default="Vos apps, un seul endroit.")
    site_name = models.CharField("nom du site", max_length=80, blank=True, default="Gaboma Hub")
    document_title = models.CharField("titre des pages", max_length=140, blank=True, default="Gaboma Hub · Les talents du Gabon, les apps de demain")
    meta_description = models.CharField("description SEO", max_length=220, blank=True, default="Découvrez les applications des créateurs gabonais : services, commerce, outils et nouveautés. Partagez vos avis sur Gaboma Hub.")
    catalogue_kicker = models.CharField("sur-titre du répertoire", max_length=40, blank=True, default="Le répertoire")
    catalogue_title = models.CharField("titre du répertoire", max_length=80, blank=True, default="Trouvez votre prochaine app.")
    catalogue_note = models.CharField("note du répertoire", max_length=120, blank=True, default="À chaque besoin, de nouvelles possibilités.")
    rail_new_title = models.CharField("rail nouveautés — titre", max_length=80, blank=True, default="Nouvellement ajoutées")
    rail_new_subtitle = models.CharField("rail nouveautés — sous-titre", max_length=140, blank=True, default="Des apps à ouvrir, dès maintenant.")
    rail_follow_title = models.CharField("rail projets — titre", max_length=80, blank=True, default="Les projets à suivre")
    rail_follow_subtitle = models.CharField("rail projets — sous-titre", max_length=140, blank=True, default="Les projets dont le lien reste à compléter.")
    rail_rated_title = models.CharField("rail avis — titre", max_length=80, blank=True, default="Appréciées par la communauté")
    rail_rated_subtitle = models.CharField("rail avis — sous-titre", max_length=140, blank=True, default="Le classement selon vos avis.")
    creator_kicker = models.CharField("bandeau créateurs — sur-titre", max_length=40, blank=True, default="POUR LES CRÉATEURS")
    creator_title = models.CharField("bandeau créateurs — titre", max_length=80, blank=True, default="Une idée, une app.")
    creator_emphasis = models.CharField("bandeau créateurs — accent", max_length=80, blank=True, default="un public.")
    creator_text = models.CharField("bandeau créateurs — texte", max_length=240, blank=True, default="Donnez à votre projet sa place dans le paysage numérique gabonais.")
    footer_lead = models.CharField("pied de page", max_length=160, blank=True, default="Le répertoire des créateurs gabonais.")
    footer_colophon = models.CharField("signature du pied de page", max_length=160, blank=True, default="Des idées locales. Des horizons ouverts.")
    support_email = models.EmailField("e-mail de contact", blank=True, default="")
    support_phone = models.CharField("téléphone de contact", max_length=32, blank=True, default="")
    whatsapp_number = models.CharField("numéro WhatsApp", max_length=32, blank=True, default="", help_text="Ex. 077000000 ou +24177000000. Vide : le lien n'apparaît pas.")
    facebook_url = models.URLField("Facebook", max_length=500, blank=True, default="", validators=[validate_application_url])
    instagram_url = models.URLField("Instagram", max_length=500, blank=True, default="", validators=[validate_application_url])
    tiktok_url = models.URLField("TikTok", max_length=500, blank=True, default="", validators=[validate_application_url])
    linkedin_url = models.URLField("LinkedIn", max_length=500, blank=True, default="", validators=[validate_application_url])
    x_url = models.URLField("X", max_length=500, blank=True, default="", validators=[validate_application_url])
    android_app = models.FileField("application Android", upload_to=native_package_path, blank=True, help_text="Fichier .apk, 80 Mo maximum. Proposé sur les téléphones Android. Sans fichier, le Hub s'installe comme application web.")
    ios_app = models.FileField("application Apple", upload_to=native_package_path, blank=True, help_text="Fichier .ipa, 80 Mo maximum. Proposé sur iPhone. Sans fichier, le Hub explique l'ajout à l'écran d'accueil.")
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
    def __str__(self): return "Accueil, vitrine et abonnement"

    @classmethod
    def current(cls):
        return cls.objects.first() or cls()

    def whatsapp_href(self):
        digits = re.sub(r"\D", "", self.whatsapp_number or "")
        if digits.startswith("00"):
            digits = digits[2:]
        if digits.startswith("0"):
            digits = "241" + digits[1:]
        return f"https://wa.me/{digits}" if digits else ""

    def contact_links(self):
        links = []
        if self.support_email:
            links.append(("E-mail", f"mailto:{self.support_email}"))
        if self.support_phone:
            links.append(("Téléphone", f"tel:{re.sub(r'[^0-9+]', '', self.support_phone)}"))
        if self.whatsapp_href():
            links.append(("WhatsApp", self.whatsapp_href()))
        for label, url in (("Facebook", self.facebook_url), ("Instagram", self.instagram_url), ("TikTok", self.tiktok_url), ("LinkedIn", self.linkedin_url), ("X", self.x_url)):
            if url:
                links.append((label, url))
        return links

class HeroSlide(models.Model):
    appearance = models.ForeignKey(HubAppearance, on_delete=models.CASCADE, related_name="slides", verbose_name="paramètres")
    image = models.ImageField("image", upload_to=editorial_image_path)
    alt = models.CharField("légende", max_length=120, blank=True)
    order = models.PositiveSmallIntegerField("ordre", default=0)
    is_active = models.BooleanField("affichée dans le carrousel", default=True)
    class Meta:
        verbose_name = "image du hero"
        verbose_name_plural = "images du hero"
        ordering = ["order", "pk"]
    def __str__(self):
        return self.alt or f"Image {self.pk or ''}".strip()

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

class CatalogueFilter(models.Model):
    ICONS = [("wallet", "Portefeuille"), ("user", "Personne"), ("sparkles", "Étoile filante"), ("shield", "Bouclier"), ("message", "Message"), ("grid", "Grille"), ("star", "Étoile"), ("heart", "Cœur"), ("search", "Recherche"), ("clock", "Horloge"), ("pin", "Lieu"), ("link", "Lien"), ("image", "Image"), ("mail", "Courrier")]
    TONES = [("mint", "Menthe"), ("blue", "Bleu"), ("gold", "Or"), ("ice", "Givre")]
    label = models.CharField("libellé", max_length=40)
    category = models.ForeignKey(Category, verbose_name="catégorie filtrée", on_delete=models.PROTECT, related_name="directory_filters")
    icon = models.CharField("icône", max_length=20, choices=ICONS, default="grid")
    tone = models.CharField("teinte", max_length=12, choices=TONES, default="blue")
    order = models.PositiveSmallIntegerField("ordre", default=0)
    is_active = models.BooleanField("affichée sur l'accueil", default=True)
    class Meta:
        verbose_name = "filtre d'accueil"
        verbose_name_plural = "filtres d'accueil"
        ordering = ["order", "label"]
    def __str__(self): return self.label

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
        indexes = [
            models.Index(fields=["status", "created_at"], name="hub_app_status_created"),
            models.Index(fields=["status", "category", "created_at"], name="hub_app_status_cat_created"),
        ]
    def __str__(self): return self.name
    def get_absolute_url(self): return reverse("hub:detail", kwargs={"slug": self.slug})
    @property
    def initials(self): return self.name[:2].upper()
    @property
    def paid(self):
        return bool(self.pk and covering_payments(self.pk, self.fee_amount).exists())
    @property
    def coverage_until(self):
        if not self.pk:
            return None
        return covering_payments(self.pk, self.fee_amount).order_by("-valid_until").values_list("valid_until", flat=True).first()
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
    def publish_by_creator(self):
        if self.is_admin_added:
            raise ValidationError("Cette fiche a été ajoutée par l'administration.")
        if self.status == self.Status.ARCHIVED:
            raise ValidationError("Une fiche archivée ne peut pas être publiée depuis cet espace.")
        if self.status == self.Status.PUBLISHED:
            raise ValidationError("Cette application est déjà publiée.")
        if self.status not in (self.Status.DRAFT, self.Status.REJECTED, self.Status.REVIEW):
            raise ValidationError("Cette fiche ne peut pas être confirmée.")
        if not self.paid:
            raise ValidationError("Confirmez d'abord le paiement de l'abonnement.")
        self.status = self.Status.PUBLISHED
        self.reviewed_by = None
        self.reviewed_at = timezone.now()
        self.moderation_note = ""
        self.full_clean()
        self.save(update_fields=["status", "reviewed_by", "reviewed_at", "moderation_note", "updated_at"])
        SubmissionNotice.objects.create(application=self)

class SubmissionNotice(models.Model):
    application = models.ForeignKey(Application, on_delete=models.CASCADE, related_name="notices", verbose_name="application")
    created_at = models.DateTimeField("confirmée le", auto_now_add=True)
    seen_at = models.DateTimeField("lue le", null=True, blank=True)
    class Meta:
        ordering = ["-created_at"]
        verbose_name = "notification de publication"
        verbose_name_plural = "notifications de publication"
        indexes = [models.Index(fields=["seen_at", "created_at"], name="hub_notice_seen_created")]
    def __str__(self): return self.application.name

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
        indexes = [models.Index(fields=["application", "is_visible"], name="hub_review_app_visible")]
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
    valid_until = models.DateTimeField("valable jusqu'au", null=True, blank=True)
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
    def save(self, *args, **kwargs):
        update_fields = kwargs.get("update_fields")
        if self.status == self.Status.SUCCESS and self.verified_at and not self.valid_until:
            self.valid_until = self.verified_at + timedelta(days=SUBSCRIPTION_DAYS)
            if update_fields is not None:
                kwargs["update_fields"] = set(update_fields) | {"valid_until"}
        super().save(*args, **kwargs)
    def __str__(self): return f"{self.reference} · {self.amount} FCFA"


SUBSCRIPTION_DAYS = 365


def covering_payments(application_ref, amount_ref):
    return Payment.objects.filter(
        application=application_ref,
        status=Payment.Status.SUCCESS,
        amount=amount_ref,
        currency="XAF",
        verified_at__isnull=False,
        valid_until__gt=timezone.now(),
    )

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
