from django.contrib import admin
from .models import Integration

@admin.register(Integration)
class IntegrationAdmin(admin.ModelAdmin):
    list_display = ('id', 'get_user_name', 'type', 'is_active')  # Show customer name
    list_filter = ('type', 'is_active')
    search_fields = ('user__username', 'user__first_name', 'user__last_name', 'type')
    list_editable = ('is_active',)
    ordering = ('user__username', 'type')

    # Custom method to display the user's name
    def get_user_name(self, obj):
        # Return full name if available, else username
        full_name = f"{obj.user.first_name} {obj.user.last_name}".strip()
        return full_name if full_name else obj.user.username
    get_user_name.short_description = 'Customer Name'
    get_user_name.admin_order_field = 'user__username'  # Allows sorting by username