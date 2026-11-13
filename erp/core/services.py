"""Stock posting. These functions are the only code that changes Product.stock_quantity."""
from collections import defaultdict

from django.db import transaction
from django.db.models import F

from .models import Product, StockDocument, StockMove


class StockError(Exception):
    """A document could not be posted. The message is safe to show to users."""


@transaction.atomic
def post_document(kind, lines, note="", user=None, reverses=None):
    """Post a document. `lines` is a list of (product_id, signed_quantity).

    All lines are applied or none are. Quantities are netted per product
    first, so receiving 5 and issuing 3 of an item in the same document only
    needs the net +2 to be possible.
    """
    lines = [(int(pid), int(qty)) for pid, qty in lines]
    if not lines:
        raise StockError("There is nothing to save.")
    if any(qty == 0 for _, qty in lines):
        raise StockError("Quantities can't be zero.")

    net = defaultdict(int)
    for pid, qty in lines:
        net[pid] += qty

    known = set(Product.objects.filter(pk__in=net).values_list("pk", flat=True))
    if len(known) != len(net):
        raise StockError("The list contains a product that no longer exists.")

    # Sorted so concurrent documents lock products in the same order.
    for pid, delta in sorted(net.items()):
        if delta == 0:
            continue
        # Check and change in one UPDATE, so two saves can't both spend the
        # same stock.
        updated = Product.objects.filter(pk=pid, stock_quantity__gte=-delta).update(
            stock_quantity=F("stock_quantity") + delta
        )
        if not updated:
            product = Product.objects.get(pk=pid)
            raise StockError(
                f"Not enough stock for {product.name}: "
                f"{product.stock_quantity} in stock, {-delta} needed."
            )

    doc = StockDocument.objects.create(kind=kind, note=note, created_by=user, reverses=reverses)
    StockMove.objects.bulk_create(
        StockMove(document=doc, product_id=pid, quantity=qty) for pid, qty in lines
    )
    return doc


def reverse_document(doc, user=None):
    """Post a new document that undoes `doc`. The original is left untouched."""
    if doc.kind == StockDocument.Kind.REVERSAL:
        raise StockError(f"{doc} is itself a reversal. Post a new document instead.")
    if StockDocument.objects.filter(reverses=doc).exists():
        raise StockError(f"{doc} has already been reversed.")
    lines = [(m.product_id, -m.quantity) for m in doc.lines.all()]
    return post_document(
        StockDocument.Kind.REVERSAL, lines, note=f"Reversal of {doc}", user=user, reverses=doc
    )
