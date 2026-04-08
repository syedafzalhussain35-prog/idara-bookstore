import re

from django import template
from django.utils.html import conditional_escape
from django.utils.safestring import mark_safe


register = template.Library()


@register.filter(needs_autoescape=True)
def highlight_query(value, query, autoescape=True):
    text = str(value or "")
    q = str(query or "").strip()
    if not text or not q:
        return conditional_escape(text) if autoescape else text
    escaped_text = conditional_escape(text) if autoescape else text
    pattern = re.compile(re.escape(q), re.IGNORECASE)
    highlighted = pattern.sub(lambda m: f"<mark>{m.group(0)}</mark>", str(escaped_text))
    return mark_safe(highlighted)

