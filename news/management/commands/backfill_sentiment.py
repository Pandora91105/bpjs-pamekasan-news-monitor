import os
import json
import time
from django.core.management.base import BaseCommand
from dotenv import load_dotenv
from google import genai
from news.models import News

load_dotenv()
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

BATCH_SIZE = 10


class Command(BaseCommand):
    help = 'Analisis sentimen untuk berita yang belum punya label sentimen'

    def handle(self, *args, **options):
        news_list = list(News.objects.filter(sentiment__isnull=True))
        self.stdout.write(f"Ditemukan {len(news_list)} berita tanpa sentimen. Memproses...\n")

        if not news_list:
            self.stdout.write(self.style.SUCCESS("Tidak ada yang perlu diproses."))
            return

        for i in range(0, len(news_list), BATCH_SIZE):
            batch = news_list[i:i + BATCH_SIZE]
            self.stdout.write(f"Memproses batch {i // BATCH_SIZE + 1} ({len(batch)} berita)...")

            sentiments = self.analyze_sentiment_batch(batch)

            for news, sentiment in zip(batch, sentiments):
                news.sentiment = sentiment
                news.save()
                self.stdout.write(self.style.SUCCESS(f"  [{sentiment.upper()}] {news.title}"))

            time.sleep(5)

        self.stdout.write(self.style.SUCCESS("\nSelesai memproses semua berita."))

    def analyze_sentiment_batch(self, batch, max_retries=3):
        items_text = ""
        for idx, news in enumerate(batch):
            snippet = (news.snippet or '')[:200]
            items_text += f"\n{idx}. Judul: {news.title}\n   Cuplikan: {snippet}\n"

        prompt = f"""Kamu adalah asisten yang menilai sentimen berita terkait BPJS Kesehatan Cabang Pamekasan.

Untuk setiap berita, tentukan sentimen, pilih salah satu:
- "positif": prestasi, kolaborasi, sinergi, program bermanfaat, apresiasi, informasi netral/imbauan yang tidak mengandung kritik.
- "negatif": tunggakan, tidak dibayar, hutang, keluhan, masalah, kegagalan layanan, kritik.

Daftar berita:
{items_text}

Jawab HANYA dalam format JSON array berisi string sentimen ("positif" atau "negatif") sesuai urutan nomor di atas, tanpa teks tambahan. Contoh untuk 2 berita: ["negatif", "positif"]"""

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
                    return ["netral"] * len(batch)
                return results
            except Exception as e:
                if ("429" in str(e) or "503" in str(e)) and attempt < max_retries - 1:
                    self.stdout.write(self.style.WARNING(f"   Kena rate limit, tunggu 20 detik..."))
                    time.sleep(20)
                else:
                    self.stdout.write(self.style.WARNING(f"   Gagal analisis sentimen: {e}"))
                    return ["netral"] * len(batch)
        return ["netral"] * len(batch)