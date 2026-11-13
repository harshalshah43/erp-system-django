"""Remove the sample rows inserted by seed_products.py.

Run from the folder containing manage.py:
    python unseed_products.py
"""
import os

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "erp.settings")
django.setup()

from django.db import transaction  # noqa: E402

from core.models import Product, StockDocument, StockMove  # noqa: E402

NAMES = [
    "Laptop", "Wireless Mouse", "Mechanical Keyboard", '27" Monitor',
    "USB-C Hub", "Webcam", "Headphones", "External SSD 1TB", "Office Chair",
    "Standing Desk", "Desk Lamp", "Printer", "Router", "Power Bank",
    "Notebook Pack",
]

# Stock history is normally permanent (PROTECT), so this dev-only script
# removes those products' moves first, then any documents left with no lines.
with transaction.atomic():
    products = Product.objects.filter(name__in=NAMES)
    moves_deleted, _ = StockMove.objects.filter(product__in=products).delete()
    empty = StockDocument.objects.filter(lines__isnull=True)
    empty.update(reverses=None)  # a reversal PROTECTs the document it reverses
    docs_deleted, _ = empty.delete()
    products_deleted, _ = products.delete()
print(f"Deleted {products_deleted} products, {moves_deleted} stock moves and "
      f"{docs_deleted} empty stock documents. Total now: {Product.objects.count()}")
