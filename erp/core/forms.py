from django import forms
from .models import Product

class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = "__all__"

from .models import StockDocument

class StockTakeForm(forms.Form):
    """One 'counted quantity' field per product, prefilled with current stock."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.products = list(Product.objects.order_by("name"))
        for p in self.products:
            self.fields[f"p{p.pk}"] = forms.IntegerField(
                label=p.name, min_value=0, initial=p.stock_quantity
            )
