from django.shortcuts import render,redirect,get_object_or_404
from django.http import HttpResponse
from .models import Product
from .forms import ProductForm


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
    product.delete()
    return redirect('home')
