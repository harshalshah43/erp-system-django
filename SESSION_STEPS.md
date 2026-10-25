# Session Steps

Branch: `lesson2` · Project: `erp-system-django` (app: `core`)

## 1. Product form and template

- Created [erp/core/forms.py](erp/core/forms.py) with `ProductCreationForm`, a `ModelForm` on `Product` with fields `name`, `description`, `price`.
- Created [erp/core/templates/core/product_form.html](erp/core/templates/core/product_form.html) (next to `home.html` and `about.html`). It renders `{{form.as_p}}` with `{% csrf_token %}` and a Save button.

## 2. Styling with Bootstrap 5

- A first attempt with hand-written CSS was rejected. You asked for Bootstrap 5 and said not to install anything.
- Restyled `home.html` and `product_form.html` with Bootstrap 5.3.3, loaded from the jsDelivr CDN through a `<link>` tag. Nothing was installed.
  - `home.html`: `container`, and the table uses `table table-striped table-hover` with a `table-dark` header.
  - `product_form.html`: the form sits in a `card`, and the Save button is `btn btn-primary`.
- Note: the CDN link needs internet access. Form fields from `as_p` do not get Bootstrap's `form-control` class.

## 3. Add button on the home page

- Added an "Add Product" button below the table in `home.html`, first as a placeholder link (`href="#"`).
- Changed the button from `btn-primary` to `btn-dark` so it matches the dark table header.
- You then wired it up yourself:
  - `href="{% url 'add-product' %}"` in `home.html`
  - `add_product` view in [views.py](erp/core/views.py)
  - routes in [urls.py](erp/core/urls.py): `home` is now named, and `add-product` was added

## 4. Code review (no changes made)

`python manage.py check` reported no issues. Reading the code turned up these problems:

1. **`add_product`: the form is never bound to POST data.** `ProductCreationForm()` is created before the POST check, so `is_valid()` is always `False`. Fix: use `ProductCreationForm(request.POST)` on POST, and an empty form otherwise.
2. **`form.errors()` raises a `TypeError`.** `errors` is a property. Use `form.errors`.
3. **Typo:** `'form vaidation failed'` should be `'form validation failed'`.
4. **Route has no trailing slash.** `'add-product'` does not match the style of `'home/'` and `'about/'`. It is served at `/core/add-product`, and `/core/add-product/` will 404.
5. **`Product.name` has `max_length=10`.** Names like "Samsung Smart TV 32 inches" will fail validation. Check that migration `0002_alter_product_description_alter_product_name.py` has been applied with `python manage.py migrate`.
6. **The home page reads a hard-coded `products` list.** A saved product will not show up until `home` uses `Product.objects.all()`.

## Open items

- Fix items 1–4 above (waiting on your go-ahead).
- Have `home` read products from the database.
- Optionally add `form-control` classes to the form widgets.
