import random
from datetime import timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone
from news.models import SocialMediaPost


DUMMY_POSTS = [
    # (platform, username, caption, sentiment, likes, comments)

    # ===== Positif - Pelayanan =====
    ('instagram', 'warga_pamekasan', 'Alhamdulillah pelayanan BPJS Kesehatan Cabang Pamekasan sekarang makin cepat, antrean online sangat membantu! Terima kasih 🙏', 'positif', 245, 18),
    ('instagram', 'sehat_selalu_id', 'Kolaborasi bagus antara BPJS Kesehatan Pamekasan dan RSUD dr. Slamet Martodirdjo, semoga makin banyak yang terbantu', 'positif', 312, 22),
    ('tiktok', 'infosehatmadura', 'BPJS Kesehatan Pamekasan sekarang bisa daftar online, gak perlu antre lama lagi! #bpjskesehatan #madura', 'positif', 2340, 156),
    ('instagram', 'kelurhan_warga', 'Proses klaim BPJS Kesehatan di Pamekasan lama banget, sudah sebulan belum cair juga', 'negatif', 203, 58),
    ('tiktok', 'ceritagamaradura', 'Pengalaman saya urus BPJS Kesehatan di Pamekasan, prosesnya ribet dan pegawainya kurang ramah #bpjspamekasan #keluhan', 'negatif', 1420, 203),
    ('instagram', 'pejuang_bpjs', 'Sudah antre dari jam 6 pagi di kantor BPJS Kesehatan Pamekasan tapi loketnya baru buka jam 9, kurang efisien menurut saya 😤', 'negatif', 428, 31),
    ('tiktok', 'suarawargaid', 'Kenapa ya klaim BPJS Kesehatan Pamekasan saya ditolak terus, padahal syarat udah lengkap semua #curhat', 'negatif', 1876, 412),
    ('instagram', 'madura_update', 'Sosialisasi bagus dari BPJS Kesehatan Pamekasan mengenai penggunaan aplikasi Mobile JKN untuk warga', 'positif', 198, 14),
    ('tiktok', 'edukasi_jkn', 'Tips supaya klaim BPJS Kesehatan gak nonaktif, jangan telat bayar! #jkn #bpjskesehatan #madura', 'positif', 3078, 178),
    ('instagram', 'peserta_jkn_pamekasan', 'Terima kasih BPJS Kesehatan Pamekasan sudah bantu warga sangat membantu untuk layanan mobile JKN keliling di desa saya', 'positif', 276, 19),

    # ===== Antrean =====
    ('instagram', 'antrean_madura', 'Antrean loket BPJS Kesehatan Pamekasan hari ini panjang banget, sudah 2 jam belum dipanggil', 'negatif', 512, 87),
    ('tiktok', 'keluhwargaid', 'Sistem antrean online BPJS Kesehatan Pamekasan sering error, jadi harus antre manual lagi #antre #keluhan', 'negatif', 2104, 298),
    ('instagram', 'infoterkini_pmk', 'Fasilitas ruang tunggu BPJS Kesehatan Pamekasan sudah diperbarui, lebih nyaman untuk antre', 'positif', 189, 12),
    ('tiktok', 'reviewlayananpublik', 'Nomor antrean BPJS Kesehatan Pamekasan sekarang bisa diambil online, gak perlu datang subuh lagi #tips #bpjs', 'positif', 4210, 356),

    # ===== Klaim =====
    ('instagram', 'jkn_madura_info', 'Klaim rawat inap BPJS Kesehatan Pamekasan saya cair cuma dalam 3 hari, cepat banget prosesnya', 'positif', 345, 28),
    ('tiktok', 'ceritapasienbpjs', 'Klaim BPJS Kesehatan Pamekasan saya ditolak dengan alasan yang gak jelas, sudah komplain tapi gak ada respon #kecewa', 'negatif', 3456, 521),
    ('instagram', 'reviewrsud_pmk', 'Klaim persalinan BPJS Kesehatan di RSUD Pamekasan diproses dengan baik dan transparan', 'positif', 267, 19),
    ('tiktok', 'sorotanmadura', 'Sudah 2 bulan klaim BPJS Kesehatan Pamekasan saya belum cair, gimana ini min?', 'negatif', 1987, 267),

    # ===== Kepesertaan =====
    ('instagram', 'kartubpjs_info', 'Kartu BPJS Kesehatan saya nonaktif tiba-tiba padahal rutin bayar, sangat mengecewakan pelayanan Pamekasan', 'negatif', 678, 145),
    ('tiktok', 'ulasanjkn', 'Cara aktifkan kembali kartu BPJS Kesehatan yang nonaktif di Pamekasan, gampang kok! #tutorial #bpjs', 'positif', 2890, 201),
    ('instagram', 'kepesertaan_jkn', 'Terima kasih BPJS Kesehatan Pamekasan sudah bantu proses pendaftaran peserta baru anak saya dengan cepat', 'positif', 234, 16),
    ('tiktok', 'infowargapmk', 'Data kepesertaan BPJS Kesehatan saya salah terus, sudah 3 kali ke kantor Pamekasan tapi belum diperbaiki #komplain', 'negatif', 2567, 389),

    # ===== Digitalisasi =====
    ('instagram', 'digitalmadura', 'Aplikasi Mobile JKN BPJS Kesehatan Pamekasan sangat membantu untuk cek status kepesertaan online', 'positif', 298, 21),
    ('tiktok', 'reviewaplikasi_id', 'Server aplikasi Mobile JKN BPJS Kesehatan sering down, susah banget diakses dari Pamekasan #erroraplikasi', 'negatif', 1765, 234),
    ('instagram', 'onlinejkn_pmk', 'Sekarang bisa daftar online BPJS Kesehatan Pamekasan lewat aplikasi, gak perlu ke kantor lagi', 'positif', 356, 27),

    # ===== Sosialisasi & Edukasi =====
    ('tiktok', 'edukasikesehatan_pmk', 'BPJS Kesehatan Pamekasan gelar sosialisasi program JKN-KIS di balai desa, warga antusias banget', 'positif', 1543, 98),
    ('instagram', 'sosialisasi_jkn', 'Acara edukasi BPJS Kesehatan Pamekasan tentang pentingnya iuran rutin sangat informatif', 'positif', 187, 13),

    # ===== Program & Layanan Sabtu =====
    ('instagram', 'programbpjs_pmk', 'Layanan Sabtu BPJS Kesehatan Pamekasan sangat membantu warga yang kerja Senin-Jumat', 'positif', 412, 34),
    ('tiktok', 'infoprogram_madura', 'Program REHAB dari BPJS Kesehatan Pamekasan bantu banget buat cicil tunggakan JKN', 'positif', 2987, 187),

    # ===== Fasilitas =====
    ('instagram', 'fasilitaspmk', 'Kantor BPJS Kesehatan Pamekasan yang baru lebih nyaman dan luas untuk pelayanan', 'positif', 234, 17),
    ('tiktok', 'reviewkantorbpjs', 'Fasilitas kantor BPJS Kesehatan Pamekasan kurang memadai, AC-nya sering mati pas rame pengunjung', 'negatif', 1234, 178),

    # ===== Lainnya / Umum =====
    ('instagram', 'infojkn_madura', 'BPJS Kesehatan Cabang Pamekasan raih penghargaan pelayanan publik terbaik se-Jawa Timur, selamat!', 'positif', 1560, 47),
    ('tiktok', 'pamekasan_viral', 'BPJS Kesehatan Pamekasan buka layanan sabtu untuk warga yang kerja weekday, keren nih programnya', 'positif', 3210, 289),
    ('tiktok', 'kritiksosial_md', 'Kenapa loket BPJS Kesehatan Pamekasan selalu penuh, apa gak bisa nambah petugas?', 'negatif', 1540, 198),
    ('instagram', 'ibu_dua_anak', 'Info dong, kartu BPJS Kesehatan anak saya kok belum bisa dipakai padahal sudah daftar sebulan lalu', 'negatif', 89, 34),
    ('instagram', 'sehat_selalu_pmk', 'Kolaborasi bagus antara BPJS Kesehatan Pamekasan dan RSUD dr. Slamet Martodirdjo, semoga makin banyak yang terbantu', 'positif', 156, 47),
    ('tiktok', 'pengaduanmasyarakat', 'Sudah 3 minggu tunggu balasan pengaduan BPJS Kesehatan Pamekasan, min tolong direspon dong', 'negatif', 1123, 156),
    ('instagram', 'liputanpmk_official', 'BPJS Kesehatan Pamekasan raih penghargaan pelayanan prima tahun ini, apresiasi untuk seluruh petugas', 'positif', 890, 62),
    ('tiktok', 'newspamekasan_id', 'Dugaan keterlambatan pembayaran klaim RS oleh BPJS Kesehatan Pamekasan disorot warganet #viral', 'negatif', 4567, 823),
    ('instagram', 'kabarmadura_update', 'Testimoni positif dari peserta JKN-KIS soal kemudahan layanan BPJS Kesehatan Pamekasan terbaru', 'positif', 445, 38),
    ('tiktok', 'realitamadura', 'Pengalaman buruk urus rujukan BPJS Kesehatan di Pamekasan, birokrasinya ribet banget menurutku', 'negatif', 2345, 401),
    ('instagram', 'jkn_kis_pamekasan', 'Alhamdulillah operasi anak saya ditanggung penuh BPJS Kesehatan Pamekasan, terima kasih banyak', 'positif', 678, 89),
    ('tiktok', 'infoterviral_pmk', 'BPJS Kesehatan Pamekasan gencar sosialisasi ke sekolah-sekolah soal pentingnya JKN sejak dini', 'positif', 1890, 134),
    ('instagram', 'wartamadura_kini', 'Layanan mobile JKN keliling BPJS Kesehatan Pamekasan sangat membantu warga di pelosok desa', 'positif', 523, 41),
    ('tiktok', 'suaramasyarakat_md', 'Kartu BPJS saya hilang, urus penggantian di Pamekasan ternyata cepat dan gak ribet kok', 'positif', 2134, 167),
    ('instagram', 'reportase_pmk', 'Petugas BPJS Kesehatan Pamekasan kurang informatif saat saya tanya soal prosedur klaim', 'negatif', 178, 45),
    ('tiktok', 'faktamadura_id', 'BPJS Kesehatan Pamekasan diduga lambat proses verifikasi berkas peserta baru, banyak keluhan warganet', 'negatif', 3123, 567),
]


class Command(BaseCommand):
    help = 'Generate data dummy untuk monitoring media sosial (Instagram & TikTok)'

    def handle(self, *args, **options):
        created_count = 0
        now = timezone.now()

        for platform, username, caption, sentiment, likes, comments in DUMMY_POSTS:
            # Sebaran tanggal lebih rapat: mayoritas dalam 45 hari terakhir,
            # supaya filter default "30 hari terakhir" selalu punya data yang cukup.
            random_days_ago = random.randint(1, 45)
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