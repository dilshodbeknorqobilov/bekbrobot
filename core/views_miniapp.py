import json
import logging
import urllib.request
from pathlib import Path

from django.conf import settings
from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator
from django.db import models
from django.http import FileResponse, Http404, JsonResponse
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST

from bot.utils import ID_PATTERN, find_pdf, normalize_phone
from core.models import Nazoratchi, Talabgor
from core.telegram_auth import get_telegram_user_from_request

logger = logging.getLogger(__name__)


def _send_telegram_notification(chat_id: int, text: str, reply_markup: dict = None) -> None:
    """Telegram bot orqali adminga xabar yuborish (standart urllib orqali)."""
    token = getattr(settings, "BOT_TOKEN", "")
    if not token:
        return
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML",
    }
    if reply_markup:
        payload["reply_markup"] = reply_markup

    try:
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )
        urllib.request.urlopen(req, timeout=5)
    except Exception as exc:
        logger.warning("Telegram bildirishnoma yuborishda xatolik (%s): %s", chat_id, exc)


@require_GET
def miniapp_home(request):
    """Telegram Mini App asosiy sahifasini ko'rsatish."""
    return render(
        request,
        "miniapp/index.html",
        {
            "bot_username": getattr(settings, "BOT_USERNAME", ""),
        },
    )


@require_GET
def miniapp_user_info(request):
    """Foydalanuvchining Telegram initData ma'lumotlarini tekshirish va
    nazoratchilik statusini qaytarish.
    """
    is_valid, user_data, err = get_telegram_user_from_request(request)
    if not is_valid or not user_data:
        return JsonResponse(
            {"success": False, "detail": err or "Autentifikatsiya xatosi."},
            status=401,
            json_dumps_params={"ensure_ascii": False},
        )

    telegram_id = user_data.get("id")
    admin_ids = getattr(settings, "ADMIN_IDS", [])
    is_admin = telegram_id in admin_ids

    nazoratchi = Nazoratchi.objects.filter(telegram_id=telegram_id).first()
    nazoratchi_status = nazoratchi.status if nazoratchi else "none"
    is_approved = nazoratchi_status == Nazoratchi.Status.APPROVED

    return JsonResponse(
        {
            "success": True,
            "user": {
                "id": telegram_id,
                "first_name": user_data.get("first_name", ""),
                "last_name": user_data.get("last_name", ""),
                "username": user_data.get("username", ""),
            },
            "is_admin": is_admin,
            "is_nazoratchi": is_approved,
            "nazoratchi_status": nazoratchi_status,
        },
        json_dumps_params={"ensure_ascii": False},
    )


@csrf_exempt
@require_POST
def miniapp_request_nazoratchi(request):
    """Mini App orqali Nazoratchi bo'lish so'rovi yuborish."""
    is_valid, user_data, err = get_telegram_user_from_request(request)
    if not is_valid or not user_data:
        return JsonResponse(
            {"success": False, "detail": err or "Autentifikatsiya xatosi."},
            status=401,
            json_dumps_params={"ensure_ascii": False},
        )

    telegram_id = user_data.get("id")
    username = user_data.get("username") or ""
    first_name = user_data.get("first_name") or ""
    last_name = user_data.get("last_name") or ""
    full_name = f"{first_name} {last_name}".strip() or str(telegram_id)

    nazoratchi, _ = Nazoratchi.objects.update_or_create(
        telegram_id=telegram_id,
        defaults={
            "username": username,
            "full_name": full_name,
        },
    )

    if nazoratchi.status == Nazoratchi.Status.APPROVED:
        return JsonResponse(
            {"success": True, "message": "Siz allaqachon tasdiqlangan nazoratchisiz.", "status": "approved"},
            json_dumps_params={"ensure_ascii": False},
        )

    if nazoratchi.status == Nazoratchi.Status.PENDING:
        return JsonResponse(
            {"success": True, "message": "So'rovingiz allaqachon yuborilgan, kuting.", "status": "pending"},
            json_dumps_params={"ensure_ascii": False},
        )

    nazoratchi.status = Nazoratchi.Status.PENDING
    nazoratchi.decided_at = None
    nazoratchi.save()

    # Adminga Telegram bot orqali tasdiqlash tugmalari bilan xabar yuborish
    admin_ids = getattr(settings, "ADMIN_IDS", [])
    text = (
        "🆕 Yangi Nazoratchi so'rovi (Mini App orqali):\n"
        f"Ism: {full_name}\n"
        f"Username: @{username or '-'}\n"
        f"Telegram ID: {telegram_id}"
    )
    markup = {
        "inline_keyboard": [
            [
                {"text": "✅ Ha", "callback_data": f"nazoratchi_yes:{telegram_id}"},
                {"text": "❌ Yo'q", "callback_data": f"nazoratchi_no:{telegram_id}"},
            ]
        ]
    }
    for admin_id in admin_ids:
        _send_telegram_notification(admin_id, text, markup)

    return JsonResponse(
        {"success": True, "message": "So'rovingiz adminga yuborildi. Javobni kuting.", "status": "pending"},
        json_dumps_params={"ensure_ascii": False},
    )


@csrf_exempt
@require_POST
def miniapp_add_talabgor(request):
    """Mini App orqali yangi Talabgor qo'shish (faqat tasdiqlangan nazoratchilar)."""
    is_valid, user_data, err = get_telegram_user_from_request(request)
    if not is_valid or not user_data:
        return JsonResponse(
            {"success": False, "detail": err or "Autentifikatsiya xatosi."},
            status=401,
            json_dumps_params={"ensure_ascii": False},
        )

    telegram_id = user_data.get("id")
    nazoratchi = Nazoratchi.objects.filter(
        telegram_id=telegram_id, status=Nazoratchi.Status.APPROVED
    ).first()

    if not nazoratchi:
        return JsonResponse(
            {"success": False, "detail": "Talabgor qo'shish uchun faqat tasdiqlangan nazoratchilarga ruxsat berilgan."},
            status=403,
            json_dumps_params={"ensure_ascii": False},
        )

    familiya = (request.POST.get("familiya") or "").strip()
    ism = (request.POST.get("ism") or "").strip()
    otasining_ismi = (request.POST.get("otasining_ismi") or "").strip()
    telefon_raw = (request.POST.get("telefon") or "").strip()
    id_raqam = (request.POST.get("id_raqam") or "").strip()
    photo = request.FILES.get("photo")

    if not (familiya and ism and otasining_ismi and telefon_raw and id_raqam and photo):
        return JsonResponse(
            {"success": False, "detail": "Barcha maydonlar va rasm to'ldirilishi shart."},
            status=400,
            json_dumps_params={"ensure_ascii": False},
        )

    if not ID_PATTERN.match(id_raqam):
        return JsonResponse(
            {"success": False, "detail": "ID raqam 4 yoki 6 xonali son bo'lishi kerak."},
            status=400,
            json_dumps_params={"ensure_ascii": False},
        )

    if Talabgor.objects.filter(id_raqam=id_raqam).exists():
        return JsonResponse(
            {"success": False, "detail": f"'{id_raqam}' ID raqam allaqachon bazada mavjud."},
            status=400,
            json_dumps_params={"ensure_ascii": False},
        )

    telefon = normalize_phone(telefon_raw)
    if not telefon:
        return JsonResponse(
            {"success": False, "detail": "Telefon raqami noto'g'ri (masalan: 901234567)."},
            status=400,
            json_dumps_params={"ensure_ascii": False},
        )

    try:
        talabgor = Talabgor(
            familiya=familiya,
            ism=ism,
            otasining_ismi=otasining_ismi,
            telefon=telefon,
            id_raqam=id_raqam,
            nazoratchi=nazoratchi,
        )
        _, ext = photo.name.rsplit(".", 1) if "." in photo.name else ("", "jpg")
        photo_filename = f"{id_raqam}.{ext.lower()}"
        talabgor.photo.save(photo_filename, photo, save=False)
        talabgor.save()

        photo_url = request.build_absolute_uri(talabgor.photo.url) if talabgor.photo else None
        return JsonResponse(
            {
                "success": True,
                "message": "Talabgor muvaffaqiyatli saqlandi!",
                "talabgor": {
                    "id": talabgor.id,
                    "id_raqam": talabgor.id_raqam,
                    "familiya": talabgor.familiya,
                    "ism": talabgor.ism,
                    "otasining_ismi": talabgor.otasining_ismi,
                    "telefon": talabgor.telefon,
                    "photo_url": photo_url,
                },
            },
            json_dumps_params={"ensure_ascii": False},
        )
    except Exception as exc:
        logger.exception("Talabgorni saqlashda xatolik:")
        return JsonResponse(
            {"success": False, "detail": f"Saqlashda xatolik yuz berdi: {str(exc)}"},
            status=500,
            json_dumps_params={"ensure_ascii": False},
        )


@require_GET
def miniapp_search(request, id_raqam: str):
    """Mini App: ID bo'yicha talabgor va test PDF natijasini qidirish."""
    id_raqam = id_raqam.strip()
    if not ID_PATTERN.match(id_raqam):
        return JsonResponse(
            {"success": False, "detail": "ID raqam 4 yoki 6 xonali son bo'lishi kerak."},
            status=400,
            json_dumps_params={"ensure_ascii": False},
        )

    talabgor = Talabgor.objects.filter(id_raqam=id_raqam).select_related("nazoratchi").first()
    talabgor_data = None
    if talabgor:
        photo_url = request.build_absolute_uri(talabgor.photo.url) if talabgor.photo else None
        talabgor_data = {
            "id_raqam": talabgor.id_raqam,
            "familiya": talabgor.familiya,
            "ism": talabgor.ism,
            "otasining_ismi": talabgor.otasining_ismi,
            "fio": f"{talabgor.familiya} {talabgor.ism} {talabgor.otasining_ismi}",
            "telefon": talabgor.telefon,
            "photo_url": photo_url,
        }

    testpdf_dir = getattr(settings, "TESTPDF_DIR", "")
    pdf_path = find_pdf(testpdf_dir, id_raqam)
    has_pdf = pdf_path is not None

    return JsonResponse(
        {
            "success": True,
            "id_raqam": id_raqam,
            "found": talabgor_data is not None or has_pdf,
            "talabgor": talabgor_data,
            "has_pdf": has_pdf,
            "pdf_name": pdf_path.name if pdf_path else None,
            "pdf_download_url": f"/api/miniapp/pdf/{id_raqam}/" if has_pdf else None,
        },
        json_dumps_params={"ensure_ascii": False},
    )


@require_GET
def miniapp_download_pdf(request, id_raqam: str):
    """Mini App: ID bo'yicha topilgan PDF faylini yuklab berish."""
    id_raqam = id_raqam.strip()
    if not ID_PATTERN.match(id_raqam):
        raise Http404("ID noto'g'ri.")

    testpdf_dir = getattr(settings, "TESTPDF_DIR", "")
    pdf_path = find_pdf(testpdf_dir, id_raqam)
    if not pdf_path or not pdf_path.exists():
        raise Http404("PDF fayl topilmadi.")

    return FileResponse(
        open(pdf_path, "rb"),
        content_type="application/pdf",
        filename=pdf_path.name,
        as_attachment=True,
    )


@require_GET
def miniapp_my_talabgorlar(request):
    """Tasdiqlangan nazoratchining kiritgan talabgorlari ro'yxatini 10 tadan
    sahifalab (pagination) qaytarish.
    """
    is_valid, user_data, err = get_telegram_user_from_request(request)
    if not is_valid or not user_data:
        return JsonResponse(
            {"success": False, "detail": err or "Autentifikatsiya xatosi."},
            status=401,
            json_dumps_params={"ensure_ascii": False},
        )

    telegram_id = user_data.get("id")
    admin_ids = getattr(settings, "ADMIN_IDS", [])
    is_admin = telegram_id in admin_ids

    nazoratchi = Nazoratchi.objects.filter(
        telegram_id=telegram_id, status=Nazoratchi.Status.APPROVED
    ).first()

    if not nazoratchi and not is_admin:
        return JsonResponse(
            {"success": False, "detail": "Talabgorlar ro'yxatini ko'rish faqat tasdiqlangan nazoratchilarga ruxsat berilgan."},
            status=403,
            json_dumps_params={"ensure_ascii": False},
        )

    if is_admin:
        qs = Talabgor.objects.all().order_by("-created_at")
    else:
        qs = Talabgor.objects.filter(nazoratchi=nazoratchi).order_by("-created_at")

    search_query = (request.GET.get("q") or "").strip()
    if search_query:
        qs = qs.filter(
            models.Q(id_raqam__icontains=search_query)
            | models.Q(familiya__icontains=search_query)
            | models.Q(ism__icontains=search_query)
            | models.Q(telefon__icontains=search_query)
        )

    paginator = Paginator(qs, 10)  # Har sahifada 10 tadan ma'lumot
    page_number = request.GET.get("page", 1)

    try:
        page_obj = paginator.page(page_number)
    except PageNotAnInteger:
        page_obj = paginator.page(1)
    except EmptyPage:
        page_obj = paginator.page(paginator.num_pages)

    results = []
    for t in page_obj:
        photo_url = request.build_absolute_uri(t.photo.url) if t.photo else None
        results.append({
            "id": t.id,
            "id_raqam": t.id_raqam,
            "familiya": t.familiya,
            "ism": t.ism,
            "otasining_ismi": t.otasining_ismi,
            "fio": f"{t.familiya} {t.ism} {t.otasining_ismi}".strip(),
            "telefon": t.telefon,
            "photo_url": photo_url,
            "created_at": t.created_at.strftime("%Y-%m-%d %H:%M"),
        })

    return JsonResponse(
        {
            "success": True,
            "page": page_obj.number,
            "total_pages": paginator.num_pages,
            "total_count": paginator.count,
            "has_next": page_obj.has_next(),
            "has_prev": page_obj.has_previous(),
            "results": results,
        },
        json_dumps_params={"ensure_ascii": False},
    )


@csrf_exempt
@require_POST
def miniapp_edit_talabgor(request, talabgor_id: int):
    """Tasdiqlangan nazoratchi o'zi kiritgan talabgor ma'lumotlarini tahrirlashi."""
    is_valid, user_data, err = get_telegram_user_from_request(request)
    if not is_valid or not user_data:
        return JsonResponse(
            {"success": False, "detail": err or "Autentifikatsiya xatosi."},
            status=401,
            json_dumps_params={"ensure_ascii": False},
        )

    telegram_id = user_data.get("id")
    admin_ids = getattr(settings, "ADMIN_IDS", [])
    is_admin = telegram_id in admin_ids

    nazoratchi = Nazoratchi.objects.filter(
        telegram_id=telegram_id, status=Nazoratchi.Status.APPROVED
    ).first()

    if not nazoratchi and not is_admin:
        return JsonResponse(
            {"success": False, "detail": "Faqat tasdiqlangan nazoratchilarga tahrirlash huquqi berilgan."},
            status=403,
            json_dumps_params={"ensure_ascii": False},
        )

    try:
        talabgor = Talabgor.objects.get(id=talabgor_id)
    except Talabgor.DoesNotExist:
        return JsonResponse(
            {"success": False, "detail": "Talabgor topilmadi."},
            status=404,
            json_dumps_params={"ensure_ascii": False},
        )

    if not is_admin and talabgor.nazoratchi_id != nazoratchi.id:
        return JsonResponse(
            {"success": False, "detail": "Siz faqat o'zingiz kiritgan talabgorlarni tahrirlashingiz mumkin."},
            status=403,
            json_dumps_params={"ensure_ascii": False},
        )

    familiya = (request.POST.get("familiya") or "").strip()
    ism = (request.POST.get("ism") or "").strip()
    otasining_ismi = (request.POST.get("otasining_ismi") or "").strip()
    telefon_raw = (request.POST.get("telefon") or "").strip()
    id_raqam = (request.POST.get("id_raqam") or "").strip()
    photo = request.FILES.get("photo")

    if not (familiya and ism and otasining_ismi and telefon_raw and id_raqam):
        return JsonResponse(
            {"success": False, "detail": "Barcha maydonlar to'ldirilishi shart."},
            status=400,
            json_dumps_params={"ensure_ascii": False},
        )

    if not ID_PATTERN.match(id_raqam):
        return JsonResponse(
            {"success": False, "detail": "ID raqam 4 yoki 6 xonali son bo'lishi kerak."},
            status=400,
            json_dumps_params={"ensure_ascii": False},
        )

    if Talabgor.objects.filter(id_raqam=id_raqam).exclude(id=talabgor.id).exists():
        return JsonResponse(
            {"success": False, "detail": f"'{id_raqam}' ID raqam boshqa talabgorga tegishli."},
            status=400,
            json_dumps_params={"ensure_ascii": False},
        )

    telefon = normalize_phone(telefon_raw)
    if not telefon:
        return JsonResponse(
            {"success": False, "detail": "Telefon raqami noto'g'ri (masalan: 901234567)."},
            status=400,
            json_dumps_params={"ensure_ascii": False},
        )

    try:
        talabgor.familiya = familiya
        talabgor.ism = ism
        talabgor.otasining_ismi = otasining_ismi
        talabgor.telefon = telefon
        talabgor.id_raqam = id_raqam

        if photo:
            _, ext = photo.name.rsplit(".", 1) if "." in photo.name else ("", "jpg")
            photo_filename = f"{id_raqam}.{ext.lower()}"
            talabgor.photo.save(photo_filename, photo, save=False)

        talabgor.save()

        photo_url = request.build_absolute_uri(talabgor.photo.url) if talabgor.photo else None
        return JsonResponse(
            {
                "success": True,
                "message": "Talabgor ma'lumotlari muvaffaqiyatli yangilandi!",
                "talabgor": {
                    "id": talabgor.id,
                    "id_raqam": talabgor.id_raqam,
                    "familiya": talabgor.familiya,
                    "ism": talabgor.ism,
                    "otasining_ismi": talabgor.otasining_ismi,
                    "fio": f"{talabgor.familiya} {talabgor.ism} {talabgor.otasining_ismi}".strip(),
                    "telefon": talabgor.telefon,
                    "photo_url": photo_url,
                },
            },
            json_dumps_params={"ensure_ascii": False},
        )
    except Exception as exc:
        logger.exception("Talabgorni yangilashda xatolik:")
        return JsonResponse(
            {"success": False, "detail": f"Yangilashda xatolik yuz berdi: {str(exc)}"},
            status=500,
            json_dumps_params={"ensure_ascii": False},
        )
