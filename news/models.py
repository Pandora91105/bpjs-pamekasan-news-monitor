from django.db import models

class News(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Menunggu Review'),
        ('approved', 'Disetujui'),
        ('rejected', 'Ditolak'),
    ]

    SENTIMENT_CHOICES = [
        ('positif', 'Positif'),
        ('netral', 'Netral'),
        ('negatif', 'Negatif'),
    ]

    title = models.CharField(max_length=500)
    source = models.CharField(max_length=200)
    url = models.URLField(max_length=1000, unique=True)
    snippet = models.TextField(blank=True)
    image_url = models.URLField(max_length=1000, blank=True, null=True)
    published_date = models.DateTimeField()

    is_relevant = models.BooleanField(default=False)
    sentiment = models.CharField(max_length=10, choices=SENTIMENT_CHOICES, blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')

    fetched_at = models.DateTimeField(auto_now_add=True)
    reviewed_at = models.DateTimeField(blank=True, null=True)

    def __str__(self):
        return self.title

    class Meta:
        ordering = ['-published_date']
        verbose_name = 'Berita'
        verbose_name_plural = 'Berita'