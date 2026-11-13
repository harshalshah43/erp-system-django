from django.shortcuts import render,redirect,get_object_or_404
from django.http import HttpResponse
import json
from django.db import transaction
from django.db.models import Q
from django.http import JsonResponse
from django.urls import reverse
from django.contrib import messages
from .models import Product, StockDocument
from .forms import ProductForm, StockTakeForm


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
    products = Product.objects.all()
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
    except Exception as e:
        return render(request,'core/error.html',{'message':"Object does not exist"}) 

def delete_product(request,id):
    product = get_object_or_404(Product,id = id)
    if request.method == 'POST':
        product.delete()
        return redirect('home')
    else:
        message = "Are you sure you wish to delete this product?"
        context = {
            'message':message,
            'product':product
        }
        return render(request,'core/delete_product_confirm.html',context)


def product_search(request):
    """JSON product list for the cart page: filter by name/id, 15 per page."""
    q = request.GET.get('q', '').strip()
    try:
        page = max(1, int(request.GET.get('page', 1)))
    except ValueError:
        page = 1
    size = 15
    qs = Product.objects.all()
    if q:
        cond = Q(name__icontains=q)
        if q.isdigit():
            cond |= Q(pk=int(q))
        qs = qs.filter(cond)
    rows = list(qs.order_by('name', 'pk')[(page - 1) * size:page * size + 1])
    results = [{'id': p.pk, 'name': p.name, 'stock': p.stock_quantity} for p in rows[:size]]
    return JsonResponse({'results': results, 'page': page, 'has_next': len(rows) > size})

def stock_transaction(request):
    """Cart-style page; POST is JSON {note, lines:[{product, type, quantity}]}.
    All lines save or none do."""
    if request.method != 'POST':
        return render(request, 'core/stock_transaction.html')
    try:
        data = json.loads(request.body)
        lines = [(int(l['product']), l['type'], int(l['quantity'])) for l in data['lines']]
        if not lines or any(t not in ('IN', 'OUT') or q < 1 for _, t, q in lines):
            raise ValueError("Add at least one item with a quantity of 1 or more.")
        note = str(data.get('note', ''))[:255]
        # Incoming first so a receipt and an issue in the same cart can offset.
        lines.sort(key=lambda l: l[1] != 'IN')
        with transaction.atomic():
            for pid, t, q in lines:
                StockDocument.objects.create(product_id=pid, doc_type=t, quantity=q, note=note)
    except (ValueError, KeyError, TypeError) as e:
        return JsonResponse({'error': str(e) or "Invalid request."}, status=400)
    except Product.DoesNotExist:
        return JsonResponse({'error': "Unknown product in cart."}, status=400)
    messages.success(request, "Stock transaction saved.")
    return JsonResponse({'redirect': reverse('home')})

def stock_take(request):
    """Enter counted quantities; differences become IN/OUT documents."""
    form = StockTakeForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        with transaction.atomic():
            for p in form.products:
                diff = form.cleaned_data[f"p{p.pk}"] - p.stock_quantity
                if diff:
                    StockDocument.objects.create(
                        product=p,
                        doc_type=StockDocument.INCOMING if diff > 0 else StockDocument.OUTGOING,
                        quantity=abs(diff),
                        note="Stock take adjustment",
                    )
        messages.success(request, "Stock take saved.")
        return redirect('home')
    return render(request, 'core/stock_take.html', {'form': form})
