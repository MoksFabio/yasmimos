from .cart import Cart

def cart(request):
    return {'carrinho': Cart(request)}
