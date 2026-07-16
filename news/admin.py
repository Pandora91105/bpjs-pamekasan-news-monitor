from django.contrib import admin
from .models import News

@admin.register(News)
class NewsAdmin(admin.ModelAdmin):
    list_display = ('title', 'source', 'published_date', 'is_relevant', 'status')
    list_filter = ('status', 'is_relevant', 'source')
    search_fields = ('title', 'snippet')