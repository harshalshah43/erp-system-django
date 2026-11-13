from django.contrib import admin
from .models import Product, StockDocument

# Register your models here.
admin.site.register(Product)
admin.site.register(StockDocument)
