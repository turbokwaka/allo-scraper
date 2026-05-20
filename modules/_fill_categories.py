from load_django import *
from parser_app.models import Category

categories = [
    {"name": "Холодильники", "link": "https://allo.ua/ua/holodilniki/action-da/discount-da/seller-allo/"},
    {"name": "Телевізори", "link": "https://allo.ua/ua/televizory/action-da/discount-da/seller-allo/"},
    {"name": "Пральні машини", "link": "https://allo.ua/ua/stiralnye-mashiny/action-da/discount-da/seller-allo/"},
    {"name": "Мікрохвильовки", "link": "https://allo.ua/ua/products/mikrovolnovki/action-da/discount-da/seller-allo/"},
    {"name": "Смартфони",
     "link": "https://allo.ua/ua/products/mobile/action-da/discount-da/klass-kommunikator_smartfon/seller-allo/"},
    {"name": "Планшети", "link": "https://allo.ua/ua/products/internet-planshety/action-da/discount-da/seller-allo/"},
    {"name": "Ноутбуки", "link": "https://allo.ua/ua/products/notebooks/action-da/discount-da/seller-allo/"},
    {"name": "Навушники", "link": "https://allo.ua/ua/naushniki/action-da/discount-da/seller-allo/"},
]

for category_data in categories:
    # get_or_create повертає кортеж (об'єкт, булеве_значення_чи_був_створений)
    category, created = Category.objects.get_or_create(
        name=category_data["name"],
        defaults={
            "link": category_data["link"]
        }
    )

    if created:
        print(f"Створено нову категорію: {category.name}")
    else:
        print(f"Категорія вже існує: {category.name}")

print("Оновлення бази даних завершено!")