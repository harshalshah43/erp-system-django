conda info --envs
conda deactivate
conda create -n dj python=3.13
conda activate dj
python3 --version
pip3 --version
pip3 install Django
pip3 freeze > requirements.txt
django-admin startproject erp # --> manage.py and other project files created
cd erp
python3 manage.py runserver
python3 manage.py migrate
python3 manage.py createsuperuser
python3 manage.py startapp core # --> app folder and its files created
python3 manage.py makemigrations
python3 manage.py migrate
python3 manage.py sqlmigrate core 0001 # --> not mandatory, just to see the sql command.
[Action] In admin.py add 2 lines 
- from .models import Product
- admin.site.register(Product)

python3 manage.py shell
>>> Product.objects.create(name = 'Remote Control', description = 'Works with any smart TV', price = 100)
<Product: Product object (1)>
>>> Product.objects.all()
<QuerySet [<Product: Product object (1)>]>
>>> Products.objects.create(name = 'Samsung Smart TV 32 inches', description = 'New HD and 4K display', price = 200)
Traceback (most recent call last):
  File "<console>", line 1, in <module>
NameError: name 'Products' is not defined. Did you mean: 'Product'?
>>> Product.objects.create(name = 'Samsung Smart TV 32 inches', description = 'New HD and 4K display', price = 200)
<Product: Product object (2)>
>>> Product.objects.create(name = 'OTT Package', description = 'All packages for 2399.00', price = 2399)
<Product: Product object (3)>
>>> Product.objects.all()
<QuerySet [<Product: Product object (1)>, <Product: Product object (2)>, <Product: Product object (3)>]>