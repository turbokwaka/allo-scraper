from load_django import *
from parser_app.models import Category

categories = Category.objects.all()
for category in categories:
    category.status = "New"
    category.save()
    print(f"Category '{category.name}' status reset to 'New'")
