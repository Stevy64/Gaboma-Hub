from django.urls import path
from . import views
app_name = "hub"
urlpatterns = [
    path("", views.home, name="home"),
    path("repertoire/", views.catalogue, name="catalogue"),
    path("applications/<slug:slug>/", views.detail, name="detail"),
    path("applications/<slug:slug>/avis/", views.save_review, name="review"),
    path("applications/<slug:slug>/avis/supprimer/", views.delete_review, name="delete-review"),
    path("favoris/<uuid:public_id>/", views.toggle_favorite, name="favorite"),
    path("inscription/", views.signup, name="signup"),
    path("mon-espace/", views.dashboard, name="dashboard"),
    path("conditions-utilisation/", views.terms, name="terms"),
    path("faq/", views.faq, name="faq"),
    path("soumettre/", views.submit_application, name="submit"),
    path("mes-applications/<uuid:public_id>/", views.submission, name="submission"),
    path("mes-applications/<uuid:public_id>/confirmer/", views.confirm_submission, name="confirm"),
    path("mes-applications/<uuid:public_id>/modifier/", views.edit_submission, name="edit"),
    path("mes-applications/<uuid:public_id>/payer/", views.checkout, name="checkout"),
    path("paiements/<uuid:public_id>/retour/", views.payment_return, name="payment-return"),
    path("paiements/<uuid:public_id>/verifier/", views.check_payment, name="check-payment"),
    path("paiements/singpay/callback/", views.singpay_callback, name="singpay-callback"),
]
