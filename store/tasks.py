import threading

from django.conf import settings

from .email_utils import send_order_confirmation_email, send_order_alert_email
from .models import Order


def _run_async(func, *args, **kwargs):
    if not getattr(settings, "ASYNC_TASKS_ENABLED", False):
        return func(*args, **kwargs)

    thread = threading.Thread(target=func, args=args, kwargs=kwargs, daemon=True)
    thread.start()
    return None


def enqueue_order_confirmation(order_id):
    def _task():
        order = Order.objects.filter(id=order_id).first()
        if order:
            send_order_confirmation_email(order)

    return _run_async(_task)


def enqueue_order_alert(order_id):
    def _task():
        order = Order.objects.filter(id=order_id).first()
        if order:
            send_order_alert_email(order)

    return _run_async(_task)
