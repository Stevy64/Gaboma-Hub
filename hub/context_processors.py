from .models import CatalogueFilter, HubAppearance

def hub_context(request):
    sections = {
        "login": ("Votre compte", "Connexion"),
        "signup": ("Votre compte", "Inscription"),
        "password_reset": ("Votre compte", "Récupérer l'accès"),
        "password_reset_done": ("Votre compte", "Récupérer l'accès"),
        "password_reset_confirm": ("Votre compte", "Nouveau mot de passe"),
        "password_reset_complete": ("Votre compte", "Accès rétabli"),
        "password_change": ("Votre compte", "Mot de passe"),
        "password_change_done": ("Votre compte", "Mot de passe"),
        "dashboard": ("Espace créateur", "Vue d'ensemble"),
        "submit": ("Espace créateur", "Présenter une application"),
        "edit": ("Espace créateur", "Modifier la fiche"),
        "submission": ("Espace créateur", "Suivi de publication"),
        "detail": ("Le répertoire", "Application"),
        "review": ("La communauté", "Votre avis"),
        "payment-return": ("Espace créateur", "Suivi du paiement"),
    }
    name = getattr(request.resolver_match, "url_name", "")
    appearance = getattr(request, "hub_appearance", None) or HubAppearance.current()
    filters = CatalogueFilter.objects.filter(is_active=True).select_related("category")
    return {"appearance": appearance, "submission_fee": appearance.submission_fee, "page_section": sections.get(name), "directory_filters": filters}
