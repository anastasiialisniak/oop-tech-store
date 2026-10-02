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