"""Insert 15 sample rows into the Product table.

Run from the folder containing manage.py:
    python seed_products.py
"""
import os
from decimal import Decimal

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "erp.settings")
django.setup()

from django.db import transaction  # noqa: E402

from core.models import Product, StockDocument  # noqa: E402
from core.services import post_document  # noqa: E402

PRODUCTS = [
    ("Laptop", "14-inch business laptop, 16GB RAM", "899.99", 25),
    ("Wireless Mouse", "Ergonomic 2.4GHz wireless mouse", "19.99", 150),
    ("Mechanical Keyboard", "RGB backlit mechanical keyboard", "79.50", 60),
    ("27\" Monitor", "27-inch 4K IPS display", "329.00", 40),
    ("USB-C Hub", "7-in-1 USB-C multiport adapter", "34.90", 80),
    ("Webcam", "1080p HD webcam with microphone", "49.99", 45),
    ("Headphones", "Noise-cancelling over-ear headphones", "149.00", 70),
    ("External SSD 1TB", "Portable NVMe SSD, 1050MB/s", "109.99", 55),
    ("Office Chair", "Adjustable ergonomic office chair", "189.00", 20),
    ("Standing Desk", "Electric height-adjustable desk", "429.00", 12),
    ("Desk Lamp", "LED desk lamp with dimmer", "24.75", 90),
    ("Printer", "Wireless laser printer", "159.99", 18),
    ("Router", "Dual-band Wi-Fi 6 router", "89.00", 35),
    ("Power Bank", "20000mAh fast-charging power bank", "39.99", 65),
    ("Notebook Pack", "Pack of 5 ruled notebooks", "12.50", 200),
]

with transaction.atomic():
    created = [
        Product.objects.create(name=n, description=d, price=Decimal(p)) for n, d, p, _ in PRODUCTS
    ]
    # Stock goes in through an opening-balance document, like any other stock change.
    post_document(
        StockDocument.Kind.OPENING,
        [(product.pk, qty) for product, (*_, qty) in zip(created, PRODUCTS) if qty],
        note="Seed data",
    )
print(f"Inserted {len(created)} products. Total now: {Product.objects.count()}")
