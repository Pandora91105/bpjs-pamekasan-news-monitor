import re
import time
import requests
from django.core.management.base import BaseCommand
from googlenewsdecoder import new_decoderv1
from news.models import News

BATCH_DELAY = 1


class Command(BaseCommand):
    help = 'Ambil gambar og:image untuk berita yang belum punya gambar'

    def handle(self, *args, **options):
        news_list = News.objects.filter(image_url__isnull=True) | News.objects.filter(image_url='')
        news_list = news_list.distinct()

        total = news_list.count()
        self.stdout.write(f"Ditemukan {total} berita tanpa gambar. Memproses...\n")

        if total == 0:
            self.stdout.write(self.style.SUCCESS("Tidak ada yang perlu diproses."))
            return

        berhasil = 0
        gagal = 0

        for i, news in enumerate(news_list, start=1):
            real_url = self.resolve_real_url(news.url)
            image_url = self.fetch_og_image(real_url)

            if image_url:
                news.image_url = image_url
                news.save()
                berhasil += 1
                self.stdout.write(self.style.SUCCESS(f"[{i}/{total}] OK: {news.title[:60]}"))
            else:
                gagal += 1
                self.stdout.write(self.style.WARNING(f"[{i}/{total}] Tidak ada gambar: {news.title[:60]}"))

            time.sleep(BATCH_DELAY)

        self.stdout.write("\n" + "=" * 50)
        self.stdout.write(self.style.SUCCESS(f"Selesai. {berhasil} berita dapat gambar, {gagal} tidak ditemukan."))

    def resolve_real_url(self, google_url):
        try:
            result = new_decoderv1(google_url, interval=1)
            if result.get('status') and result.get('decoded_url'):
                return result['decoded_url']
        except Exception as e:
            self.stdout.write(self.style.WARNING(f"   Gagal decode URL asli: {e}"))
        return google_url

    def fetch_og_image(self, url):
        try:
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
            response = requests.get(url, headers=headers, timeout=8, allow_redirects=True)
            html = response.text

            match = re.search(
                r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\']([^"\']+)["\']',
                html, re.IGNORECASE
            )
            if not match:
                match = re.search(
                    r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+property=["\']og:image["\']',
                    html, re.IGNORECASE
                )

            if match:
                image_found = match.group(1)
                # Safety check: skip kalau ternyata masih gambar milik Google, bukan situs berita asli
                if 'gstatic.com' in image_found or 'google.com' in image_found:
                    return None
                return image_found
        except Exception:
            pass
        return None