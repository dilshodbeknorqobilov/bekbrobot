from django.conf import settings
from django.contrib import admin
from django.urls import path, re_path
from django.views.static import serve as static_serve

from core.views import talabgor_by_id

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/talabgorlar/<str:id_raqam>/", talabgor_by_id, name="api-talabgor-detail"),
]

# Rasm fayllarini (media/) xizmat qilish — nginx bo'lmasa ham (masalan
# to'g'ridan-to'g'ri 8090-port orqali) API'dagi photo_url ochilishi uchun,
# DEBUG holatidan qat'i nazar doim yoqilgan. Katta trafik bo'lsa, buning
# o'rniga nginx orqali /media/ ni xizmat qilish tavsiya etiladi
# (qarang: deploy/nginx/bekzodbro.conf).
urlpatterns += [
    re_path(r"^media/(?P<path>.*)$", static_serve, {"document_root": settings.MEDIA_ROOT}),
]
