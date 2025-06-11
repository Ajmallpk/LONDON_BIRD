
from django import forms
from django.core.validators import MinValueValidator,RegexValidator
from django.db.models import Q
from decimal import Decimal
from .models import product, Variant,Size
from django.core.exceptions import ValidationError
import re

class ProductForm(forms.ModelForm):
    class Meta:
        model = product
        fields = ['name','price', 'description', 'category', 'is_active','image_1']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter product name'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 5, 'placeholder': 'Enter product description'}),
            'category': forms.Select(attrs={'class': 'form-control'}),
            'price': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'placeholder': 'Enter price'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'image_1': forms.ClearableFileInput(attrs={'class': 'form-control'}),
          
        }
        labels = {
            
            'name': 'Product Name',
            'price': 'Price ($)',
            'description': 'Description',
            'category': 'Category',
            'is_active': 'Active',
            'image_1': 'Main Image',

        }
        help_texts = {
            'name': 'Enter the name of the product (max 200 characters).',
            'price': 'Enter the price for this variant (e.g., 29.99).',
            'description': 'Provide a detailed description of the product.',
            'category': 'Select the category for this product.',
            'is_active': 'Check to make the product active.',
            'image_1': 'Upload the main image for this variant.',
     
            
        }
    def clean_name(self):
        name = self.cleaned_data['name']

        if not re.match(r'^[A-Za-z\s]+$', name):
            raise ValidationError('Product name must contain only letters and spaces. Numbers or special characters are not allowed.')
        return name

    def __init__(self, *args, **kwargs):
        super(ProductForm, self).__init__(*args, **kwargs)
        from .models import categories  
        self.fields['category'].required = False
        self.fields['category'].queryset = categories.objects.filter(is_listed=True)

class VariantForm(forms.ModelForm):
    class Meta:
        model = Variant
        fields = [
            'product','color',
            'image_main', 'image_1', 'image_2', 'image_3'
        ]
        widgets = {
            'product': forms.Select(attrs={'class': 'form-control'}),
            'color': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter color'}),
            'image_main': forms.ClearableFileInput(attrs={'class': 'form-control'}),
            'image_1': forms.ClearableFileInput(attrs={'class': 'form-control'}),
            'image_2': forms.ClearableFileInput(attrs={'class': 'form-control'}),
            'image_3': forms.ClearableFileInput(attrs={'class': 'form-control'}),
            
        }
        labels = {
            'product': 'Product',
            'color': 'Color',
            'image_main': 'Main Image',
            'image_1': 'Additional Image 1',
            'image_2': 'Additional Image 2',
            'image_3': 'Additional Image 3',
            
        }
        help_texts = {
            'color': 'Specify the color of this variant (e.g., Red).',
            'image_main': 'Upload the main image for this variant.',
            'image_1': 'Optional: Upload an additional image.',
            'image_2': 'Optional: Upload an additional image.',
            'image_3': 'Optional: Upload an additional image.',
            
        }

    def __init__(self, *args, **kwargs):
        selected_product = kwargs.pop('product', None)

        super(VariantForm, self).__init__(*args, **kwargs)
        self.fields['image_1'].required = False
        self.fields['image_2'].required = False
        self.fields['image_3'].required = False
        if selected_product:
            self.fields['product'].queryset = product.objects.filter(id=selected_product.id)
            self.fields['product'].initial = selected_product
            self.fields['product'].widget = forms.HiddenInput()
        

    
    
    
    
    

class SizeForm(forms.ModelForm):
    SIZE_CHOICES = [
        ('S', 'S'),
        ('M', 'M'),
        ('L', 'L'),
        ('XL', 'XL'),
        ('XXL', 'XXL'),
    ]

    size = forms.ChoiceField(
        choices=SIZE_CHOICES,
        error_messages={
            'required': 'Size is required',
            'invalid_choice': 'Please select a valid size: S, M, L, XL, XXL'
        }
    )

    stock = forms.IntegerField(
        min_value=0,
        error_messages={
            'required': 'Stock is required',
            'min_value': 'Stock cannot be negative'
        }
    )

    class Meta:
        model = Size
        fields = ['size', 'stock', 'variant']

    def __init__(self, *args, **kwargs):
        self.selected_variant = kwargs.pop('variant', None)
        super().__init__(*args, **kwargs)
        if self.selected_variant:
            self.fields['variant'].queryset = Variant.objects.filter(id=self.selected_variant.id)
            self.fields['variant'].initial = self.selected_variant
            self.fields['variant'].widget = forms.HiddenInput()
        self.fields['variant'].required = False


    def clean(self):
        cleaned_data = super().clean()
        size = cleaned_data.get('size')
        variant = cleaned_data.get('variant') or self.selected_variant

        if size and variant:
            if Size.objects.filter(variant=variant, size=size).exists():
                self.add_error('size', 'This size already exists for the variant.')
        
        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)
        if self.selected_variant:
            instance.variant = self.selected_variant
        else:
            raise ValueError("Cannot save Size without a variant.")
        if commit:
            instance.save()
        return instance