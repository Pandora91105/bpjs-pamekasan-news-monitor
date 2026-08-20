import random
from datetime import timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone
from news.models import SocialMediaPost

DUMMY_POSTS = [
    # (platform, username, caption, sentiment, likes, comments)
    ('instagram', 'warga_pamekasan', 'Alhamdulillah pelayanan BPJS Kesehatan Pamekasan sekarang makin cepat, antrean online sangat membantu! Terima kasih 🙏', 'positif', 245, 18),
    ('instagram', 'ibu_dua_anak', 'Info dong, kartu BPJS Kesehatan anak saya kok nonaktif ya padahal rutin bayar. Sudah 3 hari belum ada solusi dari kantor cabang Pamekasan 😢', 'negatif', 89, 34),
    ('instagram', 'sehat_selalu_id', 'Kolaborasi bagus antara BPJS Kesehatan Pamekasan dan RSUD dr. Slamet Martodirdjo, semoga makin banyak yang terbantu', 'positif', 312, 22),
    ('instagram', 'pejuang_bpjs', 'Sudah antre dari jam 6 pagi di kantor BPJS Pamekasan tapi loketnya baru buka jam 9, kurang efisien menurut saya', 'negatif', 156, 47),
    ('instagram', 'madura_update', 'BPJS Kesehatan Cabang Pamekasan raih penghargaan pelayanan publik terbaik se-Jawa Timur, selamat!', 'positif', 428, 31),
    ('instagram', 'keluhan_warga', 'Proses klaim BPJS Kesehatan di Pamekasan lama banget, sudah sebulan belum cair juga', 'negatif', 203, 58),
    ('instagram', 'sosialisasi_sehat', 'Terima kasih BPJS Kesehatan Pamekasan sudah adakan sosialisasi JKN di desa kami, sangat bermanfaat untuk warga', 'positif', 187, 12),
    ('instagram', 'peserta_jkn_pamekasan', 'Layanan mobile JKN keliling BPJS Pamekasan sangat membantu warga yang jauh dari kantor cabang', 'positif', 276, 19),

    ('tiktok', 'ceritawargamadura', 'Pengalaman saya urus BPJS Kesehatan di Pamekasan, prosesnya ribet dan pegawainya kurang ramah #bpjspamekasan #keluhan', 'negatif', 1420, 203),
    ('tiktok', 'infosehatmadura', 'BPJS Kesehatan Pamekasan sekarang bisa daftar online, gak perlu antre lama lagi! #bpjskesehatan #madura', 'positif', 2340, 156),
    ('tiktok', 'edukasi_jkn', 'Tips supaya kartu BPJS Kesehatan gak nonaktif, jangan telat bayar iuran ya guys #jkn #bpjspamekasan', 'positif', 987, 78),
    ('tiktok', 'suarawarga_id', 'Kenapa ya klaim BPJS Kesehatan Pamekasan saya ditolak terus, padahal syarat udah lengkap semua #curhat', 'negatif', 1876, 412),
    ('tiktok', 'pamekasan_viral', 'BPJS Kesehatan Pamekasan buka layanan sabtu untuk warga yang kerja weekday, keren nih programnya', 'positif', 3210, 289),
    ('tiktok', 'kritiksosial_md', 'Kenapa loket BPJS Kesehatan Pamekasan selalu penuh, apa gak bisa nambah petugas?', 'negatif', 1540, 198),
]


class Command(BaseCommand):
    help = 'Generate data dummy untuk monitoring media sosial (Instagram & TikTok)'

    def handle(self, *args, **options):
        created_count = 0
        now = timezone.now()

        for platform, username, caption, sentiment, likes, comments in DUMMY_POSTS:
            random_days_ago = random.randint(1, 180)
            posted_date = now - timedelta(days=random_days_ago)

            SocialMediaPost.objects.create(
                platform=platform,
                username=username,
                caption=caption,
                sentiment=sentiment,
                posted_date=posted_date,
                likes_count=likes,
                comments_count=comments,
                is_dummy=True,
            )
            created_count += 1
            self.stdout.write(self.style.SUCCESS(f"[{platform.upper()}] @{username} - {sentiment}"))

        self.stdout.write("\n" + "=" * 50)
        self.stdout.write(self.style.SUCCESS(f"Selesai. {created_count} data dummy berhasil dibuat."))