from django.contrib import admin
from .models import News
from .models import SocialMediaPost

@admin.register(News)
class NewsAdmin(admin.ModelAdmin):
    list_display = ('title', 'source', 'published_date', 'is_relevant', 'status')
    list_filter = ('status', 'is_relevant', 'source')
    search_fields = ('title', 'snippet')


@admin.register(SocialMediaPost)
class SocialMediaPostAdmin(admin.ModelAdmin):
    list_display = ('platform', 'username', 'sentiment', 'posted_date', 'likes_count', 'is_dummy')
    list_filter = ('platform', 'sentiment', 'is_dummy')
    search_fields = ('username', 'caption')