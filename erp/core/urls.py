from django.urls import path
from .views import home,about,add_product,edit_product,delete_product,stock_transaction,stock_take,product_search

urlpatterns = [
    path('home/',home,name = 'home'),
    path('about/',about,name = 'about'),
    path('add-product/',add_product,name = 'add-product'),
    path('edit-product/<int:id>/',edit_product,name = 'edit-product'),
    path('delete-product/<int:id>/',delete_product,name = 'delete-product'),
    path('stock-transaction/',stock_transaction,name = 'stock-transaction'),
    path('product-search/',product_search,name = 'product-search'),
    path('stock-take/',stock_take,name = 'stock-take'),

]