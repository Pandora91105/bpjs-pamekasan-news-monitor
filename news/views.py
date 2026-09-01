import os
import threading
import json
import calendar     
import html as html_module
import re
import bisect

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
from django.core.paginator import Paginator
from django.views import View
from django.http import JsonResponse
from .models import SocialMediaPost
from collections import Counter
from datetime import date
from django.db.models.functions import TruncDate



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

        sumber_stats_all = (
            News.objects.filter(is_relevant=True)
            .values('source')
            .annotate(jumlah=Count('id'))
            .order_by('-jumlah')
        )
        sumber_paginator = Paginator(sumber_stats_all, 8)
        sumber_page_number = self.request.GET.get('sumber_page', 1)
        context['sumber_stats'] = sumber_paginator.get_page(sumber_page_number)

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

class MarkNotificationsReadView(LoginRequiredMixin, View):
    def post(self, request):
        News.objects.filter(sentiment='negatif', notif_read=False).update(notif_read=True)
        return JsonResponse({'status': 'ok'})

TOPIC_KEYWORDS = {
    'Pelayanan': ['pelayanan', 'petugas', 'ramah', 'pegawai'],
    'Antrean': ['antre', 'antrian', 'loket'],
    'Klaim': ['klaim', 'cair', 'ditolak'],
    'Kepesertaan': ['kartu', 'peserta', 'nonaktif'],
    'Digitalisasi': ['online', 'mobile jkn', 'daftar online'],
    'Sosialisasi': ['sosialisasi', 'edukasi'],
    'Program': ['program', 'layanan sabtu'],
    'Fasilitas': ['kantor', 'rsud', 'fasilitas'],
}

STOPWORDS = {
    'yang', 'dan', 'di', 'ke', 'dari', 'untuk', 'pada', 'ini', 'itu', 'dengan',
    'tidak', 'ada', 'sudah', 'saya', 'kami', 'kita', 'akan', 'bisa', 'juga',
    'atau', 'saja', 'lagi', 'masih', 'sangat', 'sekarang', 'karena', 'kalau',
    'jadi', 'harus', 'padahal', 'banget', 'nih', 'dong', 'gak', 'tak', 'apa',
    'kok', 'ya', 'guys', 'para',
}


def detect_topics(caption):
    caption_lower = caption.lower()
    matched = [topic for topic, keywords in TOPIC_KEYWORDS.items()
            if any(kw in caption_lower for kw in keywords)]
    return matched if matched else ['Lainnya']


def extract_keywords(posts, top_n=10):
    words = []
    for post in posts:
        text = re.sub(r'#\w+', '', post.caption.lower())
        text = re.sub(r'[^\w\s]', ' ', text)
        words.extend([w for w in text.split() if len(w) > 3 and w not in STOPWORDS])
    return Counter(words).most_common(top_n)


def compute_priority_map(negatif_posts):
    if not negatif_posts:
        return {}
    engagements = sorted([p.likes_count + p.comments_count for p in negatif_posts])
    n = len(engagements)
    result = {}
    for p in negatif_posts:
        eng = p.likes_count + p.comments_count
        pct = bisect.bisect_right(engagements, eng) / n
        if pct >= 0.67:
            result[p.id] = 'HIGH'
        elif pct >= 0.33:
            result[p.id] = 'MEDIUM'
        else:
            result[p.id] = 'LOW'
    return result


class SocialMediaView(LoginRequiredMixin, TemplateView):
    template_name = 'social_media.html'
    login_url = 'login'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        params = self.request.GET

        # ---------- 1. Filter Periode ----------
        period = params.get('period', '30hari')
        today = timezone.now().date()

        if period == 'hari_ini':
            start_date = today
            end_date = today
        elif period == '7hari':
            start_date = today - timedelta(days=6)
            end_date = today
        elif period == 'bulan_ini':
            start_date = today.replace(day=1)
            end_date = today
        elif period == 'bulan_lalu':
            first_this_month = today.replace(day=1)
            last_month_end = first_this_month - timedelta(days=1)
            start_date = last_month_end.replace(day=1)
            end_date = last_month_end
        elif period == 'custom':
            try:
                start_date = datetime.strptime(params.get('start_date'), '%Y-%m-%d').date()
                end_date = datetime.strptime(params.get('end_date'), '%Y-%m-%d').date()
            except (ValueError, TypeError):
                start_date = today - timedelta(days=29)
                end_date = today
        else:  # default 30 hari
            start_date = today - timedelta(days=29)
            end_date = today

        period_length = (end_date - start_date).days + 1
        prev_start = start_date - timedelta(days=period_length)
        prev_end = start_date - timedelta(days=1)

        base_qs = SocialMediaPost.objects.filter(
            posted_date__date__gte=start_date, posted_date__date__lte=end_date
        )
        prev_qs = SocialMediaPost.objects.filter(
            posted_date__date__gte=prev_start, posted_date__date__lte=prev_end
        )

        # ---------- 2. Filter Platform & Sentimen ----------
        platform_filter = params.get('platform', 'semua')
        sentiment_filter = params.get('sentiment', 'semua')

        if platform_filter != 'semua':
            base_qs = base_qs.filter(platform=platform_filter)
        if sentiment_filter != 'semua':
            base_qs = base_qs.filter(sentiment=sentiment_filter)

        all_posts = list(base_qs)

        # ---------- 3. Deteksi Topic per Post (runtime) ----------
        for post in all_posts:
            post.topics = detect_topics(post.caption)
            post.engagement = post.likes_count + post.comments_count

        # ---------- 4. Filter Topic (setelah deteksi) ----------
        topic_filter = params.get('topic', 'semua')
        if topic_filter != 'semua':
            all_posts = [p for p in all_posts if topic_filter in p.topics]

        # ---------- 5. Priority (hanya untuk post negatif) ----------
        negatif_posts_all = [p for p in all_posts if p.sentiment == 'negatif']
        priority_map = compute_priority_map(negatif_posts_all)
        for post in all_posts:
            post.priority = priority_map.get(post.id, None)

        priority_filter = params.get('priority', 'semua')
        if priority_filter != 'semua':
            all_posts = [p for p in all_posts if p.priority == priority_filter]

        # ---------- 6. KPI ----------
        total_posts = len(all_posts)
        total_positif = len([p for p in all_posts if p.sentiment == 'positif'])
        total_negatif = len([p for p in all_posts if p.sentiment == 'negatif'])
        total_engagement = sum(p.engagement for p in all_posts)
        avg_engagement = round(total_engagement / total_posts) if total_posts else 0

        context.update({
            'total_posts': total_posts,
            'total_positif': total_positif,
            'total_negatif': total_negatif,
            'total_engagement': total_engagement,
            'avg_engagement': avg_engagement,
        })

        # ---------- 7. Sentiment Trend (harian) ----------
        trend_map = {}
        for post in all_posts:
            d = post.posted_date.date().isoformat()
            trend_map.setdefault(d, {'positif': 0, 'negatif': 0})
            trend_map[d][post.sentiment] += 1
        trend_dates = sorted(trend_map.keys())
        context['trend_labels'] = json.dumps(trend_dates)
        context['trend_positif'] = json.dumps([trend_map[d]['positif'] for d in trend_dates])
        context['trend_negatif'] = json.dumps([trend_map[d]['negatif'] for d in trend_dates])

        # ---------- 8. Platform Comparison ----------
        platform_stats = {}
        for plat in ['instagram', 'tiktok']:
            posts_p = [p for p in all_posts if p.platform == plat]
            platform_stats[plat] = {
                'total': len(posts_p),
                'positif': len([p for p in posts_p if p.sentiment == 'positif']),
                'negatif': len([p for p in posts_p if p.sentiment == 'negatif']),
                'likes': sum(p.likes_count for p in posts_p),
                'comments': sum(p.comments_count for p in posts_p),
                'engagement': sum(p.engagement for p in posts_p),
            }
        context['platform_stats'] = platform_stats

        # ---------- 9. Topic & Issue Analysis ----------
        topic_stats = {}
        for post in all_posts:
            for t in post.topics:
                topic_stats.setdefault(t, {'total': 0, 'negatif': 0, 'engagement': 0})
                topic_stats[t]['total'] += 1
                topic_stats[t]['engagement'] += post.engagement
                if post.sentiment == 'negatif':
                    topic_stats[t]['negatif'] += 1

        context['topic_list'] = sorted(topic_stats.keys())
        context['topic_stats'] = sorted(
            [{'name': k, **v} for k, v in topic_stats.items()],
            key=lambda x: x['total'], reverse=True
        )

        top_issues = sorted(
            [{'name': k, **v} for k, v in topic_stats.items() if v['negatif'] > 0],
            key=lambda x: (x['negatif'], x['engagement']), reverse=True
        )[:5]
        context['top_issues'] = top_issues

        # ---------- 10. Engagement Analysis ----------
        context['top_posts_engagement'] = sorted(all_posts, key=lambda p: p.engagement, reverse=True)[:5]
        context['top_negatif_posts'] = sorted(
            [p for p in all_posts if p.sentiment == 'negatif'], key=lambda p: p.engagement, reverse=True
        )[:5]
        context['top_positif_posts'] = sorted(
            [p for p in all_posts if p.sentiment == 'positif'], key=lambda p: p.engagement, reverse=True
        )[:5]

        # ---------- 11. Top Accounts ----------
        account_stats = {}
        for post in all_posts:
            key = (post.username, post.platform)
            account_stats.setdefault(key, {'total': 0, 'engagement': 0, 'positif': 0, 'negatif': 0})
            account_stats[key]['total'] += 1
            account_stats[key]['engagement'] += post.engagement
            account_stats[key][post.sentiment] += 1

        top_accounts = sorted(
            [{'username': k[0], 'platform': k[1], **v} for k, v in account_stats.items()],
            key=lambda x: x['engagement'], reverse=True
        )[:5]
        for acc in top_accounts:
            acc['dominan'] = 'positif' if acc['positif'] >= acc['negatif'] else 'negatif'
        context['top_accounts'] = top_accounts

        # ---------- 11b. Data lengkap semua post (untuk detail akun via JS) ----------
        all_posts_data = []
        for p in all_posts:
            all_posts_data.append({
                'username': p.username,
                'platform_display': p.get_platform_display(),
                'caption': p.caption,
                'sentiment': p.sentiment,
                'sentiment_display': p.get_sentiment_display(),
                'likes': p.likes_count,
                'comments': p.comments_count,
                'engagement': p.engagement,
                'posted_date': p.posted_date.strftime('%d %b %Y'),
                'post_url': p.post_url if p.post_url else '',
                'topics': p.topics,
            })
        context['all_posts_data'] = all_posts_data

        # ---------- 12. Keyword Analysis ----------
        context['top_keywords'] = extract_keywords(all_posts, 10)
        context['keywords_positif'] = extract_keywords([p for p in all_posts if p.sentiment == 'positif'], 8)
        context['keywords_negatif'] = extract_keywords([p for p in all_posts if p.sentiment == 'negatif'], 8)

        # ---------- 13. Alerts ----------
        alerts = []
        high_priority_posts = [p for p in all_posts if p.priority == 'HIGH']
        if high_priority_posts:
            alerts.append({
                'type': 'high_priority',
                'message': f"Ada {len(high_priority_posts)} postingan negatif dengan engagement tinggi yang perlu perhatian segera."
            })

        prev_negatif_count = prev_qs.filter(sentiment='negatif').count()
        if prev_negatif_count > 0 and total_negatif > prev_negatif_count * 1.5:
            kenaikan = round(((total_negatif - prev_negatif_count) / prev_negatif_count) * 100)
            alerts.append({
                'type': 'sentiment_spike',
                'message': f"Postingan negatif naik {kenaikan}% dibanding periode sebelumnya ({prev_negatif_count} → {total_negatif})."
            })

        context['alerts'] = alerts

        # ---------- 14. Pagination Post List ----------
        posts_sorted = sorted(all_posts, key=lambda p: p.posted_date, reverse=True)
        paginator = Paginator(posts_sorted, 10)
        page_number = params.get('page', 1)
        context['posts'] = paginator.get_page(page_number)

        # ---------- 15. Filter aktif (untuk template) ----------
        context.update({
            'period_aktif': period,
            'platform_aktif': platform_filter,
            'sentiment_aktif': sentiment_filter,
            'topic_aktif': topic_filter,
            'priority_aktif': priority_filter,
            'start_date': start_date.isoformat(),
            'end_date': end_date.isoformat(),
        })

        return context