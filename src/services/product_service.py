from src.models.product import Product
from src.services.database import Database, UNVERIFIED_SEED_ATTRIBUTES
from src.services.product_factory import ProductFactory


class ProductService:
    """Сервіс для роботи з товарами через базу даних та фабрику доменних моделей."""

    def __init__(self, database: Database | None = None):
        self.__db = database if database is not None else Database()

    @staticmethod
    def __extract_custom_description(record: dict) -> str | None:
        raw_attributes = record.get("attributes")
        if not isinstance(raw_attributes, dict):
            return None
        custom_desc = raw_attributes.get("_description")
        if isinstance(custom_desc, str) and custom_desc.strip():
            return custom_desc.strip()
        return None

    @staticmethod
    def __sanitize_record_attributes(record: dict) -> dict:
        product_id = record.get("id")
        raw_attributes = record.get("attributes")

        if not isinstance(raw_attributes, dict):
            return {}

        cleaned = {
            k: v for k, v in raw_attributes.items()
            if k != "_description"
        }

        # Якщо у БД збережено припущені (неверифіковані) атрибути товарів 5–8
        # з попереднього сіду, не видаємо їх за підтверджені характеристики.
        if (
            product_id in UNVERIFIED_SEED_ATTRIBUTES
            and cleaned == UNVERIFIED_SEED_ATTRIBUTES[product_id]
        ):
            return {}

        return dict(cleaned)

    def __record_to_dict(self, record: dict) -> dict:
        sanitized_attributes = self.__sanitize_record_attributes(record)
        custom_description = self.__extract_custom_description(record)
        normalized_record = {
            **record,
            "attributes": sanitized_attributes,
        }

        product = ProductFactory.create_from_record(normalized_record)
        validated_category = ProductFactory.validate_category(record["category"])
        validated_attributes = ProductFactory.validate_attributes(
            validated_category,
            sanitized_attributes,
        )
        description = (
            custom_description
            if custom_description is not None
            else product.get_description()
        )

        return {
            "id": product.get_product_id(),
            "name": product.get_name(),
            "brand": product.get_brand(),
            "category": validated_category,
            "price": product.calculate_final_price(),
            "stock_quantity": product.get_stock_quantity(),
            "stock": product.get_stock_quantity(),
            "available": product.is_available(),
            "image": record.get("image"),
            "attributes": validated_attributes,
            "description": description,
        }

    def get_domain_product(self, product_id: int) -> Product | None:
        if isinstance(product_id, bool) or not isinstance(product_id, int) or product_id <= 0:
            return None

        record = self.__db.get_product_by_id(product_id)
        if record is None:
            return None

        sanitized_attributes = self.__sanitize_record_attributes(record)
        return ProductFactory.create_from_record(
            {**record, "attributes": sanitized_attributes}
        )

    def get_all_products(
        self,
        category: str | None = None,
        brand: str | list[str] | None = None,
        max_price: float | None = None,
        search: str | None = None,
    ) -> list[dict]:
        validated_max_price = None
        if max_price is not None:
            validated_max_price = ProductFactory.validate_price(max_price)

        records = self.__db.get_all_products()
        products = [self.__record_to_dict(record) for record in records]

        if category is not None and category.strip() != "":
            normalized_category = category.strip().lower()
            if normalized_category != "all":
                products = [
                    p for p in products
                    if p["category"] == normalized_category
                ]

        if brand is not None:
            if isinstance(brand, str):
                raw_brands = [brand]
            elif isinstance(brand, (list, tuple, set)):
                raw_brands = list(brand)
            else:
                raise ValueError("Brand filter must be a string or list of strings.")

            selected_brands = {
                part.strip().lower()
                for item in raw_brands
                if isinstance(item, str)
                for part in item.split(",")
                if part.strip()
            }

            if selected_brands:
                products = [
                    p for p in products
                    if p["brand"].lower() in selected_brands
                ]

        if validated_max_price is not None:
            products = [
                p for p in products
                if p["price"] <= validated_max_price
            ]

        if search is not None and search.strip() != "":
            query = search.strip().lower()
            products = [
                p for p in products
                if query in p["name"].lower()
                or query in p["brand"].lower()
                or query in p["description"].lower()
            ]

        return products

    def get_product_by_id(self, product_id: int) -> dict | None:
        if isinstance(product_id, bool) or not isinstance(product_id, int) or product_id <= 0:
            return None

        record = self.__db.get_product_by_id(product_id)
        if record is None:
            return None

        return self.__record_to_dict(record)

    def create_product(
        self,
        name: str,
        brand: str,
        category: str,
        price: float,
        stock_quantity: int,
        image: str | None = None,
        attributes: dict | None = None,
        description: str | None = None,
    ) -> dict:
        product = ProductFactory.create_product(
            name=name,
            brand=brand,
            category=category,
            price=price,
            stock_quantity=stock_quantity,
            attributes=attributes,
        )
        validated_category = ProductFactory.validate_category(category)
        validated_attributes = ProductFactory.validate_attributes(
            validated_category,
            attributes,
        )

        if image is not None and not isinstance(image, str):
            raise ValueError("Product image must be a string or None.")
        clean_image = image.strip() if isinstance(image, str) and image.strip() else None

        if description is not None and not isinstance(description, str):
            raise ValueError("Product description must be a string or None.")
        clean_description = (
            description.strip()
            if isinstance(description, str) and description.strip()
            else None
        )

        db_attributes = dict(validated_attributes)
        if clean_description is not None:
            db_attributes["_description"] = clean_description

        product_id = self.__db.create_product(
            name=product.get_name(),
            brand=product.get_brand(),
            category=validated_category,
            price=product.get_price(),
            stock_quantity=product.get_stock_quantity(),
            image=clean_image,
            attributes=db_attributes,
        )

        record = self.__db.get_product_by_id(product_id)
        return self.__record_to_dict(record)

    def update_product(
        self,
        product_id: int,
        name: str | None = None,
        brand: str | None = None,
        category: str | None = None,
        price: float | None = None,
        stock_quantity: int | None = None,
        image: str | None = None,
        attributes: dict | None = None,
        description: str | None = None,
        replace_image: bool = False,
        replace_description: bool = False,
    ) -> dict | None:
        if isinstance(product_id, bool) or not isinstance(product_id, int) or product_id <= 0:
            return None

        existing_record = self.__db.get_product_by_id(product_id)
        if existing_record is None:
            return None

        target_name = existing_record["name"] if name is None else name
        target_brand = existing_record["brand"] if brand is None else brand
        target_category = existing_record["category"] if category is None else category
        target_price = existing_record["price"] if price is None else price
        target_stock = (
            existing_record["stock_quantity"]
            if stock_quantity is None
            else stock_quantity
        )

        validated_category = ProductFactory.validate_category(target_category)
        existing_category = ProductFactory.validate_category(existing_record["category"])
        existing_attributes = self.__sanitize_record_attributes(existing_record)

        if attributes is not None:
            target_attributes = attributes
        elif validated_category != existing_category:
            target_attributes = {}
        else:
            target_attributes = existing_attributes

        product = ProductFactory.create_product(
            name=target_name,
            brand=target_brand,
            category=validated_category,
            price=target_price,
            stock_quantity=target_stock,
            attributes=target_attributes,
            product_id=product_id,
        )
        validated_attributes = ProductFactory.validate_attributes(
            validated_category,
            target_attributes,
        )

        if image is not None:
            if not isinstance(image, str):
                raise ValueError("Product image must be a string or None.")
            clean_image = image.strip() if image.strip() else None
        elif replace_image:
            clean_image = None
        else:
            clean_image = existing_record.get("image")

        existing_description = self.__extract_custom_description(existing_record)
        if description is not None:
            if not isinstance(description, str):
                raise ValueError("Product description must be a string or None.")
            clean_description = description.strip() if description.strip() else None
        elif replace_description:
            clean_description = None
        else:
            clean_description = existing_description

        db_attributes = dict(validated_attributes)
        if clean_description is not None:
            db_attributes["_description"] = clean_description

        updated = self.__db.update_product(
            product_id=product_id,
            name=product.get_name(),
            brand=product.get_brand(),
            category=validated_category,
            price=product.get_price(),
            stock_quantity=product.get_stock_quantity(),
            image=clean_image,
            attributes=db_attributes,
        )
        if not updated:
            return None

        record = self.__db.get_product_by_id(product_id)
        return self.__record_to_dict(record)

    def update_product_stock(self, product_id: int, new_stock: int) -> bool:
        validated_stock = ProductFactory.validate_stock_quantity(new_stock)
        if isinstance(product_id, bool) or not isinstance(product_id, int) or product_id <= 0:
            return False

        return self.__db.update_product_stock(product_id, validated_stock)

    def delete_product(self, product_id: int) -> bool:
        if isinstance(product_id, bool) or not isinstance(product_id, int) or product_id <= 0:
            return False

        return self.__db.delete_product(product_id)
