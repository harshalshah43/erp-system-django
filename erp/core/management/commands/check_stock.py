from django.core.management.base import BaseCommand, CommandError
from django.db.models import F, Sum
from django.db.models.functions import Coalesce

from core.models import Product


class Command(BaseCommand):
    help = "Check that every product's stock_quantity equals the sum of its stock moves."

    def handle(self, *args, **options):
        wrong = (
            Product.objects.annotate(ledger=Coalesce(Sum("moves__quantity"), 0))
            .exclude(stock_quantity=F("ledger"))
            .order_by("name")
        )
        for p in wrong:
            self.stdout.write(f"{p.name} (id {p.pk}): stock {p.stock_quantity}, moves add up to {p.ledger}")
        if wrong:
            raise CommandError(f"{len(wrong)} product(s) out of balance.")
        self.stdout.write(self.style.SUCCESS("Stock matches the moves for every product."))
