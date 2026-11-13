"""Bulk test data for regression testing the stock ledger.

Creates N products and gives each exactly M stock movements, posted through
core.services.post_document (the same code the pages use). Every document
has between --min-lines and --max-lines lines, each for a different product.
Some extra documents deliberately ask for more stock than exists; they must be
rejected and leave nothing behind.

Run it against a throwaway database, never your working one:

    DJANGO_SETTINGS_MODULE=... python manage.py load_regression_data --products 10000 --moves 500

The same --seed always produces the same data. At the end the command checks
its own results and fails if anything is off.
"""
import random
import time
from collections import defaultdict
from decimal import Decimal

from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.db.models import Count, Min

from core.models import Product, StockDocument, StockMove
from core.services import StockError, post_document

ADJECTIVES = ["Compact", "Heavy-duty", "Wireless", "Portable", "Premium", "Basic", "Smart",
              "Ergonomic", "Industrial", "Mini", "Pro", "Eco", "Digital", "Classic", "Ultra"]
NOUNS = ["Drill", "Cable", "Adapter", "Bracket", "Sensor", "Monitor", "Valve", "Switch",
         "Battery", "Charger", "Filter", "Pump", "Clamp", "Speaker", "Router", "Bolt Set"]


class Command(BaseCommand):
    help = "Create products and stock documents for regression testing (use a throwaway database)."

    def add_arguments(self, parser):
        parser.add_argument("--products", type=int, default=10000)
        parser.add_argument("--moves", type=int, default=500, help="Stock movements per product.")
        parser.add_argument("--min-lines", type=int, default=2)
        parser.add_argument("--max-lines", type=int, default=5)
        parser.add_argument("--fail-rate", type=float, default=0.01,
                            help="Share of documents preceded by one that must be rejected.")
        parser.add_argument("--seed", type=int, default=42)
        parser.add_argument("--batch", type=int, default=1000, help="Documents per database commit.")

    def handle(self, *args, **o):
        if o["min_lines"] < 2 or o["max_lines"] < o["min_lines"]:
            raise CommandError("Need 2 <= --min-lines <= --max-lines.")
        if o["products"] < o["max_lines"]:
            raise CommandError("Need at least --max-lines products.")
        rng = random.Random(o["seed"])
        marker = f"Regression data (seed {o['seed']})"
        if Product.objects.filter(description=marker).exists():
            raise CommandError(f"This database already has '{marker}' products. Use a fresh copy.")

        pids = self.create_products(o["products"], marker, rng)
        expected = dict.fromkeys(pids, 0)   # what stock should be, tracked independently
        stats = defaultdict(int)
        started = time.monotonic()
        total_moves = o["products"] * o["moves"]

        # One round = every product once, shuffled and cut into documents.
        # So each product gets exactly one line per round, and a document never
        # repeats a product.
        pending = []
        for round_no in range(o["moves"]):
            order = pids[:]
            rng.shuffle(order)
            for group in self.split(order, o["min_lines"], o["max_lines"], rng):
                pending.append(group)
                if len(pending) >= o["batch"]:
                    self.post_batch(pending, expected, stats, rng, o, marker)
                    pending = []
                    self.progress(stats, total_moves, started)
        self.post_batch(pending, expected, stats, rng, o, marker)
        self.progress(stats, total_moves, started, final=True)

        self.verify(pids, expected, stats, o, marker)

    def create_products(self, n, marker, rng):
        self.stdout.write(f"Creating {n} products...")
        for start in range(0, n, 1000):
            Product.objects.bulk_create([
                Product(
                    name=f"{rng.choice(ADJECTIVES)} {rng.choice(NOUNS)} {i:05d}",
                    description=marker,
                    price=Decimal(rng.randint(100, 200000)) / 100,
                )
                for i in range(start + 1, min(start + 1000, n) + 1)
            ])
        return list(Product.objects.filter(description=marker).order_by("pk").values_list("pk", flat=True))

    @staticmethod
    def split(order, lo, hi, rng):
        """Cut a list into groups of lo..hi items; a short tail joins the previous group."""
        groups, i = [], 0
        while i < len(order):
            size = rng.randint(lo, hi)
            groups.append(order[i:i + size])
            i += size
        if len(groups) > 1 and len(groups[-1]) < lo:
            groups[-2].extend(groups.pop())
        return groups

    def post_batch(self, groups, expected, stats, rng, o, marker):
        with transaction.atomic():   # one commit per batch; each document is a savepoint
            for group in groups:
                if rng.random() < o["fail_rate"]:
                    self.post_should_fail(group, expected, stats)
                lines = []
                for pid in group:
                    qty = rng.randint(1, 20)
                    if rng.random() < 0.5 and expected[pid] >= qty:
                        qty = -qty
                    lines.append((pid, qty))
                post_document(StockDocument.Kind.TRANSACTION, lines, note=marker)
                for pid, qty in lines:
                    expected[pid] += qty
                    stats["in" if qty > 0 else "out"] += 1
                stats["docs"] += 1
                stats["moves"] += len(lines)

    @staticmethod
    def post_should_fail(group, expected, stats):
        """A valid receipt plus an issue one more than available: must be rejected entirely."""
        a, b = group[0], group[1]
        try:
            post_document(StockDocument.Kind.TRANSACTION, [(a, 5), (b, -(expected[b] + 1))],
                          note="Regression: should have been rejected")
        except StockError:
            stats["rejected"] += 1
        else:
            stats["wrongly_accepted"] += 1

    def progress(self, stats, total, started, final=False):
        if not final and stats["docs"] % 50000:
            return
        elapsed = time.monotonic() - started
        done = stats["moves"] / total
        eta = elapsed / done - elapsed if done else 0
        self.stdout.write(
            f"{stats['moves']:>9,} / {total:,} moves ({done:.0%}), {stats['docs']:,} documents, "
            f"{elapsed / 60:.1f} min elapsed, ~{eta / 60:.0f} min left"
        )
        self.stdout.flush()

    def verify(self, pids, expected, stats, o, marker):
        self.stdout.write("\nVerifying...")
        problems = []

        per_product = Product.objects.filter(pk__in=pids).annotate(n=Count("moves"))
        wrong_counts = per_product.exclude(n=o["moves"]).count()
        if wrong_counts:
            problems.append(f"{wrong_counts} products do not have exactly {o['moves']} moves")

        docs = StockDocument.objects.filter(note=marker).annotate(n=Count("lines"))
        smallest = docs.aggregate(m=Min("n"))["m"]
        if smallest is None or smallest < o["min_lines"]:
            problems.append(f"smallest document has {smallest} lines (need {o['min_lines']})")
        if docs.count() != stats["docs"]:
            problems.append(f"{docs.count()} documents saved, {stats['docs']} posted")

        if StockDocument.objects.filter(note="Regression: should have been rejected").exists():
            problems.append("a document that should have been rejected was saved")
        if stats["wrongly_accepted"]:
            problems.append(f"{stats['wrongly_accepted']} oversized issues were accepted")

        mismatched = sum(
            1 for pk, stock in Product.objects.filter(pk__in=pids).values_list("pk", "stock_quantity")
            if stock != expected[pk]
        )
        if mismatched:
            problems.append(f"{mismatched} products' stock differs from the expected value")
        if Product.objects.filter(stock_quantity__lt=0).exists():
            problems.append("negative stock found")

        try:
            call_command("check_stock", stdout=self.stdout)
        except CommandError as e:
            problems.append(f"check_stock: {e}")

        self.stdout.write(
            f"Products: {len(pids):,} | documents: {stats['docs']:,} (smallest {smallest} lines) | "
            f"moves: {stats['moves']:,} ({stats['in']:,} in, {stats['out']:,} out) | "
            f"rejected as expected: {stats['rejected']:,}"
        )
        if problems:
            raise CommandError("Regression FAILED:\n  - " + "\n  - ".join(problems))
        self.stdout.write(self.style.SUCCESS("Regression data loaded and verified."))
