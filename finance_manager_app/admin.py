from django.contrib import admin
from . import models

# Register your models here.

admin.site.register(models.Transaction)
admin.site.register(models.Monthly_budget)
admin.site.register(models.Recurring_bill)
admin.site.register(models.CategoryModel)

@admin.register(models.CustomUserModel)
class CustomUserAdmin(admin.ModelAdmin):
    list_display = ('id', 'email')
    list_filter = ('id', 'email')
    search_fields = ('id', 'email')
