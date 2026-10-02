from src.models.mouse import Mouse


mouse = Mouse(
    product_id=2,
    name="Gaming Mouse",
    brand="Logitech",
    price=1500,
    stock_quantity=20,
    dpi=12000,
    connection_type="Wireless"
)

print(mouse.get_description())
print("Available:", mouse.is_available())
print("Price:", mouse.calculate_final_price())