from django.db import models

class Category(models.Model):
    STATUS_TYPES = [
        ("New", "New"),
        ("Done", "Done"),
    ]
    name = models.CharField(max_length=255, unique=True, verbose_name="Назва категорії")
    link = models.URLField(max_length=1000, verbose_name="Посилання на категорію", blank=True, null=True)
    status = models.CharField(max_length=50, verbose_name="Статус категорії", default="New", choices=STATUS_TYPES)


    class Meta:
        verbose_name = "Категорія"
        verbose_name_plural = "Категорії"
        ordering = ['name']

    def __str__(self):
        return self.name


class Product(models.Model):
    STATUS_TYPES = [
        ("Pending", "Pending"),
        ("Processed", "Processed"),
        ("Error", "Error"),
    ]
    AVAILABILITY_TYPES = [
        ("InStock", "In Stock"),
        ("LimitedAvailability", "Limited Availability"),
    ]

    # Основна інформація
    status = models.CharField(max_length=50, verbose_name="Статус товару", default="Pending", choices=STATUS_TYPES)
    site_name = models.CharField(max_length=255, verbose_name="Сайт", default="allo.ua")
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='products', verbose_name="Категорія")
    brand = models.CharField(max_length=255, verbose_name="Бренд")
    name = models.CharField(max_length=500, verbose_name="Назва товару")
    url = models.URLField(max_length=1000, verbose_name="Посилання", unique=True)
    sku = models.CharField(max_length=100, verbose_name="Артикул (SKU)", blank=True, null=True)
    availabily = models.CharField(max_length=50, verbose_name="Наявність", choices=AVAILABILITY_TYPES, default="InStock")

    # Ціни та знижки (використовуємо DecimalField для точних фінансових розрахунків)
    old_price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Ціна до знижки")
    current_price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Ціна зі знижкою")
    discount_percent = models.DecimalField(max_digits=5, decimal_places=2, verbose_name="% знижки")
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Сума знижки")

    # Вся інша специфічна інформація (характеристики, наявність тощо)
    additional_info = models.JSONField(verbose_name="Додаткова інформація", blank=True, default=dict)

    # Системні поля
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Додано до БД")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Оновлено")

    class Meta:
        verbose_name = "Товар"
        verbose_name_plural = "Товари"
        ordering = ['-discount_percent']  # За замовчуванням сортуємо від найбільшої знижки

    def __str__(self):
        return f"{self.brand} {self.name} (-{self.discount_percent}%)"