from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0004_stock_ledger"),
    ]

    operations = [
        migrations.RemoveField(model_name="stockdocument", name="product"),
        migrations.RemoveField(model_name="stockdocument", name="doc_type"),
        migrations.RemoveField(model_name="stockdocument", name="quantity"),
        migrations.AlterModelOptions(
            name="stockdocument",
            options={"ordering": ["-created_at", "-pk"]},
        ),
        migrations.AddConstraint(
            model_name="product",
            constraint=models.CheckConstraint(
                condition=models.Q(stock_quantity__gte=0), name="product_stock_not_negative"
            ),
        ),
        migrations.AddConstraint(
            model_name="stockmove",
            constraint=models.CheckConstraint(
                condition=models.Q(quantity=0, _negated=True), name="stockmove_quantity_not_zero"
            ),
        ),
    ]
