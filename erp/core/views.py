from django.shortcuts import render,redirect,get_object_or_404
from django.http import HttpResponse
import json
from django.core.paginator import Paginator
from django.db.models import Count, Exists, F, OuterRef, ProtectedError, Q, Sum, Window
from django.http import JsonResponse
from django.urls import reverse
from django.contrib import messages
from .models import Product, StockDocument, StockMove
from .forms import ProductForm
from .services import StockError, post_document


# products = [
#     {
#         'name':'Remote Control',
#         'description':'Works with any smart TV',
#         'price':100
#     },
#     {
#         'name':'Samsung Smart TV 32 inches',
#         'description':'Works with any smart TV',
#         'price':200
#     },
#     {
#         'name':'OTT Package',
#         'description':'All packages for 2399.00',
#         'price':2399
#     }
# ]


# Create your views here.
def home(request):
    products = Product.objects.filter(is_active=True)
    context = {
                'message':'Hi!! Kamakshi!',
                'subtext':'You are too early, the site is in construction',
                'title':'This is my Home Page',
                'products':products
              }
    return render(request,'core/home.html',context)
    # return HttpResponse('<h1>Hello World!!</h1>')

# Create your views here.
def about(request):
    return render(request,'core/about.html')

def add_product(request):
    form = ProductForm()
    if request.method == 'POST':
        form = ProductForm(request.POST)
        if form.is_valid():
            form.save()
            print('form saved')
            return redirect('home')
        else:
            print('form not saved, validation failed!!!!')
    context = {
        'form':form
    }
    return render(request,'core/product_form.html',context)

def edit_product(request,id):
    try:
        product = Product.objects.get(id = id)
        # product = get_object_or_404(Product,id = id) # PReferred alternative to try, except block
        form = ProductForm(instance = product)
        if request.method == 'POST':
            form = ProductForm(request.POST, instance = product)
            if form.is_valid():
                form.save()
                print('form saved')
                return redirect('home')
            else:
                print('form not saved, validation failed!!!!')
        context = {
            'form':form
        }
        return render(request,'core/product_form.html',context)
    except Exception as e:
        return render(request,'core/error.html',{'message':"Object does not exist"}) 

def delete_product(request,id):
    product = get_object_or_404(Product,id = id, is_active = True)
    if request.method == 'POST':
        try:
            product.delete()
        except ProtectedError:
            # Stock moves point at this product, and they are kept forever.
            product.is_active = False
            product.save(update_fields=['is_active'])
            messages.info(request, f"{product.name} has stock history, so it was archived instead of deleted.")
        return redirect('home')
    else:
        message = "Are you sure you wish to delete this product?"
        if product.moves.exists():
            message = f"{product.name} has stock history, so it will be archived (hidden) instead of deleted. Continue?"
        context = {
            'message':message,
            'product':product
        }
        return render(request,'core/delete_product_confirm.html',context)


def product_search(request):
    """JSON product list for the stock pages: filter by name/id, 15 per page."""
    q = request.GET.get('q', '').strip()
    try:
        page = max(1, int(request.GET.get('page', 1)))
    except ValueError:
        page = 1
    size = 15
    qs = Product.objects.filter(is_active=True)
    if q:
        cond = Q(name__icontains=q)
        if q.isdigit():
            cond |= Q(pk=int(q))
        qs = qs.filter(cond)
    # Fetch one extra row to know if there is a next page, without a COUNT query.
    rows = list(qs.order_by('name', 'pk')[(page - 1) * size:page * size + 1])
    results = [{'id': p.pk, 'name': p.name, 'stock': p.stock_quantity} for p in rows[:size]]
    return JsonResponse({'results': results, 'page': page, 'has_next': len(rows) > size})


def _transaction_line(line):
    """{product, type: IN|OUT, quantity} -> (product_id, signed quantity)"""
    qty = int(line['quantity'])
    if qty < 1:
        raise StockError("Quantities must be 1 or more.")
    if line['type'] not in ('IN', 'OUT'):
        raise StockError("Each line must be Add or Remove.")
    return int(line['product']), qty if line['type'] == 'IN' else -qty


def _stock_take_line(line):
    """{product, counted, expected} -> (product_id, counted - expected)

    `expected` is the stock the counter saw when they added the line. Posting
    the difference (rather than overwriting stock with the count) keeps any
    receipts or issues saved by someone else while the count was in progress.
    """
    counted = int(line['counted'])
    if counted < 0:
        raise StockError("Counted quantities can't be negative.")
    return int(line['product']), counted - int(line['expected'])


def _stock_page(request, kind, parse_line):
    """Shared GET/POST handling for the two cart-style stock pages.

    POST body is JSON {note, lines: [...]}; each line is parsed by parse_line.
    Lines with no change are dropped. Everything saves or nothing does.
    """
    take = kind == StockDocument.Kind.STOCK_TAKE
    if request.method != 'POST':
        return render(request, 'core/stock_cart.html', {
            'title': 'Stock Take' if take else 'Stock Transaction',
            'mode': 'take' if take else 'transaction',
        })
    try:
        data = json.loads(request.body)
        note = str(data.get('note', ''))[:255]
        lines = [parse_line(line) for line in data['lines']]
        if not lines:
            raise StockError("The list is empty. Pick items from the list on the right.")
        lines = [(pid, qty) for pid, qty in lines if qty]
        if lines:
            user = request.user if request.user.is_authenticated else None
            doc = post_document(kind, lines, note=note, user=user)
    except StockError as e:
        return JsonResponse({'error': str(e)}, status=400)
    except (ValueError, KeyError, TypeError, AttributeError):
        return JsonResponse({'error': "Invalid request."}, status=400)
    if not lines:
        messages.info(request, "Every count matched the stock on record, so nothing was adjusted.")
    else:
        messages.success(request, f"{doc} saved.")
    return JsonResponse({'redirect': reverse('home')})


def stock_transaction(request):
    return _stock_page(request, StockDocument.Kind.TRANSACTION, _transaction_line)


def stock_take(request):
    return _stock_page(request, StockDocument.Kind.STOCK_TAKE, _stock_take_line)


def product_history(request, id):
    """Every stock move for one product, newest first, with the balance after each."""
    product = get_object_or_404(Product, id=id)
    moves = (
        StockMove.objects.filter(product=product)
        .select_related('document', 'document__created_by')
        # Running total from the oldest move = stock after that move.
        .annotate(balance=Window(Sum('quantity'), order_by=[F('document_id').asc(), F('pk').asc()]))
        .order_by('-document_id', '-pk')
    )
    page = Paginator(moves, 25).get_page(request.GET.get('page'))
    return render(request, 'core/product_history.html', {'product': product, 'page': page})


DIRECTIONS = {'in': 'Incoming', 'out': 'Outgoing'}


def document_list(request):
    """All stock documents, filterable by direction (incoming/outgoing) and kind."""
    direction = request.GET.get('direction', '')
    kind = request.GET.get('kind', '')
    docs = StockDocument.objects.select_related('created_by')
    # Exists() rather than filter(lines__...) so the totals below still count every line.
    if direction == 'in':
        docs = docs.filter(Exists(StockMove.objects.filter(document=OuterRef('pk'), quantity__gt=0)))
    elif direction == 'out':
        docs = docs.filter(Exists(StockMove.objects.filter(document=OuterRef('pk'), quantity__lt=0)))
    if kind in StockDocument.Kind.values:
        docs = docs.filter(kind=kind)
    docs = docs.annotate(
        line_count=Count('lines'),
        total_in=Sum('lines__quantity', filter=Q(lines__quantity__gt=0)),
        total_out=Sum('lines__quantity', filter=Q(lines__quantity__lt=0)),
    ).order_by('-created_at', '-pk')  # Meta.ordering is dropped for grouped queries
    page = Paginator(docs, 25).get_page(request.GET.get('page'))
    return render(request, 'core/document_list.html', {
        'page': page,
        'direction': direction if direction in DIRECTIONS else '',
        'directions': DIRECTIONS,
        'kind': kind,
        'kinds': StockDocument.Kind.choices,
    })


def document_detail(request, id):
    doc = get_object_or_404(StockDocument.objects.select_related('created_by', 'reverses'), id=id)
    reversed_by = StockDocument.objects.filter(reverses=doc).first()
    lines = doc.lines.select_related('product').order_by('pk')
    return render(request, 'core/document_detail.html', {
        'doc': doc, 'lines': lines, 'reversed_by': reversed_by,
    })
