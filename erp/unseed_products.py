"""Remove the sample rows inserted by seed_products.py.

Run from the folder containing manage.py:
    python unseed_products.py
"""
import os

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "erp.settings")
django.setup()

from core.models import Product, StockDocument  # noqa: E402

NAMES = [
    "Laptop", "Wireless Mouse", "Mechanical Keyboard", '27" Monitor',
    "USB-C Hub", "Webcam", "Headphones", "External SSD 1TB", "Office Chair",
    "Standing Desk", "Desk Lamp", "Printer", "Router", "Power Bank",
    "Notebook Pack",
]

products = Product.objects.filter(name__in=NAMES)
# Documents are PROTECTed against product deletion, so remove them first.
docs_deleted, _ = StockDocument.objects.filter(product__in=products).delete()
products_deleted, _ = products.delete()
print(f"Deleted {products_deleted} products and {docs_deleted} stock documents. "
      f"Total now: {Product.objects.count()}")
