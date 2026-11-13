import math
from src.models.product import Product
from src.models.keyboard import Keyboard
from src.models.mouse import Mouse
from src.models.headphones import Headphones
from src.models.webcam import Webcam


class ProductFactory:
    """Фабрика для валідації та створення доменних об'єктів товарів."""

    SUPPORTED_CATEGORIES = {
        "keyboard": Keyboard,
        "mouse": Mouse,
        "headphones": Headphones,
        "webcam": Webcam,
    }

    @classmethod
    def validate_product_id(cls, product_id: int) -> int:
        if isinstance(product_id, bool) or not isinstance(product_id, int):
            raise ValueError("Product ID must be an integer.")
        if product_id < 0:
            raise ValueError("Product ID cannot be negative.")
        return product_id

    @classmethod
    def validate_name(cls, name: str) -> str:
        if not isinstance(name, str) or not name.strip():
            raise ValueError("Product name cannot be empty.")
        return name.strip()

    @classmethod
    def validate_brand(cls, brand: str) -> str:
        if not isinstance(brand, str) or not brand.strip():
            raise ValueError("Product brand cannot be empty.")
        return brand.strip()

    @classmethod
    def validate_category(cls, category: str) -> str:
        if not isinstance(category, str) or not category.strip():
            raise ValueError("Product category cannot be empty.")

        normalized = category.strip().lower()
        if normalized not in cls.SUPPORTED_CATEGORIES:
            raise ValueError(f"Unsupported product category: '{category}'.")
        return normalized

    @classmethod
    def validate_price(cls, price: float) -> float:
        if isinstance(price, bool) or not isinstance(price, (int, float)):
            raise ValueError("Price must be a valid number.")
        if not math.isfinite(price):
            raise ValueError("Price must be a finite number.")
        if price < 0:
            raise ValueError("Price cannot be negative.")
        return float(price)

    @classmethod
    def validate_stock_quantity(cls, stock_quantity: int) -> int:
        if isinstance(stock_quantity, bool) or not isinstance(stock_quantity, int):
            raise ValueError("Stock quantity must be an integer.")
        if stock_quantity < 0:
            raise ValueError("Stock quantity cannot be negative.")
        return stock_quantity

    @classmethod
    def validate_attributes(
        cls,
        category: str,
        attributes: dict | None = None,
        require_attributes: bool = False,
    ) -> dict:
        normalized_category = cls.validate_category(category)

        if attributes is None:
            attributes = {}

        if not isinstance(attributes, dict):
            raise ValueError("Product attributes must be a dictionary.")

        if len(attributes) == 0:
            if require_attributes:
                raise ValueError(
                    f"Category-specific attributes are required for '{normalized_category}'."
                )
            return {}

        if normalized_category == "keyboard":
            if set(attributes.keys()) != {"switch_type", "layout"}:
                raise ValueError(
                    "Keyboard attributes must contain 'switch_type' and 'layout'."
                )
            switch_type = attributes["switch_type"]
            layout = attributes["layout"]
            if not isinstance(switch_type, str) or not switch_type.strip():
                raise ValueError("Keyboard 'switch_type' must be a non-empty string.")
            if not isinstance(layout, str) or not layout.strip():
                raise ValueError("Keyboard 'layout' must be a non-empty string.")
            return {
                "switch_type": switch_type.strip(),
                "layout": layout.strip(),
            }

        if normalized_category == "mouse":
            if set(attributes.keys()) != {"dpi", "connection_type"}:
                raise ValueError(
                    "Mouse attributes must contain 'dpi' and 'connection_type'."
                )
            dpi = attributes["dpi"]
            connection_type = attributes["connection_type"]
            if isinstance(dpi, bool) or not isinstance(dpi, int) or dpi <= 0:
                raise ValueError("Mouse 'dpi' must be a positive integer.")
            if not isinstance(connection_type, str) or not connection_type.strip():
                raise ValueError("Mouse 'connection_type' must be a non-empty string.")
            return {
                "dpi": dpi,
                "connection_type": connection_type.strip(),
            }

        if normalized_category == "headphones":
            if set(attributes.keys()) != {"wireless", "has_microphone"}:
                raise ValueError(
                    "Headphones attributes must contain 'wireless' and 'has_microphone'."
                )
            wireless = attributes["wireless"]
            has_microphone = attributes["has_microphone"]
            if not isinstance(wireless, bool):
                raise ValueError("Headphones 'wireless' must be a boolean.")
            if not isinstance(has_microphone, bool):
                raise ValueError("Headphones 'has_microphone' must be a boolean.")
            return {
                "wireless": wireless,
                "has_microphone": has_microphone,
            }

        if normalized_category == "webcam":
            if set(attributes.keys()) != {"resolution", "frame_rate"}:
                raise ValueError(
                    "Webcam attributes must contain 'resolution' and 'frame_rate'."
                )
            resolution = attributes["resolution"]
            frame_rate = attributes["frame_rate"]
            if not isinstance(resolution, str) or not resolution.strip():
                raise ValueError("Webcam 'resolution' must be a non-empty string.")
            if (
                isinstance(frame_rate, bool)
                or not isinstance(frame_rate, int)
                or frame_rate <= 0
            ):
                raise ValueError("Webcam 'frame_rate' must be a positive integer.")
            return {
                "resolution": resolution.strip(),
                "frame_rate": frame_rate,
            }

        raise ValueError(f"Unsupported product category: '{category}'.")

    @classmethod
    def create_product(
        cls,
        name: str,
        brand: str,
        category: str,
        price: float,
        stock_quantity: int,
        attributes: dict | None = None,
        product_id: int = 0,
        require_attributes: bool = False,
    ) -> Product:
        validated_id = cls.validate_product_id(product_id)
        validated_name = cls.validate_name(name)
        validated_brand = cls.validate_brand(brand)
        validated_category = cls.validate_category(category)
        validated_price = cls.validate_price(price)
        validated_stock = cls.validate_stock_quantity(stock_quantity)
        validated_attrs = cls.validate_attributes(
            validated_category,
            attributes,
            require_attributes=require_attributes,
        )

        has_verified_specs = len(validated_attrs) > 0

        if validated_category == "keyboard":
            product = Keyboard(
                validated_id,
                validated_name,
                validated_brand,
                validated_price,
                validated_stock,
                validated_attrs.get("switch_type"),
                validated_attrs.get("layout"),
            )
        elif validated_category == "mouse":
            product = Mouse(
                validated_id,
                validated_name,
                validated_brand,
                validated_price,
                validated_stock,
                validated_attrs.get("dpi"),
                validated_attrs.get("connection_type"),
            )
        elif validated_category == "headphones":
            product = Headphones(
                validated_id,
                validated_name,
                validated_brand,
                validated_price,
                validated_stock,
                validated_attrs.get("wireless"),
                validated_attrs.get("has_microphone"),
            )
        elif validated_category == "webcam":
            product = Webcam(
                validated_id,
                validated_name,
                validated_brand,
                validated_price,
                validated_stock,
                validated_attrs.get("resolution"),
                validated_attrs.get("frame_rate"),
            )
        else:
            raise ValueError(f"Unsupported product category: '{category}'.")

        if not has_verified_specs:
            # Не видаємо неверифіковані характеристики за фактичний опис товару
            product.get_description = lambda: ""

        return product

    @classmethod
    def create_from_record(
        cls,
        record: dict,
        require_attributes: bool = False,
    ) -> Product:
        if not isinstance(record, dict):
            raise ValueError("Product record must be a dictionary.")

        product_id = record.get("id", record.get("product_id", 0))
        stock_quantity = (
            record["stock_quantity"]
            if "stock_quantity" in record
            else record.get("stock")
        )

        return cls.create_product(
            name=record.get("name"),
            brand=record.get("brand"),
            category=record.get("category"),
            price=record.get("price"),
            stock_quantity=stock_quantity,
            attributes=record.get("attributes"),
            product_id=product_id,
            require_attributes=require_attributes,
        )

    from_dict = create_from_record
