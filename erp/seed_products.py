"""Insert 15 sample rows into the Product table.

Run from the folder containing manage.py:
    python seed_products.py
"""
import os
from decimal import Decimal

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "erp.settings")
django.setup()

from core.models import Product  # noqa: E402

PRODUCTS = [
    ("Laptop", "14-inch business laptop, 16GB RAM", "899.99"),
    ("Wireless Mouse", "Ergonomic 2.4GHz wireless mouse", "19.99"),
    ("Mechanical Keyboard", "RGB backlit mechanical keyboard", "79.50"),
    ("27\" Monitor", "27-inch 4K IPS display", "329.00"),
    ("USB-C Hub", "7-in-1 USB-C multiport adapter", "34.90"),
    ("Webcam", "1080p HD webcam with microphone", "49.99"),
    ("Headphones", "Noise-cancelling over-ear headphones", "149.00"),
    ("External SSD 1TB", "Portable NVMe SSD, 1050MB/s", "109.99"),
    ("Office Chair", "Adjustable ergonomic office chair", "189.00"),
    ("Standing Desk", "Electric height-adjustable desk", "429.00"),
    ("Desk Lamp", "LED desk lamp with dimmer", "24.75"),
    ("Printer", "Wireless laser printer", "159.99"),
    ("Router", "Dual-band Wi-Fi 6 router", "89.00"),
    ("Power Bank", "20000mAh fast-charging power bank", "39.99"),
    ("Notebook Pack", "Pack of 5 ruled notebooks", "12.50"),
]

created = Product.objects.bulk_create(
    [Product(name=n, description=d, price=Decimal(p)) for n, d, p in PRODUCTS]
)
print(f"Inserted {len(created)} products. Total now: {Product.objects.count()}")
