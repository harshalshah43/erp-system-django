# Stock Management: Implementation Plan

Project: `erp-system-django`, app `core`. Branch: `stock-opus-5-5`.

This plan describes the stock feature from the data model up to the screens, in the order it should be built. It replaces the first version (commit `3a98528`), where stock was changed inside `StockDocument.save()` and each cart line became its own document.

## 1. Goals

- Stock for every product is always explained by a permanent history of documents.
- One cart (transaction) or one stock take is **one document with many lines**.
- Only one piece of code changes stock, and it is safe when two people save at once.
- Data entry is fast from the keyboard and works with a very large catalog (no dropdown of all products).
- Users can see the history of any item and browse all incoming and outgoing documents.

## 2. Design rules

| Rule | Why |
|---|---|
| Documents and their lines are never edited or deleted. A mistake is fixed by a **reversal** document. | History stays trustworthy, and stock never drifts away from it. |
| A line stores a **signed** quantity: positive is incoming, negative is outgoing. | Stock is simply the sum of lines; stock take differences and reversals need no special cases. |
| `Product.stock_quantity` is a cached running total, changed only by `post_document()`. | Fast lists and search badges without summing the history each time. |
| The database itself refuses negative stock and zero-quantity lines. | A last line of defence if code ever bypasses the service. |
| Products with history are archived, not deleted. | Lines point at products with `PROTECT`. |

## 3. Data model ([erp/core/models.py](erp/core/models.py))

**Product** (existing model, changed)
- `name` `CharField(max_length=200)`, `description` `TextField(blank=True)`, `price` `DecimalField`
- `stock_quantity` `IntegerField(default=0, editable=False)`: hidden from all forms and the admin form
- `is_active` `BooleanField(default=True)`: `False` means archived
- Constraint `product_stock_not_negative`: `stock_quantity >= 0`

**StockDocument** (the header)
- `kind`: `TXN` Stock transaction, `TAKE` Stock take, `OPEN` Opening balance, `REV` Reversal
- `note` (optional, 255), `created_at` (auto), `created_by` (user, nullable, `SET_NULL`)
- `reverses`: `OneToOneField('self', null=True, PROTECT, related_name='reversed_by')`. One-to-one, so a document can only be reversed once.
- Default ordering: newest first.

**StockMove** (the lines)
- `document` → `StockDocument` (`PROTECT`, `related_name='lines'`)
- `product` → `Product` (`PROTECT`, `related_name='moves'`)
- `quantity` `IntegerField`: signed
- Constraint `stockmove_quantity_not_zero`: `quantity != 0`

Invariant: for every product, `stock_quantity == SUM(moves.quantity)`.

## 4. Posting service ([erp/core/services.py](erp/core/services.py))

The only code that changes stock.

```python
class StockError(Exception): ...   # message is safe to show to users

@transaction.atomic
def post_document(kind, lines, note="", user=None, reverses=None):
    # lines: [(product_id, signed_qty), ...]
```

Steps inside `post_document`:
1. Reject an empty list or any zero quantity (`StockError`).
2. Net the quantities per product. Receiving 5 and issuing 3 of the same item needs only the net +2 to be possible, so line order does not matter.
3. Reject unknown products.
4. For each product, in sorted id order (consistent lock order), run one conditional update:
   ```python
   Product.objects.filter(pk=pid, stock_quantity__gte=-delta) \
          .update(stock_quantity=F("stock_quantity") + delta)
   ```
   If no row was updated, raise `StockError("Not enough stock for X: 4 in stock, 6 needed.")`. Checking and changing in one statement means two saves can never spend the same stock, on any database (SQLite ignores `select_for_update`).
5. Create the header, then `bulk_create` the lines exactly as entered.

Any error rolls back everything: all lines save or none do.

`reverse_document(doc, user=None)` posts a `REV` document with every line negated and `reverses=doc`. It refuses to reverse a reversal or reverse the same document twice. It fails normally if the stock has already been issued.

## 5. Migrations

Built on top of `0003_stock`, which added `stock_quantity` and the first single-line `StockDocument`.

**`0004_stock_ledger`**: additive changes plus data conversion
1. Add `Product.is_active`; make `stock_quantity` non-editable.
2. Add `kind`, `created_by`, `reverses` to `StockDocument`; create `StockMove`.
3. Make the old `product`, `doc_type`, `quantity` columns nullable, so new headers can be created during the conversion.
4. `RunPython`:
   - Each old document becomes a header with one signed line. The note "Stock take adjustment" becomes kind `TAKE`, everything else `TXN`.
   - For every product whose stock is not explained by its lines (seeded or typed-in stock), add one `OPEN` document with the difference, so the invariant holds from day one.

**`0005_stock_ledger_cleanup`**: drop the old columns, set ordering, add both check constraints.

Schema changes and data writes are split across two migrations because PostgreSQL refuses to alter a table with pending trigger events in the same transaction. The conversion is not reversible.

Verify with `python manage.py makemigrations --check` (no changes) and `python manage.py check_stock`.

> All branches share one `db.sqlite3`. Running `migrate` on a branch with different migrations can rebuild tables from that branch's models and drop columns. Back up the DB before switching branches and migrating.

## 6. Admin ([erp/core/admin.py](erp/core/admin.py))

- **Product**: list shows name, price, stock, active; stock is read-only; filter by active; search by name.
- **StockDocument**: read-only (no add, change or delete permission), lines shown as a read-only inline, filter by kind.
- Admin action **"Reverse selected documents"** calls `reverse_document()` and reports success or the `StockError` message per document.

## 7. Product pages

- `ProductForm` lists `name`, `description`, `price` explicitly. Stock never appears on a form, and new model fields are not exposed by accident.
- `edit_product` binds the POST to `instance=product` so it updates instead of creating a new product.
- `delete_product`: on POST, try to delete; on `ProtectedError`, set `is_active=False` and show "X has stock history, so it was archived instead of deleted." The confirmation page warns about this in advance.
- Home page and product search show only active products.

## 8. Stock Transaction page (keyboard-first)

URL `/core/stock-transaction/`, template [stock_cart.html](erp/core/templates/core/stock_cart.html) (shared with Stock Take), plain JavaScript and Bootstrap 5.0, no libraries.

**Layout**
- Left: the cart table. Its first row is the **entry line**: Product · In stock · IN/OUT switch · − Qty + · **Add line** · ✕ (clear). Added lines appear below it. Then a note field and Save.
- Right: the item list with a search box, 15 items per page, Prev/Next, stock badge and **+** per item.

**IN/OUT switch**
- A single button with both labels always visible: IN on the left, OUT on the right. The active side is filled (green IN, red OUT).
- Enter, Space or a click flips it. ← sets IN, → sets OUT.
- The direction carries over to the next line, so a run of receipts or issues just tabs past it.
- Cart rows show the same switch (smaller); clicking it flips that row.

**Keyboard flow**

| Step | Field | Key | Result |
|---|---|---|---|
| 1 | Search | type | List filters by name or ID (200 ms debounce) |
| 2 | Search | Enter | First match goes into the entry line; focus moves to the switch. Clicking an item does the same. |
| 3 | Switch | Enter | Flips IN ↔ OUT |
| 4 | Switch | Tab | Focus to Qty, number selected so typing replaces it |
| 5 | Qty | Enter | Adds the line, clears the entry line, focus back to Search with its text selected |
| – | Qty | Tab | Focus to **Add line**; Enter on it also adds the line |
| – | any | Shift+Tab | Back one field |

The − and + buttons work as before but are skipped by Tab (`tabindex="-1"`) so Tab goes straight from the switch to Qty.

**Rules on the page**
- Enter in Search before the list has refreshed waits for the new results first. A request counter ignores stale responses.
- Same product and same direction merges into the existing line; the opposite direction is a separate line.
- A line turns yellow when an OUT quantity is more than the stock shown. It is a warning only; the server decides on save.
- Adding with no item picked shows "Pick an item from the list first." A quantity below 1 keeps focus in Qty.
- Save is blocked while an item is still sitting in the entry line ("press Add line, or ✕ to clear it").
- Item names are inserted with `textContent` to avoid HTML injection.

**Server side**
- `GET /core/product-search/?q=&page=` returns `{results: [{id, name, stock}], page, has_next}`. It fetches 16 rows to know whether a next page exists, avoiding a `COUNT` on a large table.
- Save POSTs JSON `{note, lines: [{product, type: "IN"|"OUT", quantity}]}` with the CSRF token in a header.
- The view turns each line into `(product_id, ±quantity)` and calls `post_document(TXN, ...)`.
- Success: flash "Stock transaction #N saved." and return `{redirect}`. Failure: HTTP 400 `{error}` shown in the red alert on the page.

## 9. Stock Take page

URL `/core/stock-take/`, same template and item list, no switch.

- Picking an item adds a line with columns On record · Counted · Difference, and puts the cursor in Counted with the number selected.
- The difference updates live while typing. Enter in Counted returns to Search.
- Each line remembers the stock the counter saw (`expected`). On save, POST `{product, counted, expected}`; the server posts `counted − expected` for lines that differ, as a `TAKE` document.
- Posting the difference (not overwriting stock with the count) keeps receipts or issues that other people saved while the count was in progress.
- Only counted items are touched. If every count matches, nothing is posted and the user is told so.

## 10. Item history

URL `/core/products/<id>/history/`, template `product_history.html`, linked from a **History** button in each row of the home page table and from document lines.

- Header: product name, current stock, "Archived" badge if inactive.
- Table, newest first, 25 per page: Date · Document (link) · Type · Note · Change (IN +5 / OUT −3) · Balance · By.
- Balance is the stock after that movement, calculated in the database with a window function:
  ```python
  Window(Sum("quantity"), order_by=[F("document_id").asc(), F("pk").asc()])
  ```

## 11. Documents tab

Navbar link **Documents**.

**List** (`/core/documents/`, `document_list.html`)
- Pills: **All / Incoming / Outgoing**. Incoming means the document has at least one positive line, outgoing at least one negative line. A document with both appears under both.
- Type dropdown: Stock transaction, Stock take, Opening balance, Reversal. It combines with the pills.
- Columns: # (link) · Date · Type · Note · Lines · In total · Out total · By. 25 per page; filters are kept while paging (`{% querystring %}`).
- Filtering uses `Exists()` subqueries, not `filter(lines__...)`, so the line count and totals still include every line of the document. An explicit `order_by` is needed because Django drops `Meta.ordering` on grouped queries.

**Detail** (`/core/documents/<id>/`, `document_detail.html`)
- Date, type, note, user, "Reverses #x" / "Reversed by #y" links.
- Lines: product (links to its history) and change.

Shared snippets: `_pager.html`, `_kind_badge.html`, `_qty.html`.

## 12. Scripts and commands

- [seed_products.py](erp/seed_products.py): creates 15 products, then posts their starting stock as one `OPEN` document ("Seed data").
- [unseed_products.py](erp/unseed_products.py) (development only): deletes those products' lines, then documents left with no lines, then the products.
- `python manage.py check_stock`: lists any product whose stock does not equal the sum of its lines and exits with an error if there is one.
- `python manage.py load_regression_data`: bulk test data for regression testing (see section 16). Only for the regression database.
- [regression_timings.py](erp/regression_timings.py): times every stock page against a running server.

## 13. URLs ([erp/core/urls.py](erp/core/urls.py), under `/core/`)

| Path | View | Name |
|---|---|---|
| `stock-transaction/` | `stock_transaction` | `stock-transaction` |
| `stock-take/` | `stock_take` | `stock-take` |
| `product-search/` | `product_search` | `product-search` |
| `products/<id>/history/` | `product_history` | `product-history` |
| `documents/` | `document_list` | `documents` |
| `documents/<id>/` | `document_detail` | `document-detail` |

## 14. Tests ([erp/core/tests.py](erp/core/tests.py), 31 tests)

Run with `python manage.py test core`.

- **Service**: one document with many lines; all-or-nothing on insufficient stock; netting per product; empty, zero and unknown products rejected; database constraints.
- **Reversal**: restores stock and leaves the original untouched; no double reversal; no reversing a reversal; fails if the stock is already issued.
- **Stock transaction view**: saves one document; every kind of bad input returns 400 and saves nothing.
- **Stock take view**: only counted items change; a receipt during the count is kept; matching counts save nothing; negative counts rejected.
- **Products**: no stock field on the form; edit updates in place; delete without history deletes; delete with history archives and hides from home and search; search paging.
- **Admin**: documents cannot be added, changed or deleted; stock not editable; reverse action works.
- **`check_stock`**: reports a mismatch.
- **History and documents**: home links to history; running balance newest first; archived product history; Incoming/Outgoing/type filters; totals count every line when filtered; reversal links; 404 for a missing document.

Every test that changes stock also checks the invariant (`stock_quantity == SUM(moves)`).

**Browser check** (manual or headless Chrome): drive the transaction page with real key presses (type, Enter, Enter, Tab, quantity, Enter) and confirm focus moves as in section 8 and the saved document has the right signed lines.

## 15. Build order

1. Models and `services.py` with their tests.
2. Migrations `0004` and `0005`; run them on a **copy** of the database first, then `check_stock`.
3. Admin, product form and archive-on-delete.
4. Stock Transaction page with the entry line and switch, then Stock Take on the same template.
5. Item history and the Documents tab.
6. Seed and unseed scripts, `check_stock` command.
7. Full test run, `makemigrations --check`, browser check.

## 16. Regression testing

### 16.1 What was tested (14 Nov 2026)

The whole stock feature was loaded with a large volume of data and checked for correctness and speed.

| Requirement | Result |
|---|---|
| 10,000 new products with random names and prices | 10,000 created (named like "Compact Drill 00001") |
| 500 stock movements on **each** product, all dated today | Exactly 500 per product, 5,000,000 lines (2,578,364 IN, 2,421,636 OUT) |
| Every document has **at least 2 lines** | 1,428,441 documents, 2–5 lines each (each line a different product), smallest has 2 |
| Oversized issues are rejected and leave nothing behind | 14,154 attempted, all rejected, none saved |
| Stock equals the expected value for every product | All 10,000 match |
| Stock equals the sum of lines (`check_stock`) | Passes |
| No negative stock | None |

Load time: 16.5 minutes on SQLite. Database size: 329 MB.

Dates are stored in UTC, so documents created on 14 Nov after midnight India time show as 13 Nov in the raw database. The pages show the local date.

### 16.2 How the test was conducted

1. **A separate database.** The test runs on `erp/regression.sqlite3`, a copy of `db.sqlite3`, selected by the settings file [settings_regression.py](erp/erp/settings_regression.py). Your working database is never touched. `regression.sqlite3` is in `.gitignore`.
2. **The generator** is the management command [load_regression_data.py](erp/core/management/commands/load_regression_data.py):
   - Creates the products (all with description `Regression data (seed 42)` so they can be found later).
   - Works in 500 **rounds**. In each round every product is used exactly once: the product list is shuffled and cut into documents of 2–5 lines. This guarantees exactly 500 movements per product and never repeats a product inside one document.
   - Each line is a random quantity of 1–20, IN or OUT at random. An OUT is only generated when the generator's own copy of the stock allows it, so the regular documents should all succeed.
   - Every document is posted through `post_document()`, the same code the pages use, so the stock check, netting and all-or-nothing saving are all exercised. Documents are committed in batches of 1,000.
   - About 1% of the time it first posts a document that must fail: a valid receipt plus an issue of one more than is in stock. It must raise `StockError` and save nothing.
   - The same `--seed` always produces exactly the same data.
3. **Self-check at the end.** The command fails with "Regression FAILED" and a list of problems if any of these are wrong: 500 lines per product, at least 2 lines per document, document count, no rejected document saved, stock equal to its own expected value for every product, no negative stock, `check_stock`.
4. **Page timings.** [regression_timings.py](erp/regression_timings.py) requests each page three times from a running server and prints the median and slowest time and the page size, then saves three 3-line transactions.

### 16.3 Timing results (10,000 products, 1.4 million documents, 5 million lines)

| Page | Time | Verdict |
|---|---|---|
| Home (all 10,000 products) | 0.31 s, **4.7 MB** of HTML | Server is fine; the browser must draw 10,000 rows |
| Product search (empty, by name, deep page, by ID) | 0.001–0.002 s | Fine |
| Item history (first and last page) | 0.006 s | Fine |
| **Documents: All / Incoming / Outgoing / with type** | **5.9–6.8 s** | Too slow |
| **Documents: page 20,000** | **7.2 s** | Too slow |
| Document detail | 0.002 s | Fine |
| Stock Transaction and Stock Take pages | 0.001 s | Fine |
| Save a 3-line transaction | 0.002 s | Fine |

**Findings to fix**
- **Documents list:** every load totals the lines of all 1.4 million documents (to show 25), counts every document for "Page X of Y", and sorts by an unindexed date. Fix: sort by document number, total only the 25 documents on screen, use Prev/Next paging without a count.
- **Home page:** no paging. Fix: 50 products per page plus a search box.
- **Search:** fast at 10,000 products, but `LIKE '%q%'` will slow down around a million. Fix: the indexed SKU in section 17.

### 16.4 Run the app

All commands are run from the `erp` folder (the one with `manage.py`).

**Your normal app** (working database `db.sqlite3`):
```
cd erp
python manage.py migrate
python manage.py runserver
```
Open http://127.0.0.1:8000/core/home/

**The app on the regression database** (on a different port, so both can run at once):
```
cd erp
DJANGO_SETTINGS_MODULE=erp.settings_regression python manage.py runserver 8001
```
Open http://127.0.0.1:8001/core/home/ for the 10,000 test items, http://127.0.0.1:8001/core/documents/ for the documents, and any item's **History** button for its 500 movements.

The admin (http://127.0.0.1:8001/admin/) uses the users copied from `db.sqlite3`. To add one only for the regression database:
```
DJANGO_SETTINGS_MODULE=erp.settings_regression python manage.py createsuperuser
```

### 16.5 View the database

**Command line** (`sqlite3` comes with macOS):
```
cd erp
sqlite3 -header -column regression.sqlite3
```
Useful queries:
```sql
-- Overall counts
SELECT COUNT(*) FROM core_product WHERE description = 'Regression data (seed 42)';
SELECT COUNT(*) FROM core_stockdocument WHERE note = 'Regression data (seed 42)';
SELECT COUNT(*) FROM core_stockmove;

-- Movements per regression product (both 500; a few more after running regression_timings.py)
SELECT MIN(moves), MAX(moves) FROM (
  SELECT COUNT(*) AS moves FROM core_stockmove m JOIN core_product p ON p.id = m.product_id
  WHERE p.description = 'Regression data (seed 42)' GROUP BY m.product_id);

-- Smallest regression document (must be 2 or more lines)
SELECT MIN(n) FROM (
  SELECT COUNT(*) AS n FROM core_stockmove m JOIN core_stockdocument d ON d.id = m.document_id
  WHERE d.note = 'Regression data (seed 42)' GROUP BY m.document_id);

-- One product's history with the running balance
SELECT d.id, d.created_at, m.quantity,
       SUM(m.quantity) OVER (ORDER BY d.id, m.id) AS balance
FROM core_stockmove m JOIN core_stockdocument d ON d.id = m.document_id
WHERE m.product_id = 41 ORDER BY d.id DESC LIMIT 10;

-- Stock should equal the sum of lines (no rows = correct)
SELECT p.id, p.name, p.stock_quantity, SUM(m.quantity) AS ledger
FROM core_product p LEFT JOIN core_stockmove m ON m.product_id = p.id
GROUP BY p.id HAVING p.stock_quantity != COALESCE(SUM(m.quantity), 0);
```
Type `.quit` to leave.

**With a viewer:** open `erp/regression.sqlite3` in DB Browser for SQLite (free) or a VS Code SQLite extension. The tables are `core_product`, `core_stockdocument` and `core_stockmove`.

**Through Django:** `DJANGO_SETTINGS_MODULE=erp.settings_regression python manage.py check_stock`

### 16.6 Run the test again

1. **Start from a fresh copy** of the working database (the command refuses to run twice on the same database with the same seed):
   ```
   cd erp
   python manage.py migrate
   rm -f regression.sqlite3
   cp db.sqlite3 regression.sqlite3
   DJANGO_SETTINGS_MODULE=erp.settings_regression python manage.py migrate
   ```
2. **Load and verify the data** (about 16 minutes; progress is printed every 50,000 documents):
   ```
   DJANGO_SETTINGS_MODULE=erp.settings_regression python manage.py load_regression_data --products 10000 --moves 500 --seed 42
   ```
   It must end with "Regression data loaded and verified." Anything else is a failure, with the reasons listed.

   Options: `--products`, `--moves` (per product), `--min-lines` (at least 2) and `--max-lines` per document, `--fail-rate` (share of must-fail documents, default 0.01), `--seed`, `--batch` (documents per commit). For a quick check:
   ```
   DJANGO_SETTINGS_MODULE=erp.settings_regression python manage.py load_regression_data --products 200 --moves 50
   ```
3. **Run the automated tests** (they use their own temporary database):
   ```
   python manage.py test core
   ```
4. **Time the pages.** Start the regression server in one terminal:
   ```
   DJANGO_SETTINGS_MODULE=erp.settings_regression python manage.py runserver 8001
   ```
   Find a regression product id and the latest document id in another terminal:
   ```
   sqlite3 regression.sqlite3 "SELECT MIN(id) FROM core_product WHERE description LIKE 'Regression%'; SELECT MAX(id) FROM core_stockdocument;"
   ```
   Then run (with those two numbers):
   ```
   python regression_timings.py http://127.0.0.1:8001 41 1428465
   ```
   Compare the output with the table in 16.3. The timing script saves three small "timing" documents, so that product ends up with a few more than 500 movements.
5. **Check in the browser:** open http://127.0.0.1:8001/core/home/, an item's History, Documents with All/Incoming/Outgoing, and save a transaction with the keyboard flow from section 8.
6. **Clean up** when done: stop the server (Ctrl+C) and `rm regression.sqlite3`.

## 17. Not done yet

- **Regression findings** (section 16.3): fast Documents list and paged Home page.
- **Very large catalogs**: name search uses `icontains` (`LIKE '%q%'`), a full scan per keystroke. Add a unique, indexed SKU searched by prefix, or a trigram index on PostgreSQL.
- **Users**: there is no login, so `created_by` is empty for documents made on the site pages.
- **Reversal from the site**: reversing is only available in the admin; a Reverse button on the document page would be a small addition.
- **Seed scripts** could become management commands (`manage.py seed_products --reset`).
- **Decimal quantities** (kg, metres) would need `DecimalField` quantities throughout.
