from io import BytesIO

from django import forms
from django.core.files.base import ContentFile
from PIL import Image, ImageOps

from .models import Product


class ProductPhotoInput(forms.ClearableFileInput):
    template_name = 'products/photo_input.html'


class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = ['label', 'description', 'price', 'photo']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 5}),
            'price': forms.NumberInput(attrs={'min': '0', 'step': '0.01'}),
            'photo': ProductPhotoInput(attrs={'accept': 'image/jpeg,image/png,image/webp'}),
        }
        help_texts = {
            'photo': 'Optional. JPEG, PNG or WebP, up to 5 MB and 4096 × 4096 pixels.',
        }

    def clean_photo(self):
        photo = self.cleaned_data.get('photo')
        if not photo or not hasattr(photo, 'image'):
            return photo
        if photo.size > 5 * 1024 * 1024:
            raise forms.ValidationError('The photo must be no larger than 5 MB.')
        image_format = photo.image.format
        extensions = {'JPEG': 'jpg', 'PNG': 'png', 'WEBP': 'webp'}
        if image_format not in extensions:
            raise forms.ValidationError('Please upload a JPEG, PNG or WebP image.')
        if max(photo.image.size) > 4096:
            raise forms.ValidationError('The photo must be no larger than 4096 × 4096 pixels.')
        # Re-encode images so original metadata and appended content are not stored.
        try:
            photo.seek(0)
            with Image.open(photo) as image:
                image = ImageOps.exif_transpose(image)
                image.load()
                output = BytesIO()
                image.save(output, format=image_format)
        except (OSError, ValueError):
            raise forms.ValidationError('The photo could not be read. Please choose another image.')
        return ContentFile(output.getvalue(), name=f'photo.{extensions[image_format]}')
