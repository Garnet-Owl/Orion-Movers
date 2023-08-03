from django.contrib import admin

# Register your models here.
from django.contrib import admin
from .models import CustomUser, Mover, Customer, Order, Rating

class CustomUserAdmin(admin.ModelAdmin):
    list_display = ('username', 'email', 'phone_number')
    # Add any other fields you want to display in the admin list view
    # For more customization options, refer to the Django documentation: https://docs.djangoproject.com/en/stable/ref/contrib/admin/

class MoverAdmin(admin.ModelAdmin):
    list_display = ('user', 'vehicle', 'identity_verified', 'background_check', 'rating')
    list_filter = ('identity_verified', 'background_check')
    search_fields = ('user__username', 'user__email', 'vehicle')
    # Add any other fields you want to display and filter in the admin list view

class CustomerAdmin(admin.ModelAdmin):
    list_display = ('user', 'location')
    # Add any other fields you want to display in the admin list view

class OrderAdmin(admin.ModelAdmin):
    list_display = ('customer', 'mover', 'start_address', 'end_address', 'start_time', 'end_time', 'total_cost', 'status')
    list_filter = ('status',)
    search_fields = ('customer__user__username', 'mover__user__username', 'start_address', 'end_address')
    # Add any other fields you want to display and filter in the admin list view

class RatingAdmin(admin.ModelAdmin):
    list_display = ('user', 'mover', 'score', 'comment')
    list_filter = ('score',)
    search_fields = ('user__username', 'mover__user__username', 'comment')
    # Add any other fields you want to display and filter in the admin list view

# Register the models with the customized admin classes
admin.site.register(CustomUser, CustomUserAdmin)
admin.site.register(Mover, MoverAdmin)
admin.site.register(Customer, CustomerAdmin)
admin.site.register(Order, OrderAdmin)
admin.site.register(Rating, RatingAdmin)
