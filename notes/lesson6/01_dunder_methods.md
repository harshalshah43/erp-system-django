# Dunder Methods

"Dunder" means **d**ouble **under**score, as in `__str__` and `__len__`.
You never call them yourself. Python calls them when you use an operator or a built-in function.

| You write | Python calls |
|---|---|
| `print(obj)`, `str(obj)`, `{{ obj }}` | `obj.__str__()` |
| `len(obj)` | `obj.__len__()` |
| `a == b` | `a.__eq__(b)` |
| `a < b`, `sorted(...)` | `a.__lt__(b)` |
| `a + b` | `a.__add__(b)` |
| `for x in obj` | `obj.__iter__()` |
| `obj[0]` | `obj.__getitem__(0)` |
| `if obj:` | `obj.__bool__()` |
| `Product(...)` | `__init__` |

## Step 1: Why `__str__` matters

Comment out `__str__` in `core/models.py`, then open the shell:

```python
>>> Product.objects.first()
<Product: Product object (1)>      # not helpful
```

Put it back:

```python
def __str__(self):
    return self.name
```
```python
>>> Product.objects.first()
<Product: Laptop>
```

Django uses `__str__` in the admin list, in templates (`{{ product }}`), in form dropdowns and in `print()`.

## Step 2: Dunders in a plain Python class (no Django)

```python
class Box:
    def __init__(self, items):      # Box([...])
        self.items = items

    def __str__(self):              # print(b)
        return f"Box with {len(self.items)} items"

    def __len__(self):              # len(b)
        return len(self.items)

    def __eq__(self, other):        # b1 == b2
        return self.items == other.items

    def __add__(self, other):       # b1 + b2
        return Box(self.items + other.items)
```
```python
>>> b1 = Box(["pen", "book"])
>>> b2 = Box(["bag"])
>>> print(b1)
Box with 2 items
>>> len(b1 + b2)
3
>>> b1 == Box(["pen", "book"])
True
```

## Step 3: Dunders Django already wrote for you

A model is just a Python class, and Django has already defined many dunders on it.

```python
>>> a = Product.objects.get(pk=1)
>>> b = Product.objects.get(pk=1)
>>> a == b        # True:  Model.__eq__ compares primary keys
>>> a is b        # False: two different objects in memory
```

QuerySets have dunders too:

```python
>>> qs = Product.objects.all()
>>> len(qs)       # QuerySet.__len__
>>> qs[0]         # QuerySet.__getitem__
>>> for p in qs:  # QuerySet.__iter__ (what {% for %} uses in templates)
...     print(p)
>>> if qs:        # QuerySet.__bool__
...     print("we have products")
```

## Exercise: sort products by price

Add to `Product`:

```python
def __lt__(self, other):
    return self.price < other.price
```
```python
>>> sorted(Product.objects.all())
```

> In real code, `Product.objects.order_by("price")` is better because the
> database does the sorting. This exercise is only for understanding `__lt__`.

## Warning: do not override `__init__` on a model

Django uses `__init__` to build objects from database rows. If you need custom
behaviour, override `save()` instead (see `02_save_method.md`).
