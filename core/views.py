import re

from django.http import JsonResponse

from .models import Talabgor

ID_PATTERN = re.compile(r"^(\d{4}|\d{6})$")


def talabgor_by_id(request, id_raqam: str):
    """Ochiq (autentifikatsiyasiz) REST endpoint.

    So'rov: GET /api/talabgorlar/<id_raqam>/
    Javob: FIO va rasm URL manzili (JSON).

    Diqqat: bu endpoint ochiq — ID raqamni bilgan har kim ma'lumotni ko'ra oladi.
    ID raqamlar atigi 4-6 xonali bo'lgani uchun, agar kelajakda cheklov kerak
    bo'lsa, oddiy API-kalit (masalan `X-API-Key` header) qo'shish tavsiya etiladi.
    """
    if not ID_PATTERN.match(id_raqam):
        return JsonResponse(
            {"detail": "ID raqam 4 yoki 6 xonali son bo'lishi kerak."},
            status=400,
            json_dumps_params={"ensure_ascii": False},
        )

    talabgor = Talabgor.objects.filter(id_raqam=id_raqam).select_related("nazoratchi").first()
    if not talabgor:
        return JsonResponse(
            {"detail": "Bunday ID raqam bo'yicha talabgor topilmadi."},
            status=404,
            json_dumps_params={"ensure_ascii": False},
        )

    photo_url = request.build_absolute_uri(talabgor.photo.url) if talabgor.photo else None

    data = {
        "id_raqam": talabgor.id_raqam,
        "familiya": talabgor.familiya,
        "ism": talabgor.ism,
        "otasining_ismi": talabgor.otasining_ismi,
        "fio": f"{talabgor.familiya} {talabgor.ism} {talabgor.otasining_ismi}",
        "telefon": talabgor.telefon,
        "photo_url": photo_url,
    }
    return JsonResponse(data, json_dumps_params={"ensure_ascii": False})
