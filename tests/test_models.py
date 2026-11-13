import unittest

from src.models.keyboard import Keyboard
from src.models.mouse import Mouse
from src.models.cart import Cart, CartItem
from src.models.user import Customer, Admin
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


class TestGettersAndEncapsulation(unittest.TestCase):

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

    def test_product_getters(self):
        self.assertEqual(self.keyboard.get_product_id(), 1)
        self.assertEqual(self.keyboard.get_name(), "Mechanical Keyboard")
        self.assertEqual(self.keyboard.get_brand(), "Logitech")
        self.assertEqual(self.keyboard.get_price(), 2500)

    def test_cart_item_getters(self):
        item = CartItem(self.keyboard, 3)

        self.assertIs(item.get_product(), self.keyboard)
        self.assertEqual(item.get_quantity(), 3)

    def test_cart_remove_product_uses_public_getter(self):
        cart = Cart()
        cart.add_product(self.keyboard, 1)
        cart.add_product(self.mouse, 1)

        cart.remove_product(self.keyboard)

        self.assertEqual(cart.get_item_count(), 1)
        self.assertEqual(cart.calculate_total(), 1500)

    def test_cart_remove_missing_product_raises(self):
        cart = Cart()
        cart.add_product(self.keyboard, 1)

        with self.assertRaises(ValueError):
            cart.remove_product(self.mouse)

    def test_user_getters(self):
        customer = Customer(1, "Anna", "anna@gmail.com")
        admin = Admin(2, "Alex", "alex@gmail.com")

        self.assertEqual(customer.get_name(), "Anna")
        self.assertEqual(customer.get_email(), "anna@gmail.com")
        self.assertEqual(admin.get_name(), "Alex")
        self.assertEqual(admin.get_email(), "alex@gmail.com")

    def test_user_email_getter_reflects_change(self):
        customer = Customer(1, "Anna", "anna@gmail.com")
        customer.change_email("new@gmail.com")

        self.assertEqual(customer.get_email(), "new@gmail.com")


if __name__ == "__main__":
    unittest.main()
    