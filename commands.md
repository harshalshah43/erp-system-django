conda info --envs
conda deactivate
conda create -n dj python=3.13
conda activate dj
python3 --version
pip3 --version
pip3 install Django
pip3 freeze > requirements.txt
django-admin startproject erp
cd erp
python3 manage.py runserver
python3 manage.py migrate
python3 manage.py createsuperuser
python3 manage.py startapp core