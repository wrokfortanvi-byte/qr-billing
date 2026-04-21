from django.contrib import admin
from .models import Product

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ['id', 'product_id', 'name', 'category', 'hsn_code', 'price', 'gst_rate', 'stock', 'unit']
    search_fields = ['product_id', 'name', 'category']
    list_filter = ['category', 'unit']