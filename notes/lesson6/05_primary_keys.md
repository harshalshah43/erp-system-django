# Assigning a Primary Key

Add `primary_key=True` to a field. That field replaces the automatic `id`.

## 1. Use your own field

```python
class Product(models.Model):
    sku = models.CharField(max_length=50, primary_key=True)
    name = models.CharField(max_length=200)
```

- `primary_key=True` makes the field **unique** and **not null** automatically.
- A model can have **only one** primary key.
- You must provide the value yourself, or set it in `save()`.

## 2. Keep an auto number but change its type

```python
id = models.AutoField(primary_key=True)      # normal integer
id = models.BigAutoField(primary_key=True)   # large integer (Django's default)
```

The project-wide default is set in `erp/settings.py`:

```python
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
```

## 3. Use a UUID (common in real systems)

```python
import uuid

class Product(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
```

This gives IDs like `3f2b8c1e-9a4d-4c1b-...`. They are hard to guess, so URLs do not reveal how many products exist.

## Choosing a good primary key

Use something that **never changes**.

A SKU built from the product name is a poor primary key: if the product is
renamed, every link and foreign key pointing to it breaks.

A better design is to keep the automatic `id` and make the SKU unique:

```python
sku = models.CharField(max_length=50, unique=True)
```

| Option | Good for |
|---|---|
| Auto `id` (default) | Most models |
| `UUIDField` | Public URLs, APIs, merging data from several systems |
| Natural key (`sku`, `email`) | Rarely. Only if the value truly never changes |

## Caution: changing the primary key on existing data

Changing the primary key on a table that already has rows (our seeded products)
gives a messy migration. Django will ask for defaults, and existing rows can clash.

For practice, either:
- try it on a **new, throwaway model**, or
- delete `db.sqlite3` and the migration files (keep `__init__.py` in `migrations/`), run
  `makemigrations` and `migrate`, then reseed with `seed_products.py`.
