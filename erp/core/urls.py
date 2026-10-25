from django.urls import path
from .views import home,about,add_product

urlpatterns = [
    path('home/',home,name = 'home'),
    path('about/',about),
    path('add-product/',add_product,name = 'add-product')
]