# Overriding `save()`

`save()` runs every time a single object is written to the database: from the
shell, from `form.save()` in our views and from the admin.
That makes it the single place to put rules that must always apply.

## The import

```python
from django.db import models
from django.utils.text import slugify
```

`slugify` turns text into a URL-friendly form:

```python
>>> from django.utils.text import slugify
>>> slugify("  Wireless Mouse (Black)! ")
'wireless-mouse-black'
```

It lowercases the text, strips spaces from the ends, turns spaces into `-` and removes special characters.

## Example: clean the name and auto-generate a SKU

```python
class Product(models.Model):
    name = models.CharField(max_length=200)
    description = models.TextField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    sku = models.CharField(max_length=50, blank=True)

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        self.name = self.name.strip().title()          # clean the data
        if not self.sku:
            self.sku = slugify(self.name).upper()      # auto-generate
        print("Creating" if self.pk is None else "Updating", self.name)
        super().save(*args, **kwargs)                  # NEVER forget this
```

### Key ideas

- **`self.pk is None`** means the object is new and not yet in the database. After the first save, it has a `pk`.
- **`*args, **kwargs`** pass along any options Django sends (such as `update_fields`).
- **`super().save(...)`** is the line that actually writes to the database. Your code runs before it.

## Demo steps

1. Add the `sku` field and the `save()` method.
2. Run:
   ```
   python3 manage.py makemigrations
   python3 manage.py migrate
   ```
   The seeded products now have an empty `sku`.
3. In `python3 manage.py shell`:
   ```python
   >>> from core.models import Product
   >>> for p in Product.objects.all():
   ...     p.save()
   ```
   Watch "Updating ..." print for every product, then check the admin. All SKUs are filled in.
4. Create a product through the **Add Product** form (`form.save()`) and then through the **admin**.
   The same `save()` runs both times.
5. **Break it on purpose:** comment out `super().save(...)` and add a product.
   The form appears to succeed, but nothing is saved to the database.

## Gotcha: bulk operations skip `save()`

These work on the database directly and do **not** call your `save()`:

```python
Product.objects.filter(...).update(price=500)   # no save() called
Product.objects.bulk_create([...])              # no save() called
```

## Homework

Add a `stock = models.IntegerField(default=0)` field. In `save()`, raise
`ValueError("Stock cannot be negative")` if `stock < 0`.

Question: what happens when you enter `-5` in the form? Does the user see a
nice error message? (Hint: this leads to `clean()` and form validation.)
