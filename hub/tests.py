import hashlib
import hmac
import json
import time
import tempfile
from io import BytesIO
from pathlib import Path
from datetime import timedelta
from PIL import Image
from django.core.files.uploadedfile import SimpleUploadedFile
from unittest.mock import patch
from django.conf import settings
from django.contrib.admin.sites import AdminSite
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.db import IntegrityError, transaction
from django.test import Client, RequestFactory, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from .admin import ApplicationAdmin, AppearanceAdmin
from .forms import ApplicationForm
from .models import Application, CatalogueFilter, Category, Favorite, HeroSlide, Payment, PaymentEvent, Review, HubAppearance, HubVisitor, Advertisement, SubmissionNotice
from .payments.services import PaymentUnavailable, checkout_url_is_safe, exact_amount, start_checkout, verify_payment
from .payments.singpay import SingPayService

CONFIG = {"SINGPAY_API_KEY": "test-key", "SINGPAY_API_SECRET": "test-secret", "SINGPAY_MERCHANT_ID": "test-wallet",
          "SINGPAY_DISBURSEMENT_ID": "test-disbursement", "SINGPAY_WEBHOOK_SECRET": "test-webhook", "PUBLIC_BASE_URL": "http://testserver"}

@override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"])
class HubTestCase(TestCase):
    def setUp(self):
        media = tempfile.TemporaryDirectory(prefix="gaboma-hub-tests-")
        assert Path(media.name).resolve().is_relative_to(Path(tempfile.gettempdir()).resolve())
        self.addCleanup(media.cleanup)
        media_setting = override_settings(MEDIA_ROOT=media.name)
        media_setting.enable()
        self.addCleanup(media_setting.disable)
        self.user = User.objects.create_user("alice", email="alice@example.test", password="MotDePasseDeTest789!")
        self.other = User.objects.create_user("bob", password="AutreMotDePasse789!")
        self.admin = User.objects.create_superuser("admin-test", email="admin@example.test", password="AdminDeTest789!")
        self.category = Category.objects.create(name="Productivité", slug="productivite")
        self.app = Application.objects.create(name="Application externe", slug="application-externe", category=self.category,
            description="Un outil d'un autre éditeur.", website_url="https://example.com", submitted_by=self.user, fee_amount=2000)
    def image_upload(self, name="image.png"):
        output = BytesIO()
        Image.new("RGB", (64, 32), "blue").save(output, format="PNG")
        return SimpleUploadedFile(name, output.getvalue(), content_type="image/png")
    def payment(self, **kwargs):
        defaults = {"application": self.app, "user": self.user, "amount": 2000, "reference": "HUB-TEST-REFERENCE"}
        defaults.update(kwargs)
        return Payment.objects.create(**defaults)
    def remote(self, **kwargs):
        data = {"status": "success", "amount": 2000, "order_id": "REF-HUB-TEST-REFERENCE", "transaction_id": "provider-test-id", "raw": {"currency": "XAF", "portefeuille": "test-wallet"}}
        data.update(kwargs)
        return data

class HomepageOptionsTests(HubTestCase):
    def test_carousels_only_contain_published_apps_and_real_ratings(self):
        self.app.is_admin_added = True
        self.app.approve(self.admin)
        Review.objects.create(application=self.app, user=self.other, rating=5, is_visible=False)
        draft = Application.objects.create(name="Projet privé", slug="projet-prive", category=self.category, description="Privé", website_url="https://example.test")
        response = self.client.get("/")
        rails = response.context["discovery_rails"]
        self.assertFalse(any(rail["id"] == "rated-apps" for rail in rails))
        self.assertFalse(any(draft.pk == app.pk for rail in rails for app in rail["apps"]))
        Review.objects.create(application=self.app, user=self.user, rating=4)
        rails = self.client.get("/").context["discovery_rails"]
        rated = next(rail for rail in rails if rail["id"] == "rated-apps")
        self.assertEqual(rated["apps"][0].average_rating, 4)
    def test_search_and_favorites_do_not_display_unfiltered_carousels(self):
        for params in [{"q": "inexistant"}, {"vue": "favoris"}, {"categorie": "productivite"}]:
            response = self.client.get("/", params)
            self.assertEqual(response.context["discovery_rails"], [])
            self.assertNotContains(response, 'class="app-rail"')
    def test_layout_choice_preserves_filters_and_persists_in_session(self):
        response = self.client.get("/", {"affichage": "grid", "q": "outil", "categorie": "productivite", "vue": "favoris", "tri": "rating"})
        self.assertEqual(response.context["layout"], "grid")
        self.assertIn("q=outil", response.context["layout_urls"]["list"])
        self.assertIn("vue=favoris", response.context["layout_urls"]["list"])
        self.assertIn("tri=rating", response.context["layout_urls"]["list"])
        self.assertEqual(self.client.get("/").context["layout"], "grid")
        self.assertEqual(self.client.get("/", {"affichage": "list"}).context["layout"], "list")
        self.assertEqual(self.client.get("/", {"affichage": "bad"}).context["layout"], "list")
    def test_default_layout_is_grid_and_buttons_are_accessible(self):
        response = self.client.get("/")
        self.assertEqual(response.context["layout"], "grid")
        self.assertContains(response, 'aria-label="Affichage des applications"')
        self.assertContains(response, 'class="app-grid layout-grid"')
        self.assertContains(response, 'name="affichage" value="grid"')
    def test_hero_background_can_be_enabled_disabled_and_removed(self):
        appearance = HubAppearance.objects.create(hero_background="editorial/hero.webp")
        self.assertContains(self.client.get("/"), 'class="hero-background-image"')
        appearance.hero_background_enabled = False
        appearance.save()
        self.assertNotContains(self.client.get("/"), 'class="hero-background-image"')
        appearance.hero_background_enabled = True
        appearance.hero_background = ""
        appearance.save()
        self.assertContains(self.client.get("/"), "hub/images/libreville-damas.jpg")
    def test_only_active_in_date_advertisements_visible(self):
        now = timezone.now()
        base = {"image": "editorial/ad.webp", "is_active": True}
        Advertisement.objects.create(title="Annonce visible", sponsor="Équipe de test", target_url="https://example.com", **base)
        Advertisement.objects.create(title="Annonce expirée", ends_at=now-timedelta(seconds=1), **base)
        Advertisement.objects.create(title="Annonce future", starts_at=now+timedelta(days=1), **base)
        Advertisement.objects.create(title="Annonce désactivée", image="editorial/ad.webp", is_active=False)
        Advertisement.objects.create(title="Annonce sans image", is_active=True)
        response = self.client.get("/")
        self.assertContains(response, "Annonce visible")
        for name in ["Annonce expirée", "Annonce future", "Annonce désactivée", "Annonce sans image"]:
            self.assertNotContains(response, name)
        self.assertContains(response, "Publicité · Équipe de test")
        self.assertContains(response, 'rel="sponsored noopener noreferrer"')
    def test_ads_use_selected_placement_and_optional_link(self):
        Advertisement.objects.create(title="Sous catalogue", image="editorial/ad.webp", is_active=True, placement="catalogue")
        response = self.client.get("/", {"q": "test"})
        self.assertEqual(len(response.context["catalogue_ads"]), 1)
        self.assertEqual(len(response.context["discovery_ads"]), 0)
        self.assertContains(response, '<div class="ad-visual">')
    def test_bad_ad_dates_and_unsafe_target_rejected(self):
        ad = Advertisement(title="Test", image="editorial/ad.webp", target_url="javascript:alert(1)", starts_at=timezone.now(), ends_at=timezone.now()-timedelta(days=1))
        with self.assertRaises(ValidationError): ad.full_clean()
    def test_admin_can_upload_hero_and_ad_using_image_validation(self):
        self.client.force_login(self.admin)
        response = self.client.post(reverse("admin:hub_hubappearance_add"), {"hero_background": self.image_upload(), "hero_background_enabled": "on", "submission_fee": 2500, "hero_badge": "Gabon", "hero_title": "Nos apps", "hero_subtitle": "À découvrir", "hero_description": "Les créations locales", "showcase_enabled": "on", "discovery_enabled": "on", "slides-TOTAL_FORMS": "0", "slides-INITIAL_FORMS": "0", "slides-MIN_NUM_FORMS": "0", "slides-MAX_NUM_FORMS": "1000", "_save": "Enregistrer"})
        self.assertEqual(response.status_code, 302)
        self.assertTrue(HubAppearance.objects.get().hero_background.name.endswith(".webp"))
        self.assertFalse(AppearanceAdmin(HubAppearance, AdminSite()).has_delete_permission(RequestFactory().get('/')))
        response = self.client.post(reverse("admin:hub_advertisement_add"), {"title": "Campagne test", "image": self.image_upload(), "placement": "discovery", "order": 0, "is_active": "on", "_save": "Enregistrer"})
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Advertisement.objects.get().image.name.endswith(".webp"))
        self.assertContains(self.client.get("/"), "Campagne test")
    def test_regular_user_cannot_change_ad_or_hero_settings(self):
        self.client.force_login(self.user)
        for name in ["hub_hubappearance_add", "hub_advertisement_add"]:
            self.assertEqual(self.client.post(reverse(f"admin:{name}"), {}).status_code, 302)
        self.assertFalse(HubAppearance.objects.exists())
        self.assertFalse(Advertisement.objects.exists())

class CommunityTests(HubTestCase):
    def publish(self):
        self.app.is_admin_added = True
        self.app.approve(self.admin)
    def test_images_are_required_and_non_images_rejected(self):
        data = {"name": "App", "category": self.category.pk, "creator_name": "Créateur", "description": "Une app", "website_url": "https://example.com", "color": "blue", "confirmation": "on"}
        form = ApplicationForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn("logo", form.errors)
        self.assertIn("banner", form.errors)
        form = ApplicationForm(data=data, files={"logo": SimpleUploadedFile("fake.png", b"<script>alert(1)</script>"), "banner": self.image_upload()})
        self.assertFalse(form.is_valid())
        self.assertIn("logo", form.errors)
    def test_uploaded_images_saved_as_webp_and_existing_images_kept(self):
        self.client.force_login(self.user)
        response = self.client.post(reverse("hub:submit"), {"name": "Nouvelle app", "category": self.category.pk, "creator_name": "Équipe", "description": "Présentation", "about": "Texte complet", "website_url": "https://example.com", "color": "blue", "confirmation": "on", "logo": self.image_upload(), "banner": self.image_upload()})
        self.assertEqual(response.status_code, 302)
        app = Application.objects.get(name="Nouvelle app")
        self.assertTrue(app.logo.name.endswith(".webp"))
        self.assertTrue(app.banner.name.endswith(".webp"))
        with app.logo.open("rb") as stream:
            self.assertEqual(Image.open(stream).format, "WEBP")
        form = ApplicationForm(instance=app)
        self.assertFalse(form.fields["logo"].required)
        app.is_admin_added = True
        app.approve(self.admin)
        self.assertContains(self.client.get(app.get_absolute_url()), app.banner.url)
        self.assertContains(self.client.get("/"), app.logo.url)
    def test_image_size_limit(self):
        from .images import PublicImageField
        with self.assertRaises(ValidationError):
            PublicImageField().clean(SimpleUploadedFile("large.png", b"0" * (5 * 1024 * 1024 + 1)))
    def test_review_login_post_and_csrf_required(self):
        self.publish()
        url = reverse("hub:review", args=[self.app.slug])
        self.assertEqual(self.client.post(url, {"rating": 5}).status_code, 302)
        self.assertFalse(Review.objects.exists())
        self.client.force_login(self.other)
        self.assertEqual(self.client.get(url).status_code, 405)
        secured = Client(enforce_csrf_checks=True)
        secured.force_login(self.other)
        self.assertEqual(secured.post(url, {"rating": 5}).status_code, 403)
    def test_review_updates_one_per_person_and_escapes_comments(self):
        self.publish()
        self.client.force_login(self.other)
        url = reverse("hub:review", args=[self.app.slug])
        self.client.post(url, {"rating": 4, "comment": "Très utile"})
        self.client.post(url, {"rating": 5, "comment": "<script>alert('x')</script>"})
        self.assertEqual(Review.objects.count(), 1)
        self.assertEqual(Review.objects.get().rating, 5)
        page = self.client.get(self.app.get_absolute_url())
        self.assertNotContains(page, "<script>alert('x')</script>")
        self.assertContains(page, "&lt;script&gt;")
    def test_invalid_ratings_and_long_comments_rejected(self):
        self.publish()
        self.client.force_login(self.other)
        url = reverse("hub:review", args=[self.app.slug])
        for rating in [0, 6, "4.5", "bad"]:
            self.client.post(url, {"rating": rating})
        self.client.post(url, {"rating": 5, "comment": "x" * 2001})
        self.assertEqual(Review.objects.count(), 0)
    def test_hidden_review_excluded_and_cannot_be_republished(self):
        self.publish()
        Review.objects.create(application=self.app, user=self.other, rating=1, comment="Masqué", is_visible=False)
        Review.objects.create(application=self.app, user=self.user, rating=5, comment="Visible")
        page = self.client.get(self.app.get_absolute_url())
        self.assertEqual(page.context["review_stats"]["average"], 5)
        self.assertEqual(page.context["review_stats"]["count"], 1)
        self.assertNotContains(page, "Masqué")
        self.client.force_login(self.other)
        self.client.post(reverse("hub:review", args=[self.app.slug]), {"rating": 5, "is_visible": True})
        self.assertFalse(Review.objects.get(user=self.other).is_visible)
    def test_delete_review_only_affects_own_review(self):
        self.publish()
        Review.objects.create(application=self.app, user=self.user, rating=4)
        Review.objects.create(application=self.app, user=self.other, rating=2)
        self.client.force_login(self.other)
        self.client.post(reverse("hub:delete-review", args=[self.app.slug]), {"user": self.user.pk})
        self.assertEqual(Review.objects.get().user, self.user)
    def test_draft_apps_cannot_receive_reviews(self):
        self.client.force_login(self.other)
        self.assertEqual(self.client.post(reverse("hub:review", args=[self.app.slug]), {"rating": 5}).status_code, 404)
    def test_rating_sort_excludes_hidden_ratings(self):
        self.publish()
        Review.objects.create(application=self.app, user=self.other, rating=4)
        Review.objects.create(application=self.app, user=self.user, rating=1, is_visible=False)
        page = self.client.get("/", {"tri": "rating"})
        result = list(page.context["applications"])[0]
        self.assertEqual(result.average_rating, 4)
        self.assertEqual(result.review_count, 1)

class CatalogueTests(HubTestCase):
    def test_only_published_apps_visible(self):
        response = self.client.get(reverse("hub:home"))
        self.assertNotContains(response, self.app.name)
        self.assertEqual(self.client.get(self.app.get_absolute_url()).status_code, 404)
        self.app.is_admin_added = True
        self.app.approve(self.admin)
        self.assertContains(self.client.get(reverse("hub:home")), self.app.name)
    def test_seed_is_idempotent_and_preserves_edits(self):
        call_command("seed_hub", verbosity=0)
        call_command("seed_hub", verbosity=0)
        self.assertEqual(Application.objects.filter(is_admin_added=True).count(), 6)
        app = Application.objects.get(slug="zanalyze")
        app.description = "Texte personnalisé"
        app.save()
        call_command("seed_hub", verbosity=0)
        app.refresh_from_db()
        self.assertEqual(app.description, "Texte personnalisé")
    def test_catalogue_loads_the_next_page_when_the_directory_grows(self):
        from hub.views import CATALOGUE_PAGE_SIZE
        for index in range(CATALOGUE_PAGE_SIZE + 1):
            app = Application.objects.create(name=f"Lot {index:02d}", slug=f"lot-{index:02d}", category=self.category, description="Une application du lot.", website_url="https://example.com", is_admin_added=True)
            app.approve(self.admin)
        first = self.client.get("/")
        self.assertEqual(len(first.context["applications"]), CATALOGUE_PAGE_SIZE)
        self.assertContains(first, 'class="catalogue-sentinel"')
        second = self.client.get(reverse("hub:catalogue"), {"page": 2})
        self.assertEqual(len(second.context["applications"]), 1)
        self.assertNotContains(second, "<html")
        self.assertEqual(len(self.client.get(reverse("hub:catalogue"), {"page": "9999"}).context["applications"]), 0)
    def test_discovery_rails_stay_short_when_the_catalogue_grows(self):
        from hub.views import RAIL_SIZE
        for index in range(RAIL_SIZE + 4):
            app = Application.objects.create(name=f"Rail {index:02d}", slug=f"rail-{index:02d}", category=self.category, description="Une application du rail.", website_url="https://example.com", is_admin_added=True)
            app.approve(self.admin)
        home = self.client.get("/")
        rails = {rail["id"]: rail for rail in home.context["discovery_rails"]}
        self.assertLessEqual(len(rails["available-apps"]["apps"]), RAIL_SIZE)
        self.assertTrue(rails["available-apps"]["more"])
        self.assertContains(home, "Tout le répertoire")
        self.assertIn("about", home.context["applications"][0].get_deferred_fields())
    def test_search_and_category_filters(self):
        self.app.is_admin_added = True
        self.app.approve(self.admin)
        self.assertContains(self.client.get("/", {"q": "externe"}), self.app.name)
        self.assertNotContains(self.client.get("/", {"q": "introuvable"}), self.app.name)
        self.assertNotContains(self.client.get("/", {"categorie": "absente"}), self.app.name)
        self.assertEqual(self.client.get("/", {"q": "externe"}).context["total"], 1)
        self.assertEqual(self.client.get("/", {"q": "introuvable"}).context["total"], 0)
        self.assertEqual(self.client.get("/", {"categorie": "absente"}).context["total"], 0)
        self.assertEqual(self.client.get("/", {"vue": "favoris"}).context["total"], 0)
    def test_favorites_require_login_and_post(self):
        self.app.is_admin_added = True
        self.app.approve(self.admin)
        url = reverse("hub:favorite", args=[self.app.public_id])
        self.assertEqual(self.client.post(url).status_code, 302)
        self.client.force_login(self.user)
        self.assertEqual(self.client.get(url).status_code, 405)
        self.client.post(url)
        self.assertTrue(Favorite.objects.filter(user=self.user, application=self.app).exists())
        self.assertContains(self.client.get("/", {"vue": "favoris"}), self.app.name)
        self.client.post(url)
        self.assertFalse(Favorite.objects.filter(user=self.user).exists())
    def test_favorite_next_is_not_an_open_redirect(self):
        self.app.is_admin_added = True
        self.app.approve(self.admin)
        self.client.force_login(self.user)
        response = self.client.post(reverse("hub:favorite", args=[self.app.public_id]), {"next": "https://evil.example/"})
        self.assertEqual(response.url, "/")
    def test_favorite_toggle_answers_without_a_reload(self):
        self.app.is_admin_added = True
        self.app.approve(self.admin)
        self.client.force_login(self.user)
        url = reverse("hub:favorite", args=[self.app.public_id])
        liked = self.client.post(url, HTTP_X_REQUESTED_WITH="fetch")
        self.assertEqual(liked.status_code, 200)
        self.assertEqual(liked.json()["liked"], True)
        removed = self.client.post(url, HTTP_X_REQUESTED_WITH="fetch")
        self.assertEqual(removed.json()["liked"], False)
        self.assertFalse(Favorite.objects.filter(user=self.user, application=self.app).exists())
    def test_foreign_submission_and_payment_are_private(self):
        payment = self.payment()
        self.client.force_login(self.other)
        for name, value in [("submission", self.app.public_id), ("edit", self.app.public_id), ("payment-return", payment.public_id)]:
            self.assertEqual(self.client.get(reverse(f"hub:{name}", args=[value])).status_code, 404)
        self.assertEqual(self.client.post(reverse("hub:checkout", args=[self.app.public_id]), {"accept": "yes"}).status_code, 404)
    def test_submission_ignores_forged_admin_fields(self):
        self.client.force_login(self.user)
        response = self.client.post(reverse("hub:submit"), {"name": "App d'un tiers", "category": self.category.pk,
            "creator_name": "Équipe de test", "logo": self.image_upload("logo.png"), "banner": self.image_upload("banner.png"),
            "description": "Un service public utile", "website_url": "https://example.org", "color": "blue", "confirmation": "on",
            "status": "published", "is_admin_added": "true", "fee_amount": 0, "submitted_by": self.other.pk})
        self.assertEqual(response.status_code, 302)
        app = Application.objects.get(name="App d'un tiers")
        self.assertEqual(app.status, Application.Status.DRAFT)
        self.assertEqual(app.fee_amount, 5000)
        self.assertEqual(app.submitted_by, self.user)
        self.assertFalse(app.is_admin_added)
    def test_unsafe_urls_are_rejected(self):
        for url in ["javascript:alert(1)", "https://user:password@example.com"]:
            form = ApplicationForm(data={"name": "Mauvais lien", "category": self.category.pk, "description": "Description",
                "website_url": url, "color": "blue", "confirmation": "on"})
            self.assertFalse(form.is_valid())
    def test_unpaid_user_application_cannot_be_published(self):
        with self.assertRaises(ValidationError): self.app.approve(self.admin)
        self.app.status = Application.Status.PUBLISHED
        with self.assertRaises(ValidationError): self.app.full_clean()
    def test_admin_can_add_without_payment(self):
        self.app.is_admin_added = True
        self.app.approve(self.admin)
        self.assertEqual(self.app.status, Application.Status.PUBLISHED)
        self.assertFalse(Payment.objects.exists())
    def test_administration_is_not_available_to_regular_user(self):
        self.client.force_login(self.user)
        self.assertEqual(self.client.get("/admin/").status_code, 302)
    def test_regular_submission_post_requires_csrf(self):
        secured = Client(enforce_csrf_checks=True)
        secured.force_login(self.user)
        self.assertEqual(secured.post(reverse("hub:submit"), {}).status_code, 403)
    def test_signup_and_auth_pages_work(self):
        for url in ["/inscription/", "/compte/login/", "/compte/password_reset/"]:
            self.assertEqual(self.client.get(url).status_code, 200)
        response = self.client.post("/inscription/", {"username": "nouveau", "email": "new@example.test",
            "password1": "LongMotDePasseInattendu789!", "password2": "LongMotDePasseInattendu789!", "accept_terms": "on"})
        self.assertEqual(response.status_code, 302)
        self.assertTrue(User.objects.filter(username="nouveau").exists())
    def test_admin_add_form_publishes_free_app(self):
        self.client.force_login(self.admin)
        response = self.client.post(reverse("admin:hub_application_add"), {"name": "App administrateur", "slug": "app-admin",
            "logo": self.image_upload("logo.png"), "banner": self.image_upload("banner.png"),
            "category": self.category.pk, "description": "Application ajoutée gratuitement", "website_url": "https://example.net",
            "color": "sand", "icon": "custom", "status": "published", "moderation_note": "", "_save": "Enregistrer"})
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Application.objects.get(slug="app-admin").is_admin_added)

@override_settings(**CONFIG)
class PaymentTests(HubTestCase):
    def test_checkout_amount_is_server_side_and_repeated_click_reuses_pending(self):
        with patch("hub.payments.services.singpay_service.init_payment", return_value=(True, {"payment_url": "https://gateway.singpay.ga/payment/provider-test-id", "transaction_id": "provider-test-id"})) as init:
            first = start_checkout(self.app, self.user)
            second = start_checkout(self.app, self.user)
        self.assertEqual(first.pk, second.pk)
        self.assertEqual(init.call_count, 1)
        self.assertEqual(init.call_args.kwargs["amount"], 2000)
        self.assertEqual(Payment.objects.count(), 1)
    @override_settings(SINGPAY_API_KEY="")
    def test_missing_credentials_never_grant_free_publication(self):
        with self.assertRaises(PaymentUnavailable): start_checkout(self.app, self.user)
        self.assertFalse(Payment.objects.exists())
        self.app.refresh_from_db()
        self.assertEqual(self.app.status, Application.Status.DRAFT)
    def test_uncertain_initialization_does_not_create_another_charge(self):
        with patch("hub.payments.services.singpay_service.init_payment", side_effect=TimeoutError) as init:
            payment = start_checkout(self.app, self.user)
            retry = start_checkout(self.app, self.user)
        self.assertEqual(payment.pk, retry.pk)
        self.assertEqual(init.call_count, 1)
        self.assertEqual(payment.status, Payment.Status.PENDING)
    def test_provider_checkout_url_is_validated(self):
        for url in ["https://evil.example/pay", "http://gateway.singpay.ga/pay", "https://gateway.singpay.ga.evil.example/", "https://user:password@gateway.singpay.ga/"]:
            self.assertFalse(checkout_url_is_safe(url))
        self.assertTrue(checkout_url_is_safe("https://gateway.singpay.ga/payment/abc"))
    def test_exact_fcfa_parsing(self):
        for value in [None, True, "2000.9", "NaN", "Infinity", "invalid"]: self.assertIsNone(exact_amount(value))
        self.assertEqual(exact_amount("2000.00"), 2000)
    def test_paid_requires_server_verification_and_moderation(self):
        payment = self.payment()
        with patch("hub.payments.services.singpay_service.find_payment_by_reference", return_value=(True, self.remote())):
            verify_payment(payment)
        payment.refresh_from_db(); self.app.refresh_from_db()
        self.assertEqual(payment.status, Payment.Status.SUCCESS)
        self.assertIsNotNone(payment.verified_at)
        self.assertEqual(self.app.status, Application.Status.DRAFT)
        self.assertNotContains(self.client.get("/"), self.app.name)
        self.client.force_login(self.other)
        self.assertEqual(self.client.post(reverse("hub:confirm", args=[self.app.public_id]), {"confirm": "yes"}).status_code, 404)
        self.client.force_login(self.user)
        self.client.post(reverse("hub:confirm", args=[self.app.public_id]), {})
        self.app.refresh_from_db()
        self.assertEqual(self.app.status, Application.Status.DRAFT)
        published = self.client.post(reverse("hub:confirm", args=[self.app.public_id]), {"confirm": "yes"})
        self.assertEqual(published.status_code, 302)
        self.assertIn("published=1", published["Location"])
        self.app.refresh_from_db()
        self.assertEqual(self.app.status, Application.Status.PUBLISHED)
        self.assertContains(self.client.get(published["Location"]), "Félicitations")
        self.assertContains(self.client.get("/"), self.app.name)
        notice = SubmissionNotice.objects.get(application=self.app)
        self.assertIsNone(notice.seen_at)
        self.client.force_login(self.admin)
        page = self.client.get(reverse("admin:hub_application_notices"))
        self.assertContains(page, self.app.name)
        self.assertContains(page, "Fiche créée")
        self.assertContains(page, "Paiement confirmé")
        self.assertContains(page, "Publiée")
        self.client.post(reverse("admin:hub_application_notices"))
        notice.refresh_from_db()
        self.assertIsNotNone(notice.seen_at)
        self.assertNotContains(self.client.get(reverse("admin:index")), "console-notice-count")
    def test_repeated_verified_callback_is_idempotent(self):
        payment = self.payment()
        with patch("hub.payments.services.singpay_service.find_payment_by_reference", return_value=(True, self.remote())) as verify:
            verify_payment(payment)
            before = Payment.objects.get(pk=payment.pk).verified_at
            verify_payment(payment)
        self.assertEqual(verify.call_count, 1)
        self.assertEqual(Payment.objects.get(pk=payment.pk).verified_at, before)
    def test_missing_or_wrong_amount_never_confirms(self):
        payment = self.payment()
        for amount in [None, "", 1999, 2001, "2000.01", True]:
            with patch("hub.payments.services.singpay_service.find_payment_by_reference", return_value=(True, self.remote(amount=amount))): verify_payment(payment)
            payment.refresh_from_db()
            self.assertEqual(payment.status, Payment.Status.PENDING)
    def test_missing_or_wrong_reference_never_confirms(self):
        payment = self.payment()
        for ref in [None, "", "REF-OTHER-ORDER"]:
            with patch("hub.payments.services.singpay_service.find_payment_by_reference", return_value=(True, self.remote(order_id=ref))): verify_payment(payment)
            payment.refresh_from_db()
            self.assertEqual(payment.status, Payment.Status.PENDING)
    def test_wrong_currency_or_wallet_never_confirms(self):
        payment = self.payment()
        for raw in [{"currency": "USD"}, {"portefeuille": "other-wallet"}]:
            with patch("hub.payments.services.singpay_service.find_payment_by_reference", return_value=(True, self.remote(raw=raw))): verify_payment(payment)
            payment.refresh_from_db()
            self.assertEqual(payment.status, Payment.Status.PENDING)
    def test_provider_id_is_not_reusable(self):
        self.payment(status=Payment.Status.SUCCESS, verified_at=timezone.now(), provider_transaction_id="reused", reference="ALREADY-PAID")
        payment = self.payment(reference="SECOND")
        with patch("hub.payments.services.singpay_service.find_payment_by_reference", return_value=(True, self.remote(order_id="REF-SECOND", transaction_id="reused"))): verify_payment(payment)
        payment.refresh_from_db()
        self.assertEqual(payment.status, Payment.Status.PENDING)
    def test_a_late_payment_does_not_restore_archived_app(self):
        payment = self.payment()
        self.app.status = Application.Status.ARCHIVED; self.app.save()
        with patch("hub.payments.services.singpay_service.find_payment_by_reference", return_value=(True, self.remote())): verify_payment(payment)
        self.app.refresh_from_db()
        self.assertEqual(self.app.status, Application.Status.ARCHIVED)
    def test_failed_result_cannot_downgrade_success(self):
        payment = self.payment(status=Payment.Status.SUCCESS, verified_at=timezone.now())
        with patch("hub.payments.services.singpay_service.find_payment_by_reference", return_value=(True, self.remote(status="failed"))) as remote:
            verify_payment(payment)
        self.assertFalse(remote.called)
        payment.refresh_from_db(); self.assertEqual(payment.status, Payment.Status.SUCCESS)
    def test_browser_return_is_not_proof(self):
        payment = self.payment()
        self.client.force_login(self.user)
        self.client.get(reverse("hub:payment-return", args=[payment.public_id]), {"status": "success", "amount": "2000", "transaction_id": "someone-elses-payment"})
        payment.refresh_from_db()
        self.assertEqual(payment.status, Payment.Status.PENDING)
        self.assertIsNone(payment.provider_transaction_id)
    def test_forged_checkout_amount_ignored(self):
        self.client.force_login(self.user)
        with patch("hub.payments.services.singpay_service.init_payment", return_value=(True, {"payment_url": "https://gateway.singpay.ga/pay/test"})) as init:
            self.client.post(reverse("hub:checkout", args=[self.app.public_id]), {"amount": "1", "accept": "yes"})
        self.assertEqual(init.call_args.kwargs["amount"], 2000)
    def test_pending_payment_freezes_edits(self):
        self.payment()
        self.client.force_login(self.user)
        self.assertEqual(self.client.get(reverse("hub:edit", args=[self.app.public_id])).status_code, 302)
    def test_signed_webhook_still_requires_api_check(self):
        payment = self.payment()
        payload = {"reference": "REF-HUB-TEST-REFERENCE", "status": "success", "amount": 2000}
        body = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        timestamp = str(int(time.time()))
        signature = hmac.new(b"test-webhook", (timestamp + body).encode(), hashlib.sha256).hexdigest()
        with patch("hub.payments.services.singpay_service.find_payment_by_reference", return_value=(False, {})):
            result = self.client.post(reverse("hub:singpay-callback"), data=body, content_type="application/json", HTTP_X_SIGNATURE=signature, HTTP_X_TIMESTAMP=timestamp)
        self.assertEqual(result.status_code, 503)
        payment.refresh_from_db(); self.assertEqual(payment.status, Payment.Status.PENDING)
    def test_unsigned_webhook_is_rejected(self):
        self.payment()
        result = self.client.post(reverse("hub:singpay-callback"), data=json.dumps({"reference": "HUB-TEST-REFERENCE", "status": "success"}), content_type="application/json")
        self.assertEqual(result.status_code, 400)
        self.assertFalse(PaymentEvent.objects.get().signature_valid)
    def test_verified_signed_webhook_moves_to_review(self):
        self.payment()
        body = json.dumps({"reference": "REF-HUB-TEST-REFERENCE"}, sort_keys=True, separators=(",", ":"))
        timestamp = str(int(time.time()))
        signature = hmac.new(b"test-webhook", (timestamp + body).encode(), hashlib.sha256).hexdigest()
        with patch("hub.payments.services.singpay_service.find_payment_by_reference", return_value=(True, self.remote())):
            result = self.client.post(reverse("hub:singpay-callback"), data=body, content_type="application/json", HTTP_X_SIGNATURE=signature, HTTP_X_TIMESTAMP=timestamp)
        self.assertEqual(result.status_code, 200)
        self.app.refresh_from_db(); self.assertEqual(self.app.status, Application.Status.DRAFT)
    def test_stale_signature_is_rejected(self):
        body = "{}"; timestamp = str(int(time.time()) - 1000)
        signature = hmac.new(b"test-webhook", (timestamp + body).encode(), hashlib.sha256).hexdigest()
        self.assertFalse(SingPayService().verify_webhook_signature(body, signature, timestamp))
    def test_raw_array_and_ambiguous_search(self):
        service = SingPayService()
        self.assertEqual(service._unwrap_transaction({"data": [{"reference": "x"}]}), {"reference": "x"})
        self.assertEqual(service._unwrap_transaction({"data": [{"reference": "x"}, {"reference": "y"}]}), {})


class ManagedShowcaseTests(HubTestCase):
    def test_showcase_schedule_order_and_disabled_items(self):
        now = timezone.now()
        for title, extra in [
            ("Second visuel", {"order": 2}), ("Premier visuel", {"order": 1}),
            ("Pas encore", {"starts_at": now + timedelta(days=1)}),
            ("Terminé", {"ends_at": now - timedelta(days=1)}),
            ("Désactivé", {"is_active": False})]:
            values = {"title": title, "image": "editorial/test.webp", "placement": "hero", "is_active": True}
            values.update(extra)
            Advertisement.objects.create(**values)
        response = self.client.get("/")
        self.assertEqual([ad.title for ad in response.context["showcase_ads"]], ["Premier visuel", "Second visuel"])
        self.assertNotContains(response, 'id="hero-showcase"')
        self.assertContains(response, 'class="hub-hero-art"')
        self.assertNotContains(response, "Pas encore")
        self.assertNotContains(response, "Terminé")
        self.assertNotContains(response, "Désactivé")
        self.assertNotContains(response, "Premier visuel")

    def test_settings_control_copy_sections_and_escape_text(self):
        HubAppearance.objects.create(hero_title="<script>test</script>", site_name="Hub local", footer_lead="<b>Pied</b>", catalogue_title="Le catalogue local", support_email="aide@example.com", showcase_enabled=False, discovery_enabled=False)
        response = self.client.get("/")
        self.assertContains(response, "&lt;script&gt;test&lt;/script&gt;")
        self.assertContains(response, "Hub local")
        self.assertContains(response, "&lt;b&gt;Pied&lt;/b&gt;")
        self.assertContains(response, "Le catalogue local")
        self.assertContains(response, "mailto:aide@example.com")
        self.assertNotContains(response, 'id="hero-showcase"')
        self.assertEqual(response.context["discovery_rails"], [])

    def test_directory_cards_open_the_matching_catalogue(self):
        commerce = Category.objects.get(slug="commerce")
        Application.objects.create(name="Boutique test", slug="boutique-test", category=commerce, description="Une boutique.", website_url="https://example.com", is_admin_added=True, status=Application.Status.PUBLISHED)
        home = self.client.get("/")
        self.assertContains(home, 'href="/?categorie=commerce#applications"')
        self.assertContains(home, 'href="/?categorie=administration#applications"')
        self.assertContains(home, ">Administration</span>")
        self.assertNotContains(home, ">Communauté</span>")
        filtered = self.client.get("/", {"categorie": "commerce"})
        self.assertEqual(filtered.context["selected_category"], "commerce")
        self.assertContains(filtered, "Boutique test")
        self.assertNotContains(filtered, "Application externe")
        hidden = CatalogueFilter.objects.get(label="Administration")
        hidden.is_active = False
        hidden.save()
        self.assertNotContains(self.client.get("/"), ">Administration</span>")

    def test_admin_adds_and_retires_a_directory_filter(self):
        self.client.force_login(self.admin)
        response = self.client.post(reverse("admin:hub_cataloguefilter_add"), {"label": "Éducation", "category": self.category.pk, "icon": "star", "tone": "gold", "order": 8, "is_active": "on", "_save": "Enregistrer"})
        self.assertEqual(response.status_code, 302)
        self.assertContains(self.client.get("/"), 'href="/?categorie=productivite#applications"')
        created = CatalogueFilter.objects.get(label="Éducation")
        response = self.client.post(reverse("admin:hub_cataloguefilter_change", args=[created.pk]), {"label": "Éducation", "category": self.category.pk, "icon": "star", "tone": "gold", "order": 8, "_save": "Enregistrer"})
        self.assertEqual(response.status_code, 302)
        self.assertFalse(CatalogueFilter.objects.get(pk=created.pk).is_active)
        self.assertNotContains(self.client.get("/"), ">Éducation</span>")

    def test_logo_and_hero_slides_rotate_from_hub_settings(self):
        appearance = HubAppearance.objects.create(logo="editorial/logo.webp")
        HeroSlide.objects.create(appearance=appearance, image="editorial/a.webp", alt="Libreville", order=1)
        HeroSlide.objects.create(appearance=appearance, image="editorial/b.webp", alt="Marché caché", order=0, is_active=False)
        HeroSlide.objects.create(appearance=appearance, image="editorial/c.webp", alt="Côte", order=2)
        page = self.client.get("/")
        self.assertContains(page, 'class="brand-logo"')
        self.assertContains(page, "editorial/logo.webp")
        self.assertContains(page, "Libreville")
        self.assertContains(page, "Côte")
        self.assertNotContains(page, "Marché caché")
        self.assertContains(page, "data-hero-next")

    def test_public_layout_price_visitors_and_admin_logo(self):
        home = self.client.get("/")
        self.assertEqual(home.context["submission_fee"], 5000)
        self.assertContains(home, "Vos applications 100% Gaboma")
        self.assertContains(home, 'class="hero-poles"')
        self.assertContains(home, "LE GABON NUMÉRIQUE.")
        self.assertContains(home, 'class="gabon-flag"')
        self.assertNotContains(home, "Pensé au Gabon")
        self.assertNotContains(home, 'class="compact-action"')
        self.client.get("/")
        self.assertEqual(HubVisitor.objects.count(), 1)
        Client().get("/")
        self.assertEqual(HubVisitor.objects.count(), 2)
        login_page = self.client.get(reverse("login"))
        signup_page = self.client.get(reverse("hub:signup"))
        self.assertContains(login_page, 'class="auth-switch"')
        self.assertContains(login_page, "Inscription")
        self.assertContains(signup_page, "Créer mon compte")
        self.assertContains(signup_page, 'aria-selected="true"')
        self.client.force_login(self.admin)
        self.client.get("/")
        self.assertEqual(HubVisitor.objects.count(), 2)
        console = self.client.get(reverse("admin:index"))
        self.assertContains(console, "Visiteurs uniques")
        self.assertContains(console, "Logo du Hub")
        self.assertNotContains(self.client.get(reverse("hub:dashboard")), ">Administration</a>")
        uploaded = self.client.post(reverse("admin:hub_hubappearance_logo"), {"logo": self.image_upload()})
        self.assertEqual(uploaded.status_code, 302)
        self.assertTrue(HubAppearance.objects.get().logo.name.endswith(".webp"))
        self.assertContains(self.client.get("/"), 'class="brand-logo"')

    def test_admin_uploads_hero_slide(self):
        self.client.force_login(self.admin)
        response = self.client.post(reverse("admin:hub_advertisement_add"), {"title": "Vitrine test", "image": self.image_upload(), "placement": "hero", "order": 0, "is_active": "on", "_save": "Enregistrer"})
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Advertisement.objects.get().image.name.endswith(".webp"))
        self.assertContains(self.client.get("/"), "Vitrine test")

    def test_price_validation_and_admin_permissions(self):
        for price in [0, -1, 1000001]:
            with self.assertRaises(ValidationError): HubAppearance(submission_fee=price).full_clean()
        self.client.force_login(self.user)
        self.assertEqual(self.client.get(reverse("admin:hub_hubappearance_add")).status_code, 302)

    @override_settings(**CONFIG)
    def test_new_fee_is_frozen_and_verified_at_checkout(self):
        config = HubAppearance.objects.create(submission_fee=3500)
        self.client.force_login(self.user)
        response = self.client.post(reverse("hub:submit"), {"name": "Tarif personnalisé", "category": self.category.pk,
            "creator_name": "Équipe", "logo": self.image_upload("logo.png"), "banner": self.image_upload("banner.png"),
            "description": "Un service", "website_url": "https://example.org", "color": "blue", "confirmation": "on", "fee_amount": 1})
        self.assertEqual(response.status_code, 302)
        app = Application.objects.get(name="Tarif personnalisé")
        self.assertEqual(app.fee_amount, 3500)
        config.submission_fee = 5000
        config.save()
        self.assertEqual(self.client.get(reverse("hub:edit", args=[app.public_id])).context["submission_fee"], 3500)
        self.assertEqual(self.client.get(reverse("hub:submit")).context["submission_fee"], 5000)
        with patch("hub.payments.services.singpay_service.init_payment", return_value=(True, {"payment_url": "https://gateway.singpay.ga/payment/test", "transaction_id": "provider-test-id"})) as init:
            payment = start_checkout(app, self.user)
        self.assertEqual(init.call_args.kwargs["amount"], 3500)
        remote = self.remote(amount=3500, order_id=payment.reference)
        with patch("hub.payments.services.singpay_service.find_payment_by_reference", return_value=(True, remote)):
            verify_payment(payment)
        self.assertEqual(payment.status, Payment.Status.SUCCESS)
        app.refresh_from_db()
        self.assertTrue(app.paid)
        self.assertEqual((payment.valid_until - payment.verified_at).days, 365)

    def test_expired_subscription_renews_at_the_current_annual_price(self):
        HubAppearance.objects.create(submission_fee=2500)
        payment = self.payment(status=Payment.Status.SUCCESS, verified_at=timezone.now())
        Payment.objects.filter(pk=payment.pk).update(valid_until=timezone.now() - timedelta(days=1))
        self.assertFalse(Application.objects.get(pk=self.app.pk).paid)
        with patch("hub.payments.services.singpay_service.init_payment", return_value=(True, {"payment_url": "https://gateway.singpay.ga/payment/renewal", "transaction_id": "provider-renewal"})) as init:
            renewed = start_checkout(self.app, self.user)
        self.assertNotEqual(renewed.pk, payment.pk)
        self.assertEqual(renewed.amount, 2500)
        self.assertEqual(init.call_args.kwargs["amount"], 2500)
        self.assertEqual(Application.objects.get(pk=self.app.pk).fee_amount, 2500)

    def test_payment_screen_sets_the_annual_fee(self):
        self.client.force_login(self.admin)
        page = self.client.get(reverse("admin:hub_payment_changelist"))
        self.assertContains(page, "Tarif annuel")
        self.assertContains(page, 'value="5000"')
        refused = self.client.post(reverse("admin:hub_payment_changelist"), {"submission_fee": "0", "set_submission_fee": "1"})
        self.assertEqual(refused.status_code, 302)
        self.assertFalse(HubAppearance.objects.exists())
        saved = self.client.post(reverse("admin:hub_payment_changelist"), {"submission_fee": "1800", "set_submission_fee": "1"})
        self.assertEqual(saved.status_code, 302)
        self.assertEqual(HubAppearance.objects.get().submission_fee, 1800)
        self.assertEqual(self.client.get("/").context["submission_fee"], 1800)

class QuickRelatedTests(HubTestCase):
    def test_category_and_depositor_can_be_added_without_leaving_admin(self):
        self.client.force_login(self.admin)
        form = self.client.get(reverse("admin:hub_application_quick_category"))
        self.assertEqual(form.status_code, 200)
        self.assertContains(form, 'name="name"')
        created = self.client.post(reverse("admin:hub_application_quick_category"), {"name": "Santé"}, HTTP_X_REQUESTED_WITH="fetch")
        self.assertEqual(created.status_code, 200)
        payload = created.json()
        self.assertTrue(payload["ok"])
        self.assertEqual(Category.objects.get(pk=payload["value"]).slug, "sante")
        duplicate = self.client.post(reverse("admin:hub_application_quick_category"), {"name": "santé"}, HTTP_X_REQUESTED_WITH="fetch")
        self.assertEqual(duplicate.status_code, 400)
        depositor = self.client.post(reverse("admin:hub_application_quick_depositor"), {
            "username": "deposant-test", "email": "d@example.test", "password": "LongMotDePasseInattendu789!",
            "first_name": "Awa", "last_name": "Nguema",
        }, HTTP_X_REQUESTED_WITH="fetch")
        self.assertEqual(depositor.status_code, 200)
        self.assertTrue(depositor.json()["ok"])
        self.assertFalse(User.objects.get(username="deposant-test").is_staff)
        self.client.logout()
        self.assertEqual(self.client.get(reverse("admin:hub_application_quick_category")).status_code, 302)

class TermsAndDirectoryTests(HubTestCase):
    def test_terms_are_public_and_the_directory_filters(self):
        page = self.client.get(reverse("hub:terms"))
        self.assertContains(page, "Conditions générales d'utilisation")
        self.assertContains(page, "répertoire")
        self.client.force_login(self.user)
        self.assertContains(self.client.get(reverse("hub:submit")), reverse("hub:terms"))
        self.client.force_login(self.admin)
        listing = self.client.get(reverse("admin:hub_application_changelist"))
        self.assertContains(listing, "console-chip-row")
        self.assertContains(listing, "Application externe")
        offered = self.client.get(reverse("admin:hub_application_changelist"), {"abonnement": "offert"})
        self.assertNotContains(offered, "Application externe")
        due = self.client.get(reverse("admin:hub_application_changelist"), {"abonnement": "regler"})
        self.assertContains(due, "Application externe")
