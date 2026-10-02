from src.models.webcam import Webcam


webcam = Webcam(
    product_id=4,
    name="Full HD Webcam",
    brand="Logitech",
    price=2200,
    stock_quantity=8,
    resolution="1920x1080",
    frame_rate=60
)

print(webcam.get_description())
print("Available:", webcam.is_available())
print("Price:", webcam.calculate_final_price())