from .models import News


def notifications(request):
    if not request.user.is_authenticated:
        return {}

    negative_news = News.objects.filter(
        sentiment='negatif', is_relevant=True
    ).order_by('-published_date')

    return {
        'notif_count': negative_news.filter(notif_read=False).count(),
        'notif_list': negative_news[:10],
    }
