from django.conf import settings
from django.db import models
from django.db.models import Q


class Product(models.Model):
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    # Running total of this product's stock moves. Only core.services.post_document
    # changes it, which is why it is not editable in forms or the admin.
    stock_quantity = models.IntegerField(default=0, editable=False)
    # Products with stock history are archived instead of deleted.
    is_active = models.BooleanField(default=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=Q(stock_quantity__gte=0), name="product_stock_not_negative"
            ),
        ]

    def __str__(self):
        return self.name


class StockDocument(models.Model):
    """Header for one posted stock change: a transaction, a stock take, etc.

    Documents are never edited or deleted. A mistake is corrected by posting a
    reversal (core.services.reverse_document).
    """

    class Kind(models.TextChoices):
        TRANSACTION = "TXN", "Stock transaction"
        STOCK_TAKE = "TAKE", "Stock take"
        OPENING = "OPEN", "Opening balance"
        REVERSAL = "REV", "Reversal"

    kind = models.CharField(max_length=4, choices=Kind.choices)
    note = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        on_delete=models.SET_NULL, related_name="+",
    )
    # Set on a reversal. One-to-one, so a document can only be reversed once.
    reverses = models.OneToOneField(
        "self", null=True, blank=True,
        on_delete=models.PROTECT, related_name="reversed_by",
    )

    class Meta:
        ordering = ["-created_at", "-pk"]

    def __str__(self):
        return f"{self.get_kind_display()} #{self.pk}"


class StockMove(models.Model):
    """One line of a document: a signed change to one product's stock.

    Positive is incoming, negative is outgoing. A product's stock_quantity
    always equals the sum of its moves (see `manage.py check_stock`).
    """

    document = models.ForeignKey(StockDocument, on_delete=models.PROTECT, related_name="lines")
    product = models.ForeignKey(Product, on_delete=models.PROTECT, related_name="moves")
    quantity = models.IntegerField()

    class Meta:
        constraints = [
            models.CheckConstraint(condition=~Q(quantity=0), name="stockmove_quantity_not_zero"),
        ]

    def __str__(self):
        return f"{self.quantity:+d} x {self.product}"
