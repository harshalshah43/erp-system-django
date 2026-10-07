from django.shortcuts import render
from django.http import HttpResponse


# Create your views here.
def home(request):
    context = {
                'message':'Hi!! Kamakshi!',
                'subtext':'You are too early, the site is in construction'
              }
    return render(request,'core/home.html',context)
    # return HttpResponse('<h1>Hello World!!</h1>')

# Create your views here.
def about(requests):
    return HttpResponse('<h1>Hello World!! This is my About Page</h1>')
