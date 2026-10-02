import unittest

from src.models.keyboard import Keyboard
from src.models.mouse import Mouse
from src.models.cart import Cart
from src.models.payment import CardPayment
from src.models.delivery import PickupDelivery
from src.models.order import Order


class TestProduct(unittest.TestCase):

    def setUp(self):
        self.keyboard = Keyboard(
            product_id=1,
            name="Mechanical Keyboard",
            brand="Logitech",
            price=2500,
            stock_quantity=10,
            switch_type="Red",
            layout="US"
        )

    def test_product_is_available(self):
        self.assertTrue(self.keyboard.is_available())

    def test_reduce_stock(self):
        self.keyboard.reduce_stock(3)

        self.assertEqual(
            self.keyboard.get_stock_quantity(),
            7
        )

    def test_reduce_stock_with_invalid_quantity(self):
        with self.assertRaises(ValueError):
            self.keyboard.reduce_stock(20)


class TestCart(unittest.TestCase):

    def setUp(self):
        self.keyboard = Keyboard(
            product_id=1,
            name="Mechanical Keyboard",
            brand="Logitech",
            price=2500,
            stock_quantity=10,
            switch_type="Red",
            layout="US"
        )

        self.mouse = Mouse(
            product_id=2,
            name="Gaming Mouse",
            brand="Logitech",
            price=1500,
            stock_quantity=20,
            dpi=12000,
            connection_type="Wireless"
        )

        self.cart = Cart()

    def test_add_product(self):
        self.cart.add_product(self.keyboard, 2)

        self.assertEqual(
            self.cart.get_item_count(),
            1
        )

    def test_calculate_total(self):
        self.cart.add_product(self.keyboard, 2)
        self.cart.add_product(self.mouse, 1)

        self.assertEqual(
            self.cart.calculate_total(),
            6500
        )

    def test_clear_cart(self):
        self.cart.add_product(self.keyboard, 1)
        self.cart.clear()

        self.assertTrue(self.cart.is_empty())


class TestOrder(unittest.TestCase):

    def test_order_total(self):
        keyboard = Keyboard(
            product_id=1,
            name="Mechanical Keyboard",
            brand="Logitech",
            price=2500,
            stock_quantity=10,
            switch_type="Red",
            layout="US"
        )

        payment = CardPayment(
            2655,
            "1234567890123456"
        )

        delivery = PickupDelivery(
            "Kyiv, Khreshchatyk 10"
        )

        order = Order(
            order_id=1,
            payment=payment,
            delivery=delivery
        )

        order.add_item(keyboard, 1)

        self.assertEqual(
            order.calculate_total(),
            2500
        )

    def test_order_status(self):
        payment = CardPayment(
            1000,
            "1234567890123456"
        )

        delivery = PickupDelivery(
            "Kyiv, Khreshchatyk 10"
        )

        order = Order(
            order_id=1,
            payment=payment,
            delivery=delivery
        )

        self.assertEqual(
            order.get_status(),
            "Created"
        )

        order.change_status("Paid")

        self.assertEqual(
            order.get_status(),
            "Paid"
        )


if __name__ == "__main__":
    unittest.main()
    