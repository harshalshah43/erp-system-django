# Session Steps: Stock Management

Branch: `stock-sonnet5-5` · Project: `erp-system-django` (app: `core`) · Commit: `3a98528`

## 1. Stock quantity and stock documents

Changed [erp/core/models.py](erp/core/models.py):

- `Product.stock_quantity` (`IntegerField`, default 0) was added.
- `Product.name` now has `max_length=200`. Django requires `max_length` on a `CharField`.
- `Product.description` is now `blank=True`.
- New model `StockDocument` records one incoming (`IN`) or outgoing (`OUT`) movement for a product. Its fields are `product`, `doc_type`, `quantity`, `note` and `created_at`.
  - Saving a **new** document updates the product's stock inside `transaction.atomic()`, using `select_for_update()` and an `F()` expression so concurrent saves don't clobber each other.
  - An outgoing document larger than the available stock raises `ValueError`.
  - Editing an existing document does not change stock. To correct a mistake, add an opposite document.
  - The product foreign key uses `PROTECT`, so a product with documents cannot be deleted.
- Registered `StockDocument` in [admin.py](erp/core/admin.py).
- Limitation: bulk creates and queryset `update()` bypass `save()`, so they do not adjust stock.

## 2. Migrations

- [0003_stock.py](erp/core/migrations/0003_stock.py) adds `stock_quantity`, alters `description` and `name`, and creates `StockDocument`.
- `makemigrations` stopped on an interactive prompt, because the old `0002` had made `description` nullable.
- It also deleted your tracked `0002` migration and replaced it with one named `0002_product_stock...`. I restored your `0002`, renamed mine to `0003_stock`, pointed its dependency at your `0002`, and updated the matching row in `django_migrations`.
- Afterwards `makemigrations --check` reported no changes.

## 3. Seed and unseed scripts

- [seed_products.py](erp/seed_products.py): each of the 15 products now has a stock quantity as a 4th tuple item. It uses `bulk_create`, so it only works on an empty table.
- [unseed_products.py](erp/unseed_products.py) (new): deletes those 15 products by name. It deletes their stock documents first, because of `PROTECT`.
  - It would also delete a product you added yourself that shares one of those names.
  - It has not been run.

## 4. Stock take

- URL: `/core/stock-take/`, view `stock_take`, template `stock_take.html`.
- `StockTakeForm` in [forms.py](erp/core/forms.py) builds one counted-quantity field per product, prefilled with current stock.
- On save, every difference becomes an `IN` or `OUT` document with the note "Stock take adjustment", all inside one transaction.
- Limitation: it renders one field per product, so it will not scale to a very large catalog. Two people running it at the same time could overwrite each other's counts.

## 5. Stock transaction (cart view)

The first version was a model formset with 5 rows and a product dropdown. You rejected it for two reasons: a dropdown does not work with a million items, and 5 rows is a hard limit. It was replaced.

- URL: `/core/stock-transaction/`, template `stock_transaction.html`, plain JavaScript with Bootstrap, no libraries.
- **Cart (left):** each line has an Add (incoming) or Remove (outgoing) selector, − / + buttons plus a typed quantity (minimum 1), and a ✕ to remove the line.
  - A line turns yellow if you remove more than is in stock.
  - Picking the same product again adds 1 to its quantity.
  - There is one optional note for the whole transaction.
- **Item list (right):** 15 products per page with Prev and Next, a stock badge and a **+** button on each.
  - The search box filters the list by name or ID as you type, and Enter adds the first match.
  - It is backed by `product_search` (`/core/product-search/`), which returns JSON with `results`, `page` and `has_next`.
- **Save:** Save POSTs JSON `{note, lines: [{product, type, quantity}]}` with the CSRF token in a header.
  - All lines save or none do.
  - Incoming lines are applied before outgoing ones, so a receipt and an issue for the same product in one cart can offset each other.
  - Errors come back as a 400 with a message, and the page shows it. These cover an empty cart, a quantity below 1, an unknown product and not enough stock.
- Tests with the Django test client:
  - Remove 3 plus Add 5 left stock at 2.
  - A valid line plus an oversized removal saved nothing.
  - An empty cart and an unknown product were both rejected.
  - Paging returned 15 items on page 1 and the remaining 2 on page 2.
- The page itself was not opened in a browser.

## 6. Home page and navigation

- [home.html](erp/core/templates/core/home.html): added a **Stock** column (a red "Out of stock" badge at 0), flash messages, and Stock Transaction and Stock Take buttons next to Add Product.
- [base.html](erp/core/templates/core/base.html): navbar links for Stock Transaction and Stock Take.
- Flash messages ("Stock transaction saved." and "Stock take saved.") were already being set in the views, but nothing displayed them until `home.html` was updated.

## 7. Commit

Everything was committed as `3a98528` on `stock-sonnet5-5`, without pushing. This included your previously untracked `delete_product_confirm.html`.

## Open items

- Run `python seed_products.py` (empty table only) and try both stock pages in a browser.
- Stock take could use the same search and paging approach as the cart page.
- Decide whether to push the branch.
