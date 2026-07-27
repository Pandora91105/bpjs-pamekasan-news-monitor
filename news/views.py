from django.contrib.auth.views import LoginView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView, View
from django.shortcuts import redirect, get_object_or_404
from .models import News
from datetime import datetime, timedelta
from django.utils import timezone
from django.db.models import Count, Q
from django.db.models.functions import TruncMonth
from django.core.management import call_command
from django.http import HttpResponse
from django.views import View
from django.utils.html import strip_tags
import os
import threading
import json
import calendar     
import html as html_module
from django.core.paginator import Paginator

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

        berita_terbaru = list(approved_news.filter(published_date__gte=cutoff).order_by('published_date'))
        berita_sebelumnya = list(approved_news.filter(published_date__lt=cutoff).order_by('-published_date'))

        for news in berita_terbaru + berita_sebelumnya:
            news.snippet_bersih = html_module.unescape(strip_tags(news.snippet))[:200]

        context['berita_terbaru'] = berita_terbaru
        context['berita_sebelumnya'] = berita_sebelumnya

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

        all_news_sorted = all_news.order_by('-published_date')
        paginator = Paginator(all_news_sorted, 10)
        page_number = self.request.GET.get('page', 1)
        page_obj = paginator.get_page(page_number)

        context['news_list'] = page_obj
        context['filter_aktif'] = filter_sentiment

        # Data untuk dropdown filter (bulan & tahun yang tersedia)
        context['bulan_list'] = [
            (1, 'Januari'), (2, 'Februari'), (3, 'Maret'), (4, 'April'),
            (5, 'Mei'), (6, 'Juni'), (7, 'Juli'), (8, 'Agustus'),
            (9, 'September'), (10, 'Oktober'), (11, 'November'), (12, 'Desember'),
        ]

        tahun_tersedia = News.objects.filter(is_relevant=True).dates('published_date', 'year')
        context['tahun_list'] = sorted(set(d.year for d in tahun_tersedia), reverse=True)

        # Ambil parameter filter dari URL, default 6 bulan terakhir
        today = timezone.now()
        default_start = today - timedelta(days=180)

        start_month = int(self.request.GET.get('start_month', default_start.month))
        start_year = int(self.request.GET.get('start_year', default_start.year))
        end_month = int(self.request.GET.get('end_month', today.month))
        end_year = int(self.request.GET.get('end_year', today.year))

        context['selected_start_month'] = start_month
        context['selected_start_year'] = start_year
        context['selected_end_month'] = end_month
        context['selected_end_year'] = end_year

        # Hitung tanggal awal & akhir rentang filter
        range_start = datetime(start_year, start_month, 1, tzinfo=timezone.get_current_timezone())
        last_day = calendar.monthrange(end_year, end_month)[1]
        range_end = datetime(end_year, end_month, last_day, 23, 59, 59, tzinfo=timezone.get_current_timezone())

        # Query data per bulan dalam rentang tersebut
        monthly_data = (
            News.objects.filter(is_relevant=True, published_date__gte=range_start, published_date__lte=range_end)
            .annotate(month=TruncMonth('published_date'))
            .values('month')
            .annotate(
                positif=Count('id', filter=Q(sentiment='positif')),
                negatif=Count('id', filter=Q(sentiment='negatif')),
            )
            .order_by('month')
        )

        chart_labels = []
        chart_positif = []
        chart_negatif = []
        bulan_singkat = ['Jan', 'Feb', 'Mar', 'Apr', 'Mei', 'Jun', 'Jul', 'Agu', 'Sep', 'Okt', 'Nov', 'Des']

        for item in monthly_data:
            bulan_label = f"{bulan_singkat[item['month'].month - 1]} {item['month'].year}"
            chart_labels.append(bulan_label)
            chart_positif.append(item['positif'])
            chart_negatif.append(item['negatif'])

        context['chart_labels'] = json.dumps(chart_labels)
        context['chart_positif'] = json.dumps(chart_positif)
        context['chart_negatif'] = json.dumps(chart_negatif)

        context['sumber_stats'] = (
            News.objects.filter(is_relevant=True)
            .values('source')
            .annotate(jumlah=Count('id'))
            .order_by('-jumlah')
        )

        return context

class TriggerFetchView(View):
    def get(self, request):
        token = request.GET.get('token')
        expected_token = os.getenv('FETCH_SECRET_TOKEN')

        if not expected_token or token != expected_token:
            return HttpResponse('Unauthorized', status=401)

        try:
            def run_fetch():
                try:
                    call_command('fetch_news')
                except Exception as e:
                    print(f"ERROR saat menjalankan fetch_news di background: {e}")
                    import traceback
                    traceback.print_exc()

            thread = threading.Thread(target=run_fetch)
            thread.start()

            return HttpResponse('Fetch dimulai di background.')
        except Exception as e:
            print(f"ERROR di TriggerFetchView: {e}")
            import traceback
            traceback.print_exc()
            return HttpResponse(f'Error: {e}', status=500)