from django.contrib.auth.views import LoginView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView, View
from django.shortcuts import redirect, get_object_or_404
from django.utils import timezone
from .models import News
from django.utils import timezone
from datetime import timedelta

class CustomLoginView(LoginView):
    template_name = 'login.html'
    redirect_authenticated_user = True


class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'dashboard.html'
    login_url = 'login'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        approved_news = News.objects.filter(is_relevant=True)

        cutoff = timezone.now() - timedelta(days=7)

        context['berita_terbaru'] = approved_news.filter(
            published_date__gte=cutoff
        ).order_by('published_date')

        context['berita_sebelumnya'] = approved_news.filter(
            published_date__lt=cutoff
        ).order_by('-published_date')   

        return context



    


class AnalisisView(LoginRequiredMixin, TemplateView):
    template_name = 'analisis.html'
    login_url = 'login'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        all_news = News.objects.filter(is_relevant=True)

        context['total_positif'] = all_news.filter(sentiment='positif').count()
        context['total_negatif'] = all_news.filter(sentiment='negatif').count()
        context['total_semua'] = all_news.count()

        total = context['total_semua']
        context['persen_positif'] = round((context['total_positif'] / total) * 100) if total else 0
        context['persen_negatif'] = round((context['total_negatif'] / total) * 100) if total else 0

        context['berita_negatif_terbaru'] = all_news.filter(sentiment='negatif').order_by('-published_date').first()

        filter_sentiment = self.request.GET.get('sentiment', 'semua')
        if filter_sentiment != 'semua':
            all_news = all_news.filter(sentiment=filter_sentiment)

        context['news_list'] = all_news.order_by('-published_date')
        context['filter_aktif'] = filter_sentiment

        return context