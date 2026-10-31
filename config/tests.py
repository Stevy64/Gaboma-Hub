from unittest.mock import patch
from django.test import TestCase, override_settings

@override_settings(SECURE_SSL_REDIRECT=True)
class HealthTests(TestCase):
    def test_live_is_available_over_internal_http(self):
        self.assertEqual(self.client.get('/health/live/').status_code, 200)

    def test_ready_checks_dependencies(self):
        self.assertEqual(self.client.get('/health/ready/').status_code, 200)

    @patch('config.health.cache.get', side_effect=ConnectionError('secret-host'))
    def test_failure_does_not_expose_connection_details(self, mocked):
        response = self.client.get('/health/ready/')
        self.assertEqual(response.status_code, 503)
        self.assertNotIn(b'secret-host', response.content)


class PwaTests(TestCase):
    def test_manifest_and_scoped_worker(self):
        manifest = self.client.get('/manifest.webmanifest').json()
        self.assertEqual(manifest['display'], 'standalone')
        self.assertEqual(len(manifest['icons']), 3)
        response = self.client.get('/sw.js')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Service-Worker-Allowed'], '/')
        self.assertIn('no-store', response['Cache-Control'])
        self.assertNotIn(b'__ASSETS__', response.content)
        self.assertNotIn(b'__REVISION__', response.content)

    def test_retired_offline_endpoints_are_unavailable(self):
        self.assertEqual(self.client.get('/hors-ligne/').status_code, 404)
        self.assertEqual(self.client.get('/pwa/catalogue.json').status_code, 404)

    def test_install_page_is_retired_and_native_files_are_absent_by_default(self):
        self.assertEqual(self.client.get('/installer/').status_code, 404)
        self.assertEqual(self.client.get('/applications-natives/android/').status_code, 404)
        self.assertEqual(self.client.get('/applications-natives/ios/').status_code, 404)
        home = self.client.get('/')
        self.assertContains(home, 'data-install-hub')
        self.assertContains(home, 'data-legal="terms"')
        self.assertNotContains(home, '/installer/')


class AdminConsoleTests(TestCase):
    def test_console_requires_staff_and_hides_metrics_without_permissions(self):
        from django.contrib.auth import get_user_model
        user = get_user_model().objects.create_user('limited', password='test-only', is_staff=True)
        self.assertEqual(self.client.get('/admin/').status_code, 302)
        self.client.force_login(user)
        response = self.client.get('/admin/')
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'Applications publiées')
        self.assertNotContains(response, 'Paiements confirmés')

    @override_settings(DEBUG=False)
    def test_demo_admin_command_refuses_production(self):
        from django.core.management import call_command, CommandError
        with self.assertRaises(CommandError):
            call_command('create_local_admin')

    def test_submission_steps_reflect_real_state(self):
        from django.contrib.auth import get_user_model
        from hub.models import Application, Category
        from django.urls import reverse
        user=get_user_model().objects.create_user('creator')
        cat=Category.objects.create(name='Test',slug='test')
        app=Application.objects.create(name='Test',slug='test',category=cat,submitted_by=user)
        self.client.force_login(user)
        response=self.client.get(reverse('hub:submission',args=[app.public_id]))
        self.assertContains(response, 'Étape terminée :', count=1)
        app.is_admin_added=True
        app.status='published'
        app.save()
        response=self.client.get(reverse('hub:submission',args=[app.public_id]))
        self.assertContains(response, 'Étape terminée :', count=3)


class SubmissionWorkflowTests(TestCase):
    def setUp(self):
        from django.contrib.auth import get_user_model
        from hub.models import Application, Category, Payment
        self.admin = get_user_model().objects.create_superuser('moderator', password='test')
        category = Category.objects.create(name='Tools', slug='tools')
        self.app = Application.objects.create(name='Test app', description='Une application de test.', slug='workflow-test', category=category, website_url='https://example.com', submitted_by=self.admin)
        self.payment = Payment.objects.create(application=self.app, user=self.admin, amount=2000, reference='HUB-WORKFLOW')
        self.url = f'/admin/hub/application/suivi/{self.app.pk}/'
        self.client.force_login(self.admin)

    def test_list_detail_and_pending_filter(self):
        self.assertContains(self.client.get('/admin/hub/application/suivi/?stage=pending'), 'Test app')
        self.assertContains(self.client.get(self.url), 'Vérifier et valider le paiement')
        self.assertNotContains(self.client.get('/admin/hub/application/suivi/?stage=review'), 'Test app')

    def test_unpaid_cannot_publish(self):
        self.client.post(self.url, {'action':'publish'})
        self.app.refresh_from_db()
        self.assertEqual(self.app.status, 'draft')

    def test_paid_publish_and_required_correction_reason_are_logged(self):
        from django.utils import timezone
        from django.contrib.admin.models import LogEntry
        self.payment.status='success'
        self.payment.verified_at=timezone.now()
        self.payment.save()
        self.client.post(self.url, {'action':'publish'})
        self.app.refresh_from_db()
        self.assertEqual(self.app.status, 'published')
        self.client.post(self.url, {'action':'corrections', 'note':''})
        self.app.refresh_from_db()
        self.assertEqual(self.app.status, 'published')
        self.client.post(self.url, {'action':'corrections', 'note':'Corriger le logo.'})
        self.app.refresh_from_db()
        self.assertEqual(self.app.status, 'rejected')
        self.assertEqual(self.app.moderation_note, 'Corriger le logo.')
        self.assertEqual(LogEntry.objects.filter(object_id=str(self.app.pk)).count(), 2)

    @patch('hub.admin_workflow.verify_payment', return_value='Paiement encore en cours.')
    def test_verify_is_post_only_and_scoped(self, verify):
        from hub.models import Application, Payment
        self.client.get(self.url, {'action':'verify', 'payment_id':self.payment.pk})
        verify.assert_not_called()
        response=self.client.post(self.url, {'action':'verify','payment_id':self.payment.pk})
        self.assertEqual(response.status_code,302)
        verify.assert_called_once()
        other=Application.objects.create(name='Other',slug='other',category=self.app.category)
        foreign=Payment.objects.create(application=other,user=self.admin,amount=2000,reference='HUB-OTHER')
        self.assertEqual(self.client.post(self.url, {'action':'verify','payment_id':foreign.pk}).status_code,404)

    def test_read_only_staff_cannot_mutate(self):
        from django.contrib.auth import get_user_model
        from django.contrib.auth.models import Permission
        user=get_user_model().objects.create_user('reader', is_staff=True)
        user.user_permissions.add(Permission.objects.get(codename='view_application'))
        self.client.force_login(user)
        self.assertEqual(self.client.get(self.url).status_code,200)
        self.assertEqual(self.client.post(self.url, {'action':'publish'}).status_code,403)
        self.assertEqual(self.client.post(self.url, {'action':'verify','payment_id':self.payment.pk}).status_code,403)

    def test_csrf_required(self):
        from django.test import Client
        client=Client(enforce_csrf_checks=True)
        client.force_login(self.admin)
        self.assertEqual(client.post(self.url, {'action':'publish'}).status_code,403)

    @patch('hub.payments.services.singpay_service')
    def test_verified_payment_then_publication(self, provider):
        provider.is_configured = True
        provider.find_payment_by_reference.return_value = (True, {
            'order_id': self.payment.reference, 'amount': 2000,
            'status': 'success', 'transaction_id': 'provider-test-unique', 'raw': {'currency': 'XAF'}})
        self.client.post(self.url, {'action': 'verify', 'payment_id': self.payment.pk})
        self.app.refresh_from_db()
        self.assertEqual(self.app.status, 'draft')
        self.assertTrue(self.app.paid)
        self.client.post(self.url, {'action': 'publish'})
        self.app.refresh_from_db()
        self.assertEqual(self.app.status, 'published')

    @patch('hub.payments.services.singpay_service')
    def test_wrong_amount_still_blocks_publication(self, provider):
        provider.is_configured = True
        provider.find_payment_by_reference.return_value = (True, {
            'order_id': self.payment.reference, 'amount': 100,
            'status': 'success', 'transaction_id': 'provider-wrong-amount', 'raw': {}})
        self.client.post(self.url, {'action': 'verify', 'payment_id': self.payment.pk})
        self.client.post(self.url, {'action': 'publish'})
        self.app.refresh_from_db()
        self.assertFalse(self.app.paid)
        self.assertEqual(self.app.status, 'draft')


class ManualPaymentTests(SubmissionWorkflowTests):
    def manual(self, **changes):
        data = {'action':'manual', 'receipt':'RECU-001', 'amount':'2000', 'note':'Reçu contrôlé dans le relevé opérateur.', 'confirmed':'on'}
        data.update(changes)
        return self.client.post(self.url, data)

    def test_pending_payment_can_be_manually_confirmed_and_published(self):
        from django.contrib.admin.models import LogEntry
        self.manual()
        self.payment.refresh_from_db()
        self.app.refresh_from_db()
        self.assertEqual(self.payment.status, 'success')
        self.assertEqual(self.payment.manual_confirmed_by, self.admin)
        self.assertEqual(self.payment.manual_reference, 'RECU-001')
        self.assertEqual(self.app.status, 'draft')
        self.assertEqual(self.app.payments.count(), 1)
        self.assertGreaterEqual(LogEntry.objects.count(), 2)
        self.client.post(self.url, {'action':'publish'})
        self.app.refresh_from_db()
        self.assertEqual(self.app.status, 'published')
        self.manual()
        self.assertEqual(self.app.payments.count(), 1)

    def test_manual_without_online_attempt(self):
        self.payment.delete()
        self.assertEqual(self.manual().status_code, 302)
        self.app.refresh_from_db()
        self.assertTrue(self.app.paid)
        self.assertEqual(self.app.payments.count(), 1)

    def test_wrong_amount_and_missing_confirmation_keep_pending(self):
        response=self.manual(amount='100')
        self.assertContains(response, 'Le montant reçu doit correspondre')
        response=self.manual(confirmed='')
        self.assertEqual(response.status_code, 200)
        self.payment.refresh_from_db()
        self.assertEqual(self.payment.status, 'pending')

    def test_duplicate_receipt_for_other_app_rejected(self):
        from hub.models import Application
        from hub.payments.manual import confirm_manual_payment
        from django.core.exceptions import ValidationError
        self.manual()
        other=Application.objects.create(name='Autre', description='Test', slug='autre-manual', category=self.app.category)
        with self.assertRaises(ValidationError):
            confirm_manual_payment(other.pk, self.admin, 'recu-001', 2000, 'Relevé vérifié', True)
        self.assertFalse(other.paid)

    def test_manual_forbidden_to_reader(self):
        from django.contrib.auth import get_user_model
        from django.contrib.auth.models import Permission
        reader=get_user_model().objects.create_user('manual-reader',is_staff=True)
        reader.user_permissions.add(Permission.objects.get(codename='view_application'))
        self.client.force_login(reader)
        self.assertEqual(self.manual().status_code,403)
        self.payment.refresh_from_db()
        self.assertEqual(self.payment.status,'pending')

    def test_reference_search_and_pagination_preserve_filters(self):
        self.manual()
        response=self.client.get('/admin/hub/application/suivi/',{'q':'RECU-001','sort':'oldest','size':'24'})
        self.assertContains(response,'Test app')
        self.assertEqual(response.context['page'].paginator.per_page,24)
        self.assertContains(response,'Filtres et affichage')

    def test_lists_page_a_hundred_and_bulk_actions_stay_inside_the_filter(self):
        from hub.models import Application
        kept = Application.objects.create(name='Keep me', description='Stable.', slug='keep-me', category=self.app.category, status='published', is_admin_added=True)
        free = Application.objects.create(name='Ready', description='Prête.', slug='ready-app', category=self.app.category, status='review', is_admin_added=True)
        listing = self.client.get('/admin/hub/application/?per_page=100')
        self.assertEqual(listing.context['cl'].list_per_page, 100)
        self.assertContains(listing, 'id="action-toggle"')
        self.assertContains(listing, 'select-across')
        self.assertEqual(self.client.get('/admin/hub/application/?per_page=9999').context['cl'].list_per_page, 50)
        self.client.post('/admin/hub/application/suivi/?stage=draft', {'action': 'archive', 'select_across': '1'})
        self.app.refresh_from_db(); kept.refresh_from_db(); free.refresh_from_db()
        self.assertEqual(self.app.status, 'archived')
        self.assertEqual(kept.status, 'published')
        self.assertEqual(free.status, 'review')
        self.app.status = 'draft'
        self.app.save(update_fields=['status'])
        self.client.post('/admin/hub/application/suivi/?stage=draft', {'action': 'archive', 'selected': [str(kept.pk)]})
        kept.refresh_from_db(); self.app.refresh_from_db()
        self.assertEqual(kept.status, 'published')
        self.assertEqual(self.app.status, 'draft')
        self.client.post('/admin/hub/application/suivi/', {'action': 'publish', 'selected': [str(self.app.pk), str(free.pk)]})
        self.app.refresh_from_db(); free.refresh_from_db()
        self.assertEqual(self.app.status, 'draft')
        self.assertEqual(free.status, 'published')
        from django.contrib.auth import get_user_model
        from django.contrib.auth.models import Permission
        reader = get_user_model().objects.create_user('list-reader', is_staff=True)
        reader.user_permissions.add(Permission.objects.get(codename='view_application'))
        self.client.force_login(reader)
        self.assertEqual(self.client.post('/admin/hub/application/suivi/', {'action': 'archive', 'selected': [str(free.pk)]}).status_code, 403)


class HeroStatisticsTests(TestCase):
    def test_visitors_are_persistent_and_refreshes_do_not_increase_count(self):
        from hub.models import HubVisitor
        from django.test import Client
        first=self.client.get('/')
        self.assertEqual(first.context['visitor_count'],1)
        self.assertTrue(first.cookies['hub_visitor']['httponly'])
        self.assertEqual(self.client.get('/?tri=rating').context['visitor_count'],1)
        self.assertEqual(Client().get('/').context['visitor_count'],2)
        self.assertEqual(HubVisitor.objects.count(),2)

    def test_only_published_apps_with_links_are_available(self):
        from hub.models import Application, Category
        category=Category.objects.create(name='Stats',slug='stats')
        for slug,status,url in [('live','published','https://example.com'),('future','published',''),('draft','draft','https://example.com')]:
            Application.objects.create(name=slug,slug=slug,category=category,status=status,website_url=url,is_admin_added=True)
        response=self.client.get('/')
        self.assertEqual(response.context['available_count'],1)
        self.assertContains(response,'Visiteur')

    def test_staff_and_known_crawlers_are_not_counted(self):
        from django.contrib.auth import get_user_model
        from hub.models import HubVisitor
        user=get_user_model().objects.create_user('stats-admin',is_staff=True)
        self.client.force_login(user)
        self.client.get('/')
        self.client.logout()
        self.client.get('/',HTTP_USER_AGENT='Googlebot')
        self.assertEqual(HubVisitor.objects.count(),0)
