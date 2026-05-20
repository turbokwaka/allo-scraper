from django.contrib import admin
from .models import Product

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = (
        'name', 'brand', 'category', 'status', 'availabily', 'old_price', 'current_price', 'discount_percent', 'created_at'
    )
    list_filter = ('status', 'availabily', 'category', 'brand')
    search_fields = ('name', 'brand', 'sku', 'url')
    ordering = ['-created_at']
