from django import forms
from .models import categories
import re

class CategoryForm(forms.ModelForm):
    class Meta:
        model = categories
        fields = ['name', 'description', 'image']

    def __init__(self, *args, **kwargs):
        self.instance = kwargs.get('instance', None)
        super(CategoryForm, self).__init__(*args, **kwargs)

    def clean_name(self):
        name = self.cleaned_data.get('name')
        if not name:
            raise forms.ValidationError("Category name is required.")
        if len(name.strip()) < 3:
            raise forms.ValidationError("Name must be at least 3 characters long.")
        if not re.match(r'^[A-Za-z\s]+$', name):
            raise forms.ValidationError("Name must contain only letters (no numbers or symbols).")
        qs = categories.objects.filter(name__iexact=name)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError("Category with this name already exists.")
        return name

    def clean_description(self):
        description = self.cleaned_data.get('description')
        if description:  # Only validate if description is provided
            if not re.match(r'^[A-Za-z\s]+$', description):
                raise forms.ValidationError("Description must contain only letters (no numbers or symbols).")
        return description

    def clean_image(self):
        image = self.cleaned_data.get('image')
        if image:
            if hasattr(image, 'content_type'):
                if image.content_type not in ['image/jpeg', 'image/png']:
                    raise forms.ValidationError("Only JPEG and PNG images are allowed.")
                if image.size > 2 * 1024 * 1024:  # 2MB limit
                    raise forms.ValidationError("Image size should not exceed 2MB.")
        return image