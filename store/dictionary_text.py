import re
import unicodedata

from django.core.exceptions import ValidationError


_BIDI_CONTROL_CHARS = "\u200e\u200f\u202a\u202b\u202c\u202d\u202e\u2066\u2067\u2068\u2069\u061c"
_ARABIC_DIACRITICS_RE = re.compile(r"[\u0610-\u061a\u064b-\u065f\u0670\u06d6-\u06ed]")
_WHITESPACE_RE = re.compile(r"\s+")
_NON_ALNUM_SPACE_RE = re.compile(r"[^a-z0-9\s]")

_ARABIC_VARIANT_MAP = str.maketrans(
    {
        "ي": "ی",
        "ى": "ی",
        "ك": "ک",
        "أ": "ا",
        "إ": "ا",
        "آ": "ا",
        "ٱ": "ا",
        "ؤ": "و",
        "ئ": "ی",
        "ة": "ه",
        "ۀ": "ه",
        "ـ": "",
    }
)

_TRANSLIT_APOSTROPHE_MAP = str.maketrans(
    {
        "'": "’",
        "`": "’",
        "‘": "’",
        "ʼ": "’",
        "ʻ": "’",
        "ʹ": "’",
    }
)

_TRANSLIT_ALLOWED_RE = re.compile(r"^[A-Za-z\u0100-\u024f\u1e00-\u1eff\u02be\u02bf’\-\s.]*$")


def normalize_script_text(value):
    text = str(value or "").translate(str.maketrans("", "", _BIDI_CONTROL_CHARS))
    text = text.translate(_ARABIC_VARIANT_MAP)
    text = _ARABIC_DIACRITICS_RE.sub("", text)
    text = _WHITESPACE_RE.sub(" ", text).strip()
    return text


def normalize_transliteration_text(value):
    text = str(value or "")
    text = text.translate(_TRANSLIT_APOSTROPHE_MAP)
    text = _WHITESPACE_RE.sub(" ", text).strip()
    return text


def normalize_latin_search_text(value):
    text = normalize_transliteration_text(value).lower()
    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = text.replace("ʿ", "").replace("ʾ", "").replace("’", "")
    text = _NON_ALNUM_SPACE_RE.sub(" ", text)
    text = _WHITESPACE_RE.sub(" ", text).strip()
    return text


def transliteration_invalid_chars(value):
    text = normalize_transliteration_text(value)
    if not text:
        return []
    if _TRANSLIT_ALLOWED_RE.match(text):
        return []
    return sorted({ch for ch in text if not _TRANSLIT_ALLOWED_RE.match(ch)})


def validate_transliteration_style(value):
    bad_chars = transliteration_invalid_chars(value)
    if bad_chars:
        bad_display = ", ".join(repr(ch) for ch in bad_chars[:8])
        raise ValidationError(
            "Transliteration style error. Use Latin transliteration with diacritics only. "
            f"Unsupported characters: {bad_display}"
        )

