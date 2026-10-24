from django.shortcuts import render
from django.http import HttpResponse

products = [
    {
        'name':'Remote Control',
        'description':'Works with any smart TV',
        'price':100
    },
    {
        'name':'Samsung Smart TV 32 inches',
        'description':'Works with any smart TV',
        'price':200
    },
    {
        'name':'OTT Package',
        'description':'All packages for 2399.00',
        'price':2399
    }
]


# Create your views here.
def home(request):
    context = {
                'message':'Hi!! Kamakshi!',
                'subtext':'You are too early, the site is in construction',
                'title':'This is my Home Page',
                'products':products
              }
    return render(request,'core/home.html',context)
    # return HttpResponse('<h1>Hello World!!</h1>')

# Create your views here.
def about(requests):
    return HttpResponse('<h1>Hello World!! This is my About Page</h1>')
