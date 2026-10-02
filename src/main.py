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