from src.models.keyboard import Keyboard


keyboard = Keyboard(
    product_id=1,
    name="Mechanical Keyboard",
    brand="Logitech",
    price=2500,
    stock_quantity=10,
    switch_type="Red",
    layout="US"
)

print(keyboard.get_description())
print("Available:", keyboard.is_available())
print("Price:", keyboard.calculate_final_price())