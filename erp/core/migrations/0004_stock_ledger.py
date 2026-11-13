"""Split StockDocument into a header (StockDocument) and lines (StockMove).

Each old single-product document becomes a header with one signed line. Then,
for every product whose stock_quantity is not explained by its lines (for
example stock typed into the product form, or set by the seed script), one
"Opening balance" document is added so stock always equals the sum of moves.

0005 removes the old columns afterwards. The two are separate so the schema
change doesn't run in the same transaction as these data writes.
"""
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models
from django.db.models import Sum


def convert_documents(apps, schema_editor):
    Product = apps.get_model("core", "Product")
    StockDocument = apps.get_model("core", "StockDocument")
    StockMove = apps.get_model("core", "StockMove")

    for doc in StockDocument.objects.all():
        doc.kind = "TAKE" if doc.note == "Stock take adjustment" else "TXN"
        doc.save(update_fields=["kind"])
        if doc.quantity:
            sign = 1 if doc.doc_type == "IN" else -1
            StockMove.objects.create(document=doc, product_id=doc.product_id, quantity=sign * doc.quantity)

    opening = []
    for product in Product.objects.annotate(ledger=Sum("moves__quantity")):
        diff = product.stock_quantity - (product.ledger or 0)
        if diff:
            opening.append((product.pk, diff))
    if opening:
        doc = StockDocument.objects.create(
            kind="OPEN", note="Opening balance: stock on hand when the ledger was introduced"
        )
        StockMove.objects.bulk_create(
            StockMove(document=doc, product_id=pid, quantity=qty) for pid, qty in opening
        )


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0003_stock"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name="product",
            name="is_active",
            field=models.BooleanField(default=True),
        ),
        migrations.AlterField(
            model_name="product",
            name="stock_quantity",
            field=models.IntegerField(default=0, editable=False),
        ),
        migrations.AddField(
            model_name="stockdocument",
            name="kind",
            field=models.CharField(
                choices=[("TXN", "Stock transaction"), ("TAKE", "Stock take"),
                         ("OPEN", "Opening balance"), ("REV", "Reversal")],
                default="TXN",
                max_length=4,
            ),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="stockdocument",
            name="created_by",
            field=models.ForeignKey(
                blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL,
                related_name="+", to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddField(
            model_name="stockdocument",
            name="reverses",
            field=models.OneToOneField(
                blank=True, null=True, on_delete=django.db.models.deletion.PROTECT,
                related_name="reversed_by", to="core.stockdocument",
            ),
        ),
        migrations.CreateModel(
            name="StockMove",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("quantity", models.IntegerField()),
                ("document", models.ForeignKey(
                    on_delete=django.db.models.deletion.PROTECT, related_name="lines", to="core.stockdocument")),
                ("product", models.ForeignKey(
                    on_delete=django.db.models.deletion.PROTECT, related_name="moves", to="core.product")),
            ],
        ),
        # The old per-document columns become nullable so new headers (the
        # opening balance) can be created before 0005 drops them.
        migrations.AlterField(
            model_name="stockdocument",
            name="product",
            field=models.ForeignKey(
                null=True, on_delete=django.db.models.deletion.PROTECT,
                related_name="documents", to="core.product",
            ),
        ),
        migrations.AlterField(
            model_name="stockdocument",
            name="doc_type",
            field=models.CharField(choices=[("IN", "Incoming"), ("OUT", "Outgoing")], max_length=3, null=True),
        ),
        migrations.AlterField(
            model_name="stockdocument",
            name="quantity",
            field=models.PositiveIntegerField(null=True),
        ),
        # Not reversible: the old columns can't hold multi-line documents.
        migrations.RunPython(convert_documents),
    ]
