from django import forms
from .models import Product


class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        # Listed explicitly so new model fields (like stock) never appear here by accident.
        fields = ["name", "description", "price"]
