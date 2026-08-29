from django.conf import settings
from django.contrib import admin
from django.urls import path, re_path
from django.views.static import serve as static_serve

from core.views import talabgor_by_id
from core.views_miniapp import (
    miniapp_add_talabgor,
    miniapp_download_pdf,
    miniapp_edit_talabgor,
    miniapp_home,
    miniapp_my_talabgorlar,
    miniapp_request_nazoratchi,
    miniapp_search,
    miniapp_user_info,
)

urlpatterns = [
    path("admin/", admin.site.urls),
    # Eski REST endpoint (orqaga moslik uchun):
    path("api/talabgorlar/<str:id_raqam>/", talabgor_by_id, name="api-talabgor-detail"),
    # Telegram Mini App sahifasi va API yo'llari:
    path("webapp/", miniapp_home, name="miniapp-home"),
    path("api/miniapp/me/", miniapp_user_info, name="miniapp-user-info"),
    path("api/miniapp/request-nazoratchi/", miniapp_request_nazoratchi, name="miniapp-request-nazoratchi"),
    path("api/miniapp/talabgor/", miniapp_add_talabgor, name="miniapp-add-talabgor"),
    path("api/miniapp/talabgor/<int:talabgor_id>/edit/", miniapp_edit_talabgor, name="miniapp-edit-talabgor"),
    path("api/miniapp/my-talabgorlar/", miniapp_my_talabgorlar, name="miniapp-my-talabgorlar"),
    path("api/miniapp/search/<str:id_raqam>/", miniapp_search, name="miniapp-search"),
    path("api/miniapp/pdf/<str:id_raqam>/", miniapp_download_pdf, name="miniapp-download-pdf"),
]

# Rasm fayllarini (media/) xizmat qilish — nginx bo'lmasa ham (masalan
# to'g'ridan-to'g'ri 8090-port orqali) API'dagi photo_url ochilishi uchun,
# DEBUG holatidan qat'i nazar doim yoqilgan. Katta trafik bo'lsa, buning
# o'rniga nginx orqali /media/ ni xizmat qilish tavsiya etiladi
# (qarang: deploy/nginx/bekzodbro.conf).
urlpatterns += [
    re_path(r"^media/(?P<path>.*)$", static_serve, {"document_root": settings.MEDIA_ROOT}),
]
