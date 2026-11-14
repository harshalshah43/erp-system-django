# `pk` vs `id`

In our project they hold the same value, but they are different things.

## `id`: a real column

We never wrote an `id` field in `Product`. Django added one automatically:

```python
id = models.BigAutoField(primary_key=True)   # added for you
```

You can see it in `core/migrations/0001_initial.py`.

## `pk`: a shortcut

`pk` is not a column. It is an alias Django provides on every model, and it
always points to **whichever field is the primary key**.

```python
>>> p = Product.objects.first()
>>> p.id, p.pk
(1, 1)
>>> Product.objects.get(pk=1) == Product.objects.get(id=1)
True
```

## When they differ

If another field is the primary key, `id` no longer exists:

```python
class Product(models.Model):
    sku = models.CharField(max_length=50, primary_key=True)
```
```python
>>> p.pk     # 'GAMING-LAPTOP'
>>> p.id     # AttributeError: there is no id field now
```

## Why prefer `pk`

Code written with `pk` works on any model, whatever its primary key is called.
Django itself uses it, for example:

- `Model.__eq__` compares `pk` (see `01_dunder_methods.md`)
- `self.pk is None` in `save()` checks whether an object is new (see `02_save_method.md`)

The same habit applies in URLs and views:

```python
path("product/<int:pk>/", views.product_detail, name="product-detail")
product = get_object_or_404(Product, pk=pk)
```

> **Remember:** `id` is the column's name, and `pk` means "whatever the primary key is." Use `pk`.
