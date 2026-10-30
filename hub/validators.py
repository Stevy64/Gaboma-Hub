from urllib.parse import urlsplit
from django.core.exceptions import ValidationError
from django.core.validators import URLValidator

def validate_application_url(value):
    URLValidator(schemes=["http", "https"])(value)
    parsed = urlsplit(value)
    if parsed.username or parsed.password:
        raise ValidationError("L'adresse ne doit pas contenir d'identifiant ni de mot de passe.")
