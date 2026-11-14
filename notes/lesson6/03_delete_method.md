# Overriding `delete()`: Soft Delete

Real ERP systems rarely remove records, because invoices and orders may still
refer to them. Instead, records are marked inactive. This is called a **soft delete**.

## Example

```python
class Product(models.Model):
    ...
    is_active = models.BooleanField(default=True)

    def delete(self, *args, **kwargs):
        self.is_active = False
        self.save()          # no super().delete(), so the row stays
```

Run `makemigrations` and `migrate`.

Show only active products in the home view:

```python
products = Product.objects.filter(is_active=True)
```

### Normal delete vs soft delete

| | Normal `delete()` | Our soft `delete()` |
|---|---|---|
| Row in database | Removed | Kept |
| `is_active` | n/a | `False` |
| Can be restored | No | Yes, set `is_active=True` |

## Demo: the gotcha

1. Open a product in the admin and click **Delete** on its detail page.
   The row is still in the database with `is_active=False`, because your `delete()` ran.
2. In the admin **list**, select a product and use the **"Delete selected"** action.
   The row is really gone.

**Why?** "Delete selected" calls `QuerySet.delete()`, which deletes in bulk
and never calls the model's `delete()` method.

```python
product.delete()                        # calls your Product.delete()
Product.objects.filter(...).delete()    # skips it
```

## Rule to remember

> Model methods (`save()`, `delete()`) run **per object**.
> Bulk QuerySet operations (`update()`, `bulk_create()`, `QuerySet.delete()`) **skip them**.
