from cart.models import Cart, CartItem
from wishlist.models import Wishlist  # Updated import

def cart_wishlist_counts(request):
    cart_items_count = 0
    wishlist_items_count = 0

    if request.user.is_authenticated:
        cart, created = Cart.objects.get_or_create(user=request.user)
        cart_items_count = cart.items.count()
        wishlist_items_count = Wishlist.objects.filter(user=request.user).count()

    return {
        'cart_items': cart_items_count,
        'wishlist_items': wishlist_items_count,
    }