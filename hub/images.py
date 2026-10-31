"""Images publiques : lecture réelle, limite de taille et réencodage sans métadonnées."""
import uuid
import warnings
from io import BytesIO
from PIL import Image, ImageOps, UnidentifiedImageError
from django import forms
from django.core.files.uploadedfile import SimpleUploadedFile

def application_image_path(instance, filename):
    return f"applications/{instance.public_id}/{uuid.uuid4().hex}.webp"

def editorial_image_path(instance, filename):
    return f"editorial/{uuid.uuid4().hex}.webp"

def native_package_path(instance, filename):
    suffix = filename.rsplit(".", 1)[-1].lower() if "." in filename else "bin"
    if suffix not in {"apk", "ipa"}:
        suffix = "bin"
    return f"native/{uuid.uuid4().hex}.{suffix}"

class PublicImageField(forms.ImageField):
    def to_python(self, data):
        if not data or not hasattr(data, "read"):
            return super().to_python(data)
        if data.size > 5 * 1024 * 1024:
            raise forms.ValidationError("L'image doit peser au maximum 5 Mo.")
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("error", Image.DecompressionBombWarning)
                data.seek(0)
                with Image.open(data) as source:
                    if source.format not in {"JPEG", "PNG", "WEBP"}:
                        raise forms.ValidationError("Utilisez une image JPG, PNG ou WebP.")
                    if source.width * source.height > 20_000_000:
                        raise forms.ValidationError("Image trop grande : maximum 20 millions de pixels.")
                    source.load()
                    image = ImageOps.exif_transpose(source).convert("RGBA")
                    image.thumbnail((1920, 1920))
                    output = BytesIO()
                    image.save(output, format="WEBP", quality=88)
            return super().to_python(SimpleUploadedFile(f"{uuid.uuid4().hex}.webp", output.getvalue(), content_type="image/webp"))
        except (UnidentifiedImageError, OSError, ValueError, Image.DecompressionBombError, Image.DecompressionBombWarning):
            raise forms.ValidationError("Ce fichier n'est pas une image valide ou il est trop volumineux.")

class ApplicationImagesMixin:
    logo = PublicImageField(label="Logo", required=False, help_text="JPG, PNG ou WebP · 5 Mo maximum. Format carré conseillé : 512 × 512 px.", widget=forms.FileInput(attrs={"accept": "image/png,image/jpeg,image/webp"}))
    banner = PublicImageField(label="Bannière", required=False, help_text="JPG, PNG ou WebP · 5 Mo maximum. Format paysage conseillé : 1600 × 900 px.", widget=forms.FileInput(attrs={"accept": "image/png,image/jpeg,image/webp"}))
