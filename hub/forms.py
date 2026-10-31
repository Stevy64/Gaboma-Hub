from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from .models import Application, Review
from .images import ApplicationImagesMixin

class SignupForm(UserCreationForm):
    email = forms.EmailField(label="Adresse e-mail")
    accept_terms = forms.BooleanField(label="J'accepte les conditions générales d'utilisation.")
    class Meta:
        model = User
        fields = ["username", "email", "password1", "password2"]
    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("Cette adresse est déjà utilisée. Vous pouvez réinitialiser votre mot de passe.")
        return email

class ApplicationForm(ApplicationImagesMixin, forms.ModelForm):
    logo = ApplicationImagesMixin.logo
    banner = ApplicationImagesMixin.banner
    confirmation = forms.BooleanField(label="Je suis autorisé à présenter cette application, la fiche est exacte, et j'accepte les conditions d'utilisation.")
    class Meta:
        model = Application
        fields = ["name", "category", "creator_name", "creator_city", "description", "about", "website_url", "logo", "banner", "color"]
        widgets = {"description": forms.Textarea(attrs={"rows": 3}),
                   "website_url": forms.URLInput(attrs={"placeholder": "https://", "inputmode": "url", "autocapitalize": "off", "spellcheck": "false"})}
    def clean_website_url(self):
        url = self.cleaned_data.get("website_url", "").strip()
        if not url: raise forms.ValidationError("L'adresse de l'application est obligatoire.")
        return url
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["logo"].required = not bool(self.instance.logo)
        self.fields["banner"].required = not bool(self.instance.banner)
        self.fields["creator_name"].required = True
        self.fields["about"].widget = forms.Textarea(attrs={"rows": 5, "placeholder": "À quoi sert votre app ? À qui s'adresse-t-elle ?"})

class StarRating(forms.RadioSelect):
    option_template_name = "hub/widgets/star_option.html"

class ReviewForm(forms.ModelForm):
    rating = forms.TypedChoiceField(label="Votre note", coerce=int, choices=[(i, f"{i} sur 5") for i in range(1, 6)], widget=StarRating)
    class Meta:
        model = Review
        fields = ["rating", "comment"]
        widgets = {"comment": forms.Textarea(attrs={"rows": 4, "placeholder": "Qu'avez-vous aimé ? Que pourrait-on améliorer ?", "maxlength": 2000})}
