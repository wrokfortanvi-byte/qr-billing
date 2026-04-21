from django.contrib import admin
from .models import Bill, BillItem

class BillItemInline(admin.TabularInline):
    model = BillItem
    extra = 1

@admin.register(Bill)
class BillAdmin(admin.ModelAdmin):
    list_display = ('id', 'customer', 'date', 'total_amount')
    inlines = [BillItemInline]

admin.site.register(BillItem)