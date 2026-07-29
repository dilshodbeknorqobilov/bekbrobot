from django.db import models


class Nazoratchi(models.Model):
    """Botdan Nazoratchi bo'lishni so'ragan va admin tomonidan
    tasdiqlangan/rad etilgan foydalanuvchi."""

    class Status(models.TextChoices):
        PENDING = "pending", "Kutilmoqda"
        APPROVED = "approved", "Tasdiqlangan"
        REJECTED = "rejected", "Rad etilgan"

    telegram_id = models.BigIntegerField(unique=True, verbose_name="Telegram ID")
    username = models.CharField(max_length=255, blank=True, null=True)
    full_name = models.CharField(max_length=255, blank=True, null=True)
    status = models.CharField(
        max_length=10, choices=Status.choices, default=Status.PENDING
    )
    requested_at = models.DateTimeField(auto_now_add=True)
    decided_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "Nazoratchi"
        verbose_name_plural = "Nazoratchilar"
        ordering = ["-requested_at"]

    def __str__(self) -> str:
        return f"{self.full_name or self.telegram_id} ({self.get_status_display()})"


class Talabgor(models.Model):
    """Nazoratchi tomonidan kiritilgan talabgor ma'lumotlari."""

    familiya = models.CharField(max_length=100, verbose_name="Familiyasi")
    ism = models.CharField(max_length=100, verbose_name="Ismi")
    otasining_ismi = models.CharField(max_length=100, verbose_name="Otasining ismi")
    telefon = models.CharField(max_length=20, verbose_name="Telefon raqami")
    photo = models.ImageField(upload_to="talabgorlar/%Y/%m/", verbose_name="Rasm")
    id_raqam = models.CharField(
        max_length=6, unique=True, db_index=True, verbose_name="ID raqam"
    )
    nazoratchi = models.ForeignKey(
        Nazoratchi,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="talabgorlar",
        verbose_name="Nazoratchi",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Talabgor"
        verbose_name_plural = "Talabgorlar"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.familiya} {self.ism} — {self.id_raqam}"
