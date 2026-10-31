from django.urls import path
from .views import home,about,add_product,edit_product

urlpatterns = [
    path('home/',home,name = 'home'),
    path('about/',about,name = 'about'),
    path('add-product/',add_product,name = 'add-product'),
    path('edit-product/<int:id>/',edit_product,name = 'edit-product')
]