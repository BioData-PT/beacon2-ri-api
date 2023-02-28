# importing the function from utils
from django.core.management.utils import get_random_secret_key

# generating and printing the SECRET_KEY
print("Copy the key below, put in the SECRET_KEY assign on secret.py.example and move it to secret.py")
print(get_random_secret_key())


