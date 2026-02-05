from django.contrib.auth.signals import user_logged_in
from django.dispatch import receiver

from .models import Cart, CartItem, CartBundleItem


@receiver(user_logged_in)
def merge_guest_cart(sender, request, user, **kwargs):
    cart_id = request.session.get("cart_id")
    if not cart_id:
        return

    guest_cart = Cart.objects.filter(id=cart_id, user__isnull=True).first()
    if not guest_cart:
        return

    user_cart, _ = Cart.objects.get_or_create(user=user)

    for item in guest_cart.items.select_related("book"):
        user_item, created = CartItem.objects.get_or_create(
            cart=user_cart,
            book=item.book,
            defaults={"quantity": item.quantity},
        )
        if not created:
            user_item.quantity += item.quantity
            user_item.save()

    for bundle_item in guest_cart.bundle_items.select_related("bundle"):
        user_bundle, created = CartBundleItem.objects.get_or_create(
            cart=user_cart,
            bundle=bundle_item.bundle,
            defaults={"quantity": bundle_item.quantity},
        )
        if not created:
            user_bundle.quantity += bundle_item.quantity
            user_bundle.save()

    guest_cart.items.all().delete()
    guest_cart.bundle_items.all().delete()
    guest_cart.delete()
    request.session.pop("cart_id", None)
    request.session.modified = True
