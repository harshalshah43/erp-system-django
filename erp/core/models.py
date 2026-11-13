from django.db import models, transaction
from django.db.models import F


class Product(models.Model):
    name = models.CharField(max_length=200)
    description = models.TextField(blank = True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    stock_quantity = models.IntegerField(default=0)

    def __str__(self):
        return self.name


class StockDocument(models.Model):
    """An incoming (receipt) or outgoing (issue) document for a product."""
    INCOMING = "IN"
    OUTGOING = "OUT"
    TYPE_CHOICES = [(INCOMING, "Incoming"), (OUTGOING, "Outgoing")]

    product = models.ForeignKey(Product, on_delete=models.PROTECT, related_name="documents")
    doc_type = models.CharField(max_length=3, choices=TYPE_CHOICES)
    quantity = models.PositiveIntegerField()
    note = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        # Stock is only adjusted when the document is first created.
        if self.pk:
            return super().save(*args, **kwargs)
        with transaction.atomic():
            product = Product.objects.select_for_update().get(pk=self.product_id)
            if self.doc_type == self.OUTGOING:
                if product.stock_quantity < self.quantity:
                    raise ValueError("Not enough stock for this outgoing document.")
                product.stock_quantity = F("stock_quantity") - self.quantity
            else:
                product.stock_quantity = F("stock_quantity") + self.quantity
            product.save(update_fields=["stock_quantity"])
            super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.get_doc_type_display()} {self.quantity} x {self.product}"
