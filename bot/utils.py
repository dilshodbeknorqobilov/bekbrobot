import re
from pathlib import Path
from typing import Optional

# 4 xonali (masalan 1234) yoki 6 xonali (masalan 123456) ID raqam
ID_REGEX = r"^(\d{4}|\d{6})$"
ID_PATTERN = re.compile(ID_REGEX)

# Telefon raqamda faqat raqamlar (va ixtiyoriy +, bo'shliq, tire ajratuvchilar)
# bo'lishi kerak; yakuniy natija 9 xonali bo'lishi shart (masalan: 881144101)
PHONE_ALLOWED_CHARS = re.compile(r"^[\d+\-\s]+$")
PHONE_REGEX = re.compile(r"^\d{9}$")


def normalize_phone(raw: str) -> Optional[str]:
    """Telefon raqamni tekshiradi va 9 xonali shaklga keltiradi.

    Faqat raqamlar (va +, bo'shliq, tire kabi ajratuvchilar) qabul qilinadi —
    harf yoki boshqa belgi bo'lsa None qaytariladi. "+998" yoki "998" mamlakat
    kodi bo'lsa, avtomatik olib tashlanadi.
    """
    cleaned = raw.strip()
    if not cleaned or not PHONE_ALLOWED_CHARS.match(cleaned):
        return None

    digits = re.sub(r"\D", "", cleaned)
    if digits.startswith("998") and len(digits) == 12:
        digits = digits[3:]

    if PHONE_REGEX.match(digits):
        return digits
    return None


def find_pdf(testpdf_dir: str, id_raqam: str) -> Optional[Path]:
    """testpdf_dir papkasidan id_raqam bilan boshlanuvchi birinchi
    PDF faylni qaytaradi, topilmasa None."""
    directory = Path(testpdf_dir)
    if not directory.exists():
        return None
    matches = sorted(directory.glob(f"{id_raqam}*.pdf"))
    return matches[0] if matches else None
