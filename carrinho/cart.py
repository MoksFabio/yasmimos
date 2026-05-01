from decimal import Decimal
from django.conf import settings
from produtos.models import Product
from .models import Cart as CartModel, CartItem
from django.db import transaction

class Cart:
    def __init__(self, request):
        self.session = request.session
        self.user = request.user
        
        # Initialize session dict if not exists
        carrinho_sessao = self.session.get(settings.CART_SESSION_ID)
        if not carrinho_sessao:
            carrinho_sessao = self.session[settings.CART_SESSION_ID] = {}
        self.carrinho = carrinho_sessao
        self.coupon_id = self.session.get('coupon_id')

        # If authenticated, ALWAYS load fresh from DB (Single Source of Truth)
        if self.user.is_authenticated:
            self._load_from_db()

    def _load_from_db(self):
        """
        Loads the cart strictly from the database, overwriting any stale session data.
        """
        cart_model, _ = CartModel.objects.get_or_create(user=self.user)
        db_items = CartItem.objects.filter(cart=cart_model)
        
        # Reset memory to match DB exactly
        self.carrinho = {} 
        
        for item in db_items:
            product_id = str(item.product.id)
            # Use item ID as part of key if metadata exists to allow multiple unique configurations
            item_key = f"{product_id}_{item.id}" if item.metadata else product_id
            self.carrinho[item_key] = {
                'quantity': item.quantity,
                'price': str(item.product.price),
                'metadata': item.metadata
            }
        
        # Update session so templates see correct data
        self.session[settings.CART_SESSION_ID] = self.carrinho
        self.save()

    def merge_session_to_db(self, user):
        """
        Explicitly merges the current anonymous session cart into the DB.
        """
        if not self.carrinho:
            return

        with transaction.atomic():
            cart_model, _ = CartModel.objects.get_or_create(user=user)
            
            for item_key, item_data in self.carrinho.items():
                try:
                    product_id = item_key.split('_')[0]
                    product = Product.objects.get(id=product_id)
                    quantity = item_data['quantity']
                    metadata = item_data.get('metadata')
                    
                    if metadata:
                        cart_item, created = CartItem.objects.get_or_create(
                            cart=cart_model, 
                            product=product,
                            metadata=metadata
                        )
                    else:
                        cart_item, created = CartItem.objects.get_or_create(
                            cart=cart_model, 
                            product=product,
                            metadata__isnull=True
                        )
                    
                    if created:
                        cart_item.quantity = quantity
                    else:
                        cart_item.quantity += quantity
                    
                    cart_item.save()
                except Product.DoesNotExist:
                    continue
            
            self.user = user 
            self._load_from_db()

    def add(self, product, quantity=1, override_quantity=False, metadata=None):
        product_id = str(product.id)
        
        # Stable item key for metadata
        item_key = product_id
        if metadata:
            import json
            # Use a stable sort_keys string instead of hash()
            m_str = json.dumps(metadata, sort_keys=True)
            item_key = f"{product_id}_{abs(hash(m_str))}" # Still using hash but now it's only for the session lifetime
        
        if item_key not in self.carrinho:
            self.carrinho[item_key] = {'quantity': 0, 'price': str(product.price), 'metadata': metadata}
        
        if override_quantity:
            self.carrinho[item_key]['quantity'] = quantity
        else:
            self.carrinho[item_key]['quantity'] += quantity
            
        self.save()

        if self.user.is_authenticated:
            try:
                cart_model, _ = CartModel.objects.get_or_create(user=self.user)
                # For DB, we use the stable metadata field lookup
                if metadata:
                    # Filter first, then get or create manually to be safer with JSONFields
                    cart_item = CartItem.objects.filter(cart=cart_model, product=product, metadata=metadata).first()
                    if not cart_item:
                        cart_item = CartItem.objects.create(cart=cart_model, product=product, metadata=metadata)
                        created = True
                    else:
                        created = False
                else:
                    cart_item, created = CartItem.objects.get_or_create(
                        cart=cart_model, 
                        product=product,
                        metadata__isnull=True
                    )
                
                if override_quantity:
                    cart_item.quantity = quantity
                else:
                    if created:
                         cart_item.quantity = quantity
                    else:
                         cart_item.quantity += quantity
                
                cart_item.save()
            except Exception as e:
                print(f"Error saving to DB: {e}")

    def remove(self, product, item_key=None):
        metadata = None
        if item_key and item_key in self.carrinho:
            metadata = self.carrinho[item_key].get('metadata')

        if item_key and item_key in self.carrinho:
            del self.carrinho[item_key]
        else:
            product_id = str(product.id)
            if product_id in self.carrinho:
                del self.carrinho[product_id]
        
        self.save()
            
        if self.user.is_authenticated:
            try:
                cart_model = CartModel.objects.get(user=self.user)
                if metadata:
                    CartItem.objects.filter(cart=cart_model, product=product, metadata=metadata).delete()
                else:
                    CartItem.objects.filter(cart=cart_model, product=product, metadata__isnull=True).delete()
            except CartModel.DoesNotExist:
                pass
            
    def update_quantity(self, product, item_key, quantity):
        if item_key in self.carrinho:
            self.carrinho[item_key]['quantity'] = quantity
            self.save()
            
            if self.user.is_authenticated:
                try:
                    cart_model = CartModel.objects.get(user=self.user)
                    metadata = self.carrinho[item_key].get('metadata')
                    if metadata:
                        items = CartItem.objects.filter(cart=cart_model, product=product, metadata=metadata)
                    else:
                        items = CartItem.objects.filter(cart=cart_model, product=product, metadata__isnull=True)
                    
                    for item in items:
                        item.quantity = quantity
                        item.save()
                except CartModel.DoesNotExist:
                    pass

    def clear(self):
        self.carrinho = {}
        self.session[settings.CART_SESSION_ID] = {}
        if 'coupon_id' in self.session:
            del self.session['coupon_id']
        if 'cart_tip' in self.session:
            del self.session['cart_tip']
        self.save()
        
        if self.user.is_authenticated:
            try:
                cart_model = CartModel.objects.get(user=self.user)
                cart_model.items.all().delete()
            except CartModel.DoesNotExist:
                pass

    def save(self):
        self.session.modified = True

    def __iter__(self):
        product_ids = [k.split('_')[0] for k in self.carrinho.keys()]
        products = Product.objects.filter(id__in=product_ids)
        prod_dict = {str(p.id): p for p in products}
        
        for item_key, item in self.carrinho.items():
            product_id = item_key.split('_')[0]
            if product_id in prod_dict:
                item['product'] = prod_dict[product_id]
                item['item_key'] = item_key
                item['price'] = Decimal(item['price'])
                item['total_price'] = item['price'] * item['quantity']
                yield item

    def __len__(self):
        return sum(item['quantity'] for item in self.carrinho.values())

    def get_total_price(self):
        return sum(Decimal(item['price']) * item['quantity'] for item in self.carrinho.values())
    
    def get_total_price_display(self):
        return f"{self.get_total_price():.2f}".replace('.', ',')
    
    @property
    def coupon(self):
        if self.coupon_id:
            from pedidos.models import Coupon
            try:
                return Coupon.objects.get(id=self.coupon_id)
            except Coupon.DoesNotExist:
                pass
        return None

    def get_discount(self):
        if self.coupon:
            total = self.get_total_price()
            if total >= self.coupon.min_purchase:
                from decimal import ROUND_HALF_UP
                discount = (self.coupon.discount_percentage / Decimal('100')) * total
                return discount.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        return Decimal('0.00')

    def get_tip(self):
        return Decimal(self.session.get('cart_tip', '0.00'))

    def set_tip(self, amount):
        self.session['cart_tip'] = str(amount)
        self.save()

    def get_total_price_after_discount(self):
        return self.get_total_price() - self.get_discount() + self.get_tip()
        
    def get_base_total_after_discount(self):
        return self.get_total_price() - self.get_discount()
