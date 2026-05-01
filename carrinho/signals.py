from django.contrib.auth.signals import user_logged_in
from django.dispatch import receiver
from .cart import Cart

@receiver(user_logged_in)
def merge_cart(sender, user, request, **kwargs):
    """
    When a user logs in, we should merge their anonymous session cart
    into their persistent database carrinho.
    This runs ONCE during login, not on every request.
    """
    try:
        cart = Cart(request)
        # Force a merge from the current (anonymous) session to the DB
        carrinho.merge_session_to_db(user)
    except Exception as e:
        # Failsafe: Don't block login if cart merge fails
        print(f"Error merging cart on login: {e}")
