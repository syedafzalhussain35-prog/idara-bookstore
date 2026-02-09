import logging
import requests

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags

logger = logging.getLogger(__name__)


def _send_via_brevo(to_email, subject, text_body, html_body):
    from_email = settings.BREVO_FROM_EMAIL
    from_name = settings.BREVO_FROM_NAME

    payload = {
        "sender": {"email": from_email, "name": from_name},
        "to": [{"email": to_email}],
        "subject": subject,
        "textContent": text_body,
        "htmlContent": html_body,
    }

    headers = {
        "api-key": settings.BREVO_API_KEY,
        "Content-Type": "application/json",
    }

    try:
        resp = requests.post(
            "https://api.brevo.com/v3/smtp/email",
            json=payload,
            headers=headers,
            timeout=10,
        )
        if resp.status_code not in (200, 201, 202):
            logger.error("Brevo error %s: %s", resp.status_code, resp.text)
    except Exception as exc:
        logger.exception("Brevo request failed: %s", exc)


def _send_via_sendgrid(to_email, subject, text_body, html_body):
    from_email = settings.SENDGRID_FROM_EMAIL
    from_name = settings.SENDGRID_FROM_NAME

    payload = {
        "personalizations": [{"to": [{"email": to_email}]}],
        "from": {"email": from_email, "name": from_name},
        "subject": subject,
        "content": [
            {"type": "text/plain", "value": text_body},
            {"type": "text/html", "value": html_body},
        ],
    }

    headers = {
        "Authorization": f"Bearer {settings.SENDGRID_API_KEY}",
        "Content-Type": "application/json",
    }

    try:
        resp = requests.post(
            "https://api.sendgrid.com/v3/mail/send",
            json=payload,
            headers=headers,
            timeout=10,
        )
        if resp.status_code not in (200, 202):
            logger.error("SendGrid error %s: %s", resp.status_code, resp.text)
    except Exception as exc:
        logger.exception("SendGrid request failed: %s", exc)


def send_order_confirmation_email(order):
    if not order.email:
        return

    subject = f"Order Confirmation #{order.id} - Idara Kitab Ul Shifa"
    html_body = render_to_string("emails/order_confirmation.html", {"order": order})
    text_body = strip_tags(html_body)

    if settings.BREVO_API_KEY:
        _send_via_brevo(
            to_email=order.email,
            subject=subject,
            text_body=text_body,
            html_body=html_body,
        )
        return

    if settings.SENDGRID_API_KEY:
        _send_via_sendgrid(
            to_email=order.email,
            subject=subject,
            text_body=text_body,
            html_body=html_body,
        )
        return

    msg = EmailMultiAlternatives(
        subject=subject,
        body=text_body,
        to=[order.email],
    )
    msg.attach_alternative(html_body, "text/html")

    try:
        msg.send(fail_silently=False)
    except Exception as exc:
        logger.exception("Order email failed to send: %s", exc)


def send_order_alert_email(order):
    recipients = [e.strip() for e in settings.ORDER_ALERT_RECIPIENTS.split(",") if e.strip()]
    if not recipients:
        return

    subject = f"New Order #{order.id} - Idara Kitab Ul Shifa"
    html_body = render_to_string("emails/order_alert.html", {"order": order})
    text_body = strip_tags(html_body)

    if settings.BREVO_API_KEY:
        for recipient in recipients:
            _send_via_brevo(
                to_email=recipient,
                subject=subject,
                text_body=text_body,
                html_body=html_body,
            )
        return

    if settings.SENDGRID_API_KEY:
        for recipient in recipients:
            _send_via_sendgrid(
                to_email=recipient,
                subject=subject,
                text_body=text_body,
                html_body=html_body,
            )
        return

    msg = EmailMultiAlternatives(
        subject=subject,
        body=text_body,
        to=recipients,
    )
    msg.attach_alternative(html_body, "text/html")
    msg.send(fail_silently=False)


def send_publish_with_us(subject, text_body, html_body):
    recipients = [e.strip() for e in settings.PUBLISH_WITH_US_RECIPIENTS.split(",") if e.strip()]
    if not recipients:
        logger.error("Publish With Us recipients not configured.")
        return

    if settings.BREVO_API_KEY:
        for recipient in recipients:
            _send_via_brevo(
                to_email=recipient,
                subject=subject,
                text_body=text_body,
                html_body=html_body,
            )
        return

    if settings.SENDGRID_API_KEY:
        for recipient in recipients:
            _send_via_sendgrid(
                to_email=recipient,
                subject=subject,
                text_body=text_body,
                html_body=html_body,
            )
        return

    msg = EmailMultiAlternatives(
        subject=subject,
        body=text_body,
        to=recipients,
    )
    msg.attach_alternative(html_body, "text/html")
    msg.send(fail_silently=False)
