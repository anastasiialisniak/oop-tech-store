from src.models.product import Product
from src.models.keyboard import Keyboard
from src.models.mouse import Mouse
from src.models.headphones import Headphones
from src.models.webcam import Webcam


keyboard = Keyboard(
    product_id=1,
    name="Mechanical Keyboard",
    brand="Logitech",
    price=2500,
    stock_quantity=10,
    switch_type="Red",
    layout="US"
)

mouse = Mouse(
    product_id=2,
    name="Gaming Mouse",
    brand="Logitech",
    price=1500,
    stock_quantity=20,
    dpi=12000,
    connection_type="Wireless"
)

headphones = Headphones(
    product_id=3,
    name="Gaming Headset",
    brand="HyperX",
    price=3200,
    stock_quantity=15,
    wireless=True,
    has_microphone=True
)

webcam = Webcam(
    product_id=4,
    name="Full HD Webcam",
    brand="Logitech",
    price=2200,
    stock_quantity=8,
    resolution="1920x1080",
    frame_rate=60
)


products: list[Product] = [
    keyboard,
    mouse,
    headphones,
    webcam
]


for product in products:
    print(product.get_description())


from src.models.user import Customer, Admin

users = [
    Customer(1, "Anna", "anna@gmail.com"),
    Admin(2, "Alex", "alex@gmail.com")
]

for user in users:
    print(user.get_role())

from src.models.payment import CardPayment, CashPayment


payments = [
    CardPayment(2500, "1234567890123456"),
    CashPayment(1500)
]

for payment in payments:
    print(payment.process_payment())

from src.models.delivery import CourierDelivery, PickupDelivery


deliveries = [
    CourierDelivery("Kyiv, Khreshchatyk 1", 5),
    PickupDelivery("Kyiv, Khreshchatyk 10")
]

for delivery in deliveries:
    print(delivery.calculate_cost())
    print(delivery.estimate_delivery_time())

from src.models.cart import Cart

cart = Cart()

cart.add_product(keyboard, 2)
cart.add_product(mouse, 1)

print("Cart total:", cart.calculate_total())
print("Items in cart:", cart.get_item_count())

cart.remove_product(mouse)

print("After removing mouse:")
print("Cart total:", cart.calculate_total())
print("Items in cart:", cart.get_item_count())


cart.clear()

print("After clearing cart:")
print("Cart total:", cart.calculate_total())
print("Is cart empty:", cart.is_empty())


from src.models.order import Order

order = Order(
    order_id=1,
    payment=CardPayment(6500, "1234567890123456"),
    delivery=CourierDelivery(
        "Kyiv, Khreshchatyk 1",
        5
    )
)

print("Keyboard stock before order:", keyboard.get_stock_quantity())
order.add_item(keyboard, 2)
order.add_item(mouse, 1)
print("Keyboard stock after order:", keyboard.get_stock_quantity())
      
print("Order total:", order.calculate_total())
print("Order status:", order.get_status())

order.change_status("Paid")

print("New order status:", order.get_status())
print("Can cancel:", order.can_be_cancelled())

customer = Customer(
    1,
    "Anna",
    "anna@gmail.com"
)

customer.add_to_wishlist(keyboard)
customer.add_to_wishlist(headphones)

print("Wishlist size:", len(customer.get_wishlist()))


customer.add_order(order)

print("Order history:", len(customer.get_order_history()))
print("Customer orders:", customer.get_order_count())

test_mouse = Mouse(
    product_id=10,
    name="Test Mouse",
    brand="Test",
    price=1000,
    stock_quantity=2,
    dpi=8000,
    connection_type="Wired"
)
try:
    test_mouse.reduce_stock(5)
except ValueError as error:
    print("Error:", error)


from src.services.repository import Repository

product_repository = Repository[Product]()

product_repository.add(keyboard)
product_repository.add(mouse)

print("Products in repository:", product_repository.count())


customer_repository = Repository[Customer]()

customer_repository.add(customer)

print("Customers in repository:", customer_repository.count())