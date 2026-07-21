import os
import json
import time
import feedparser
from datetime import datetime, timezone
from urllib.parse import quote
from django.core.management.base import BaseCommand
from dotenv import load_dotenv
from google import genai
from news.models import News
import re
import requests

load_dotenv()
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

BATCH_SIZE = 10


class Command(BaseCommand):
    help = 'Fetch berita dari Google News RSS, cek relevansi pakai AI (batch), lalu simpan ke database'

    def handle(self, *args, **options):
        keyword = "BPJS Kesehatan Cabang Pamekasan"
        encoded_keyword = quote(keyword)
        rss_url = f"https://news.google.com/rss/search?q={encoded_keyword}&hl=id&gl=ID&ceid=ID:id"

        self.stdout.write(f"Mengambil berita dengan keyword: {keyword}")
        feed = feedparser.parse(rss_url)

        if not feed.entries:
            self.stdout.write(self.style.WARNING("Tidak ada berita ditemukan."))
            return

        # Saring dulu yang belum ada di database, sebelum panggil AI (hemat kuota)
        new_entries = []
        for entry in feed.entries:
            if not News.objects.filter(url=entry.link).exists():
                new_entries.append(entry)

        skipped_duplicate = len(feed.entries) - len(new_entries)
        self.stdout.write(f"Ditemukan {len(feed.entries)} berita dari RSS, {len(new_entries)} berita baru untuk diproses.\n")

        saved_count = 0
        skipped_irrelevant = 0

        # Proses per batch (10 berita sekaligus per panggilan AI)
        for i in range(0, len(new_entries), BATCH_SIZE):
            batch = new_entries[i:i + BATCH_SIZE]
            self.stdout.write(f"Memproses batch {i // BATCH_SIZE + 1} ({len(batch)} berita)...")

            analysis_results = self.check_relevance_batch(batch)

            for entry, result in zip(batch, analysis_results):
                is_relevant = result.get("relevan", False)
                sentiment = result.get("sentimen", "netral")

                if not is_relevant:
                    skipped_irrelevant += 1
                    continue

                if entry.get('published_parsed'):
                    published_date = datetime(*entry.published_parsed[:6], tzinfo=timezone.utc)
                else:
                    published_date = datetime.now(timezone.utc)

                image_url = self.fetch_og_image(entry.link)

                News.objects.create(
                    title=entry.title,
                    source=entry.get('source', {}).get('title', 'Tidak diketahui'),
                    url=entry.link,
                    snippet=entry.get('summary', ''),
                    image_url=image_url,
                    published_date=published_date,
                    is_relevant=True,
                    sentiment=sentiment,
                )
                saved_count += 1
                self.stdout.write(self.style.SUCCESS(f"  [DISIMPAN - {sentiment.upper()}] {entry.title}"))

            time.sleep(5)  # jeda antar batch, jaga-jaga rate limit

        self.stdout.write("\n" + "=" * 50)
        self.stdout.write(self.style.SUCCESS(f"Selesai. {saved_count} berita baru disimpan."))
        self.stdout.write(f"{skipped_duplicate} berita dilewati (sudah ada).")
        self.stdout.write(f"{skipped_irrelevant} berita dilewati (tidak relevan menurut AI).")

    def check_relevance_batch(self, batch, max_retries=3):
        items_text = ""
        for idx, entry in enumerate(batch):
            snippet = entry.get('summary', '')[:200]
            items_text += f"\n{idx}. Judul: {entry.title}\n   Cuplikan: {snippet}\n"

        prompt = f"""Kamu adalah asisten yang menganalisis berita terkait BPJS Kesehatan Cabang Pamekasan (Madura, Jawa Timur, Indonesia).

                Untuk setiap berita di bawah ini, tentukan DUA hal:
                1. "relevan": apakah berita ini membahas BPJS KESEHATAN (bukan BPJS Ketenagakerjaan) yang berkaitan dengan wilayah Pamekasan secara spesifik (layanan, klaim, kepesertaan, kebijakan, keluhan, faskes, dll di Pamekasan). true/false.
                2. "sentimen": nada pemberitaan terhadap BPJS Kesehatan Pamekasan. Pilih salah satu: "positif" (prestasi, apresiasi, program bermanfaat, informasi netral/imbauan yang tidak mengandung kritik) atau "negatif" (keluhan, masalah, kegagalan layanan, kritik). Jika tidak relevan, isi sentimen dengan "positif".

                Daftar berita:
                {items_text}

                Jawab HANYA dalam format JSON array of objects, tanpa teks tambahan apapun, sesuai urutan nomor di atas. Contoh untuk 2 berita:
                [{{"relevan": true, "sentimen": "negatif"}}, {{"relevan": false, "sentimen": "netral"}}]"""

        for attempt in range(max_retries):
            try:
                response = client.models.generate_content(
                    model="gemini-flash-latest",
                    contents=prompt,
                )
                text = response.text.strip()
                text = text.replace("```json", "").replace("```", "").strip()
                results = json.loads(text)

                if len(results) != len(batch):
                    self.stdout.write(self.style.WARNING(f"   Jumlah hasil AI tidak cocok, anggap semua tidak relevan."))
                    return [{"relevan": False, "sentimen": "netral"}] * len(batch)

                return results
            except Exception as e:
                if ("429" in str(e) or "503" in str(e)) and attempt < max_retries - 1:
                    self.stdout.write(self.style.WARNING(f"   Kena rate limit, tunggu 20 detik... (percobaan {attempt + 1}/{max_retries})"))
                    time.sleep(20)
                else:
                    self.stdout.write(self.style.WARNING(f"   Gagal cek relevansi AI: {e}"))
                    return [{"relevan": False, "sentimen": "netral"}] * len(batch)
        return [{"relevan": False, "sentimen": "netral"}] * len(batch)
    
    def fetch_og_image(self, url):
        try:
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
            response = requests.get(url, headers=headers, timeout=6, allow_redirects=True)
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
                return match.group(1)
        except Exception:
            pass
        return None