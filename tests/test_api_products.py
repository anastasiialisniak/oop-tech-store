from datetime import timedelta
import json as json_module
import sqlite3
import sys
import tempfile
import types
import unittest
from pathlib import Path
from urllib.parse import unquote, urlencode, urlsplit

import anyio.to_thread
from pwdlib import PasswordHash


def _ensure_httpx_for_testclient() -> None:
    """Забезпечує сумісний in-memory транспорт для FastAPI/Starlette TestClient."""
    httpx_mod = types.ModuleType("httpx2")

    class UseClientDefault:
        pass

    USE_CLIENT_DEFAULT = UseClientDefault()

    class Headers:
        def __init__(self, headers=None):
            self._items: list[tuple[str, str]] = []
            if isinstance(headers, Headers):
                self._items = list(headers._items)
            elif isinstance(headers, dict):
                self._items = [(str(k), str(v)) for k, v in headers.items()]
            elif headers is not None:
                self._items = [(str(k), str(v)) for k, v in headers]

        def __contains__(self, key: str) -> bool:
            key_lower = key.lower()
            return any(k.lower() == key_lower for k, _ in self._items)

        def get(self, key: str, default=None):
            key_lower = key.lower()
            for k, v in reversed(self._items):
                if k.lower() == key_lower:
                    return v
            return default

        def __getitem__(self, key: str) -> str:
            val = self.get(key)
            if val is None:
                raise KeyError(key)
            return val

        def setdefault(self, key: str, value: str):
            if key not in self:
                self._items.append((key, value))
            return self.get(key)

        def multi_items(self) -> list[tuple[str, str]]:
            return list(self._items)

    class URL:
        def __init__(self, url: str):
            parsed = urlsplit(url)
            self.scheme = parsed.scheme or "http"
            host = parsed.hostname or "testserver"
            self.raw_host = host.encode("ascii")
            self.port = parsed.port
            self.netloc = (parsed.netloc or host).encode("ascii")
            self.path = parsed.path or "/"
            self.query = (parsed.query or "").encode("ascii")
            raw_path = self.path
            if parsed.query:
                raw_path = f"{self.path}?{parsed.query}"
            self.raw_path = raw_path.encode("ascii")

        def __str__(self) -> str:
            q = f"?{self.query.decode('ascii')}" if self.query else ""
            return f"{self.scheme}://{self.netloc.decode('ascii')}{self.path}{q}"

    class SyncByteStream:
        def __iter__(self):
            return iter(())

        def close(self) -> None:
            pass

    class ByteStream(SyncByteStream):
        def __init__(self, data: bytes):
            self._data = data

        def __iter__(self):
            if self._data:
                yield self._data

    class BaseTransport:
        def handle_request(self, request):
            raise NotImplementedError

        def close(self) -> None:
            pass

    class Request:
        def __init__(self, method: str, url: str, headers=None, content: bytes = b""):
            self.method = method.upper()
            self.url = URL(url)
            self.headers = Headers(headers)
            self._content = content

        def read(self) -> bytes:
            return self._content

    class Response:
        def __init__(
            self,
            status_code: int = 200,
            headers=None,
            stream=None,
            content: bytes | None = None,
            request=None,
        ):
            self.status_code = status_code
            self.headers = Headers(headers)
            self.request = request
            self.extensions: dict = {}
            if content is not None:
                self.content = content
            elif stream is not None:
                chunks = list(stream)
                if hasattr(stream, "close"):
                    stream.close()
                self.content = b"".join(chunks)
            else:
                self.content = b""

        @property
        def text(self) -> str:
            return self.content.decode("utf-8")

        def json(self):
            return json_module.loads(self.text)

    class Client:
        def __init__(
            self,
            base_url: str = "http://testserver",
            headers=None,
            transport=None,
            follow_redirects: bool = True,
            cookies=None,
        ):
            self.base_url = base_url.rstrip("/")
            self.headers = Headers(headers)
            self._transport = transport
            self.follow_redirects = follow_redirects
            self.cookies = cookies

        def _merge_url(self, url: str) -> str:
            if str(url).startswith(("http://", "https://", "ws://", "wss://")):
                return str(url)
            path = str(url)
            if not path.startswith("/"):
                path = "/" + path
            return f"{self.base_url}{path}"

        def request(
            self,
            method: str,
            url: str,
            *,
            content=None,
            data=None,
            files=None,
            json=None,
            params=None,
            headers=None,
            cookies=None,
            auth=USE_CLIENT_DEFAULT,
            follow_redirects=USE_CLIENT_DEFAULT,
            timeout=USE_CLIENT_DEFAULT,
            extensions=None,
        ) -> Response:
            merged_url = self._merge_url(url)
            if params:
                query_str = urlencode(params, doseq=True)
                sep = "&" if "?" in merged_url else "?"
                merged_url = f"{merged_url}{sep}{query_str}"

            combined_headers = self.headers.multi_items()
            if headers:
                combined_headers.extend(Headers(headers).multi_items())

            body_bytes = b""
            if json is not None:
                body_bytes = json_module.dumps(json).encode("utf-8")
                if not any(k.lower() == "content-type" for k, _ in combined_headers):
                    combined_headers.append(("content-type", "application/json"))
            elif isinstance(content, bytes):
                body_bytes = content
            elif isinstance(content, str):
                body_bytes = content.encode("utf-8")

            req = Request(
                method=method,
                url=merged_url,
                headers=combined_headers,
                content=body_bytes,
            )
            return self._transport.handle_request(req)

        def get(self, url: str, **kwargs) -> Response:
            return self.request("GET", url, **kwargs)

        def post(self, url: str, **kwargs) -> Response:
            return self.request("POST", url, **kwargs)

        def delete(self, url: str, **kwargs) -> Response:
            return self.request("DELETE", url, **kwargs)

        def put(self, url: str, **kwargs) -> Response:
            return self.request("PUT", url, **kwargs)

        def patch(self, url: str, **kwargs) -> Response:
            return self.request("PATCH", url, **kwargs)

    client_mod = types.ModuleType("httpx2._client")
    client_mod.USE_CLIENT_DEFAULT = USE_CLIENT_DEFAULT
    client_mod.UseClientDefault = UseClientDefault

    types_mod = types.ModuleType("httpx2._types")

    httpx_mod.USE_CLIENT_DEFAULT = USE_CLIENT_DEFAULT
    httpx_mod.Headers = Headers
    httpx_mod.URL = URL
    httpx_mod.SyncByteStream = SyncByteStream
    httpx_mod.ByteStream = ByteStream
    httpx_mod.BaseTransport = BaseTransport
    httpx_mod.Request = Request
    httpx_mod.Response = Response
    httpx_mod.Client = Client
    httpx_mod._client = client_mod
    httpx_mod._types = types_mod

    sys.modules["httpx2"] = httpx_mod
    sys.modules["httpx2._client"] = client_mod
    sys.modules["httpx2._types"] = types_mod


_ensure_httpx_for_testclient()

import starlette.testclient as _starlette_tc  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from src.api.dependencies import (  # noqa: E402
    get_current_user,
    get_optional_user,
    get_user_service,
    require_admin,
)
from src.api.main import app  # noqa: E402
from src.api.products import get_product_service  # noqa: E402
from src.models.user import Admin, Customer  # noqa: E402
from src.services.database import Database  # noqa: E402
from src.services.product_service import ProductService  # noqa: E402
from src.services.token_service import create_access_token, verify_access_token  # noqa: E402
from src.services.user_service import UserService  # noqa: E402


async def _direct_run_sync(func, *args, abandon_on_cancel=False, limiter=None):
    return func(*args)


def _in_memory_handle_request(self, request):
    """Виконує ASGI-запит у пам'яті без створення сокетів Windows."""
    scheme = request.url.scheme
    host = request.url.raw_host.decode("ascii")
    path = request.url.path
    raw_path = request.url.raw_path
    query = request.url.query.decode("ascii")
    port = request.url.port or (443 if scheme in {"https", "wss"} else 80)

    headers = []
    if "host" not in request.headers:
        headers.append((b"host", request.url.netloc))
    headers.extend(
        (k.lower().encode("latin-1"), v.encode("latin-1"))
        for k, v in request.headers.multi_items()
    )

    scope = {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": request.method,
        "path": unquote(path),
        "raw_path": raw_path.split(b"?", 1)[0],
        "root_path": self.root_path,
        "scheme": scheme,
        "query_string": query.encode("ascii"),
        "headers": headers,
        "client": self.client,
        "server": [host, port],
        "extensions": {"http.response.debug": {}, "http.response.trailers": {}},
        "state": self.app_state.copy(),
    }

    body_bytes = request.read() or b""
    request_received = False
    status_code = 500
    response_headers = []
    body_chunks: list[bytes] = []

    async def receive():
        nonlocal request_received
        if not request_received:
            request_received = True
            return {"type": "http.request", "body": body_bytes, "more_body": False}
        return {"type": "http.disconnect"}

    async def send(message):
        nonlocal status_code, response_headers
        if message["type"] == "http.response.start":
            status_code = message["status"]
            response_headers = [
                (k.decode("latin-1"), v.decode("latin-1"))
                for k, v in message.get("headers", [])
            ]
        elif message["type"] == "http.response.body":
            body_chunks.append(bytes(message.get("body", b"")))

    original_run_sync = anyio.to_thread.run_sync
    anyio.to_thread.run_sync = _direct_run_sync
    try:
        coro = self.app(scope, receive, send)
        try:
            while True:
                coro.send(None)
        except StopIteration:
            pass
    finally:
        anyio.to_thread.run_sync = original_run_sync

    return _starlette_tc.httpx.Response(
        status_code=status_code,
        headers=response_headers,
        content=b"".join(body_chunks),
        request=request,
    )


_starlette_tc._TestClientTransport.handle_request = _in_memory_handle_request


class DatabaseForTest(Database):
    """Ізольована тестова база даних SQLite у тимчасовому файлі."""

    def __init__(self, database_path: Path):
        self.database_path = database_path
        self.initialize()

    def connect(self):
        connection = sqlite3.connect(self.database_path)
        connection.execute("PRAGMA foreign_keys = ON")
        return connection


class TestProductsAPI(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.database_path = Path(self.temp_dir.name) / "test_api.sqlite3"
        self.database = DatabaseForTest(self.database_path)
        self.service = ProductService(self.database)
        self.user_service = UserService(self.database)

        password_hasher = PasswordHash.recommended()
        self.customer_id = self.database.create_user(
            name="Test Customer",
            email="customer@nexora.ua",
            password_hash=password_hasher.hash("CustomerPass123!"),
            role="Customer",
        )
        self.admin_id = self.database.create_user(
            name="Test Admin",
            email="admin@nexora.ua",
            password_hash=password_hasher.hash("AdminPass123!"),
            role="Admin",
        )

        self.customer_token = create_access_token(
            user_id=self.customer_id,
            role="Customer",
        )
        self.admin_token = create_access_token(
            user_id=self.admin_id,
            role="Admin",
        )

        self.customer_headers = {
            "Authorization": f"Bearer {self.customer_token}"
        }
        self.admin_headers = {
            "Authorization": f"Bearer {self.admin_token}"
        }

        app.dependency_overrides[get_product_service] = lambda: self.service
        app.dependency_overrides[get_user_service] = lambda: self.user_service
        self.client = TestClient(app)

    def tearDown(self):
        app.dependency_overrides.clear()
        self.temp_dir.cleanup()

    def test_get_all_products(self):
        response = self.client.get("/products")

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data), 8)
        self.assertEqual([item["id"] for item in data], [1, 2, 3, 4, 5, 6, 7, 8])

        self.assertEqual(
            data[0]["description"],
            "Keyboard with Red switches and US layout.",
        )
        for item in data[4:]:
            self.assertEqual(item["attributes"], {})
            self.assertEqual(item["description"], "")

    def test_get_products_with_filters(self):
        res_cat = self.client.get("/products", params={"category": "mouse"})
        self.assertEqual(res_cat.status_code, 200)
        self.assertEqual([p["id"] for p in res_cat.json()], [2, 6])

        res_brand = self.client.get(
            "/products",
            params={"brand": ["HyperX", "Sony"]},
        )
        self.assertEqual(res_brand.status_code, 200)
        self.assertEqual([p["id"] for p in res_brand.json()], [3, 7])

        res_price = self.client.get("/products", params={"max_price": 2200})
        self.assertEqual(res_price.status_code, 200)
        self.assertEqual([p["id"] for p in res_price.json()], [2, 4, 5])

        res_search = self.client.get("/products", params={"search": "Head"})
        self.assertEqual(res_search.status_code, 200)
        self.assertEqual([p["id"] for p in res_search.json()], [3, 7])

        res_bad_price = self.client.get("/products", params={"max_price": -10})
        self.assertEqual(res_bad_price.status_code, 400)

    def test_get_product_by_id_success_and_not_found(self):
        res_ok = self.client.get("/products/1")
        self.assertEqual(res_ok.status_code, 200)
        item = res_ok.json()
        self.assertEqual(item["id"], 1)
        self.assertEqual(item["name"], "Mechanical Keyboard")
        self.assertEqual(item["brand"], "Logitech")
        self.assertEqual(item["category"], "keyboard")
        self.assertEqual(item["price"], 2500.0)
        self.assertEqual(item["stock_quantity"], 10)

        res_missing = self.client.get("/products/999")
        self.assertEqual(res_missing.status_code, 404)

    def test_post_create_product_success_and_validation_errors(self):
        payload = {
            "name": "Ultra Gaming Mouse",
            "brand": "SteelSeries",
            "category": "mouse",
            "price": 3100,
            "stock_quantity": 9,
            "image": "images/steelseries.jpg",
            "attributes": {"dpi": 18000, "connection_type": "Wireless"},
        }
        res_created = self.client.post(
            "/products",
            json=payload,
            headers=self.admin_headers,
        )
        self.assertEqual(res_created.status_code, 201)
        created = res_created.json()
        self.assertEqual(created["id"], 9)
        self.assertEqual(created["name"], "Ultra Gaming Mouse")
        self.assertEqual(
            created["description"],
            "Mouse with 18000 DPI and Wireless connection.",
        )

        invalid_payloads = [
            {**payload, "name": ""},
            {**payload, "brand": "   "},
            {**payload, "category": "monitor"},
            {**payload, "price": -50},
            {**payload, "stock_quantity": 2.5},
            {**payload, "stock_quantity": -1},
            {**payload, "attributes": {"dpi": -10, "connection_type": "Wired"}},
        ]
        for bad_payload in invalid_payloads:
            res_bad = self.client.post(
                "/products",
                json=bad_payload,
                headers=self.admin_headers,
            )
            self.assertEqual(res_bad.status_code, 400)

        self.assertEqual(len(self.client.get("/products").json()), 9)

    def test_delete_product_success_and_not_found(self):
        res_del = self.client.delete(
            "/products/1",
            headers=self.admin_headers,
        )
        self.assertEqual(res_del.status_code, 200)
        self.assertEqual(res_del.json()["id"], 1)

        res_get = self.client.get("/products/1")
        self.assertEqual(res_get.status_code, 404)

        res_del_again = self.client.delete(
            "/products/1",
            headers=self.admin_headers,
        )
        self.assertEqual(res_del_again.status_code, 404)

    def test_missing_or_invalid_authentication_returns_401(self):
        payload = {
            "name": "New Webcam",
            "brand": "Logitech",
            "category": "webcam",
            "price": 2500,
            "stock_quantity": 5,
        }

        # Без заголовка Authorization
        self.assertEqual(self.client.post("/products", json=payload).status_code, 401)
        self.assertEqual(self.client.delete("/products/1").status_code, 401)

        expired_token = create_access_token(
            user_id=self.admin_id,
            role="Admin",
            expires_delta=timedelta(minutes=-10),
        )
        non_existent_user_token = create_access_token(
            user_id=9999,
            role="Admin",
        )

        for bad_auth in (
            "",
            "Basic abcdef",
            "Bearer",
            "Bearer invalid.jwt.token",
            f"Bearer {expired_token}",
            f"Bearer {non_existent_user_token}",
        ):
            headers = {"Authorization": bad_auth}
            self.assertEqual(
                self.client.post("/products", json=payload, headers=headers).status_code,
                401,
            )
            self.assertEqual(
                self.client.delete("/products/1", headers=headers).status_code,
                401,
            )

        self.assertEqual(len(self.client.get("/products").json()), 8)

    def test_customer_denied_access_to_admin_endpoints_403(self):
        payload = {
            "name": "Attempted Product",
            "brand": "Logitech",
            "category": "mouse",
            "price": 1200,
            "stock_quantity": 3,
        }

        res_post = self.client.post(
            "/products",
            json=payload,
            headers=self.customer_headers,
        )
        self.assertEqual(res_post.status_code, 403)

        res_del = self.client.delete(
            "/products/1",
            headers=self.customer_headers,
        )
        self.assertEqual(res_del.status_code, 403)

        # Навіть якщо у JWT підроблено/застаріло "role": "Admin", роль перевіряється за БД
        forged_role_token = create_access_token(
            user_id=self.customer_id,
            role="Admin",
        )
        res_forged = self.client.post(
            "/products",
            json=payload,
            headers={"Authorization": f"Bearer {forged_role_token}"},
        )
        self.assertEqual(res_forged.status_code, 403)

        self.assertEqual(len(self.client.get("/products").json()), 8)

    def test_auth_endpoints_for_customer_and_admin(self):
        # Реєстрація нового клієнта
        res_reg = self.client.post(
            "/auth/register",
            json={
                "name": "Olena",
                "email": "olena@nexora.ua",
                "password": "StrongPassword1!",
            },
        )
        self.assertEqual(res_reg.status_code, 200)
        reg_data = res_reg.json()
        self.assertIn("access_token", reg_data)
        self.assertEqual(reg_data["user"]["role"], "Customer")

        # Вхід клієнта
        res_cust_login = self.client.post(
            "/auth/login",
            json={
                "email": "customer@nexora.ua",
                "password": "CustomerPass123!",
            },
        )
        self.assertEqual(res_cust_login.status_code, 200)
        self.assertEqual(res_cust_login.json()["user"]["role"], "Customer")

        # Вхід адміністратора
        res_admin_login = self.client.post(
            "/auth/login",
            json={
                "email": "admin@nexora.ua",
                "password": "AdminPass123!",
            },
        )
        self.assertEqual(res_admin_login.status_code, 200)
        admin_login_data = res_admin_login.json()
        self.assertEqual(admin_login_data["user"]["role"], "Admin")

        # Використання токена з /auth/login для адмін-дії
        res_admin_delete = self.client.delete(
            "/products/8",
            headers={"Authorization": f"Bearer {admin_login_data['access_token']}"},
        )
        self.assertEqual(res_admin_delete.status_code, 200)

        # Невірні облікові дані повертають 401
        res_bad_login = self.client.post(
            "/auth/login",
            json={
                "email": "admin@nexora.ua",
                "password": "WrongPassword!",
            },
        )
        self.assertEqual(res_bad_login.status_code, 401)

    def test_dependencies_directly(self):
        # get_optional_user без заголовка повертає None
        self.assertIsNone(
            get_optional_user(authorization=None, service=self.user_service)
        )

        # get_optional_user та get_current_user з валідним заголовком повертають доменний об'єкт
        cust = get_current_user(
            authorization=f"Bearer {self.customer_token}",
            service=self.user_service,
        )
        self.assertIsInstance(cust, Customer)

        admin = get_optional_user(
            authorization=f"Bearer {self.admin_token}",
            service=self.user_service,
        )
        self.assertIsInstance(admin, Admin)
        self.assertIs(require_admin(current_user=admin), admin)

    def test_put_and_patch_update_product_admin_and_rbac(self):
        update_payload = {
            "name": "Mechanical Keyboard Elite",
            "brand": "Keychron",
            "category": "keyboard",
            "price": 3400,
            "stock_quantity": 18,
            "image": "images/keyboard-elite.jpg",
            "attributes": {"switch_type": "Blue", "layout": "UA"},
            "description": "Оновлена клавіатура з українською розкладкою.",
        }

        # Без авторизації -> 401
        self.assertEqual(
            self.client.put("/products/1", json=update_payload).status_code,
            401,
        )
        self.assertEqual(
            self.client.patch("/products/1", json={"price": 2900}).status_code,
            401,
        )

        # Клієнт (Customer) -> 403
        self.assertEqual(
            self.client.put(
                "/products/1",
                json=update_payload,
                headers=self.customer_headers,
            ).status_code,
            403,
        )
        self.assertEqual(
            self.client.patch(
                "/products/1",
                json={"price": 2900},
                headers=self.customer_headers,
            ).status_code,
            403,
        )

        # Адміністратор оновлює товар через PUT -> 200
        res_put = self.client.put(
            "/products/1",
            json=update_payload,
            headers=self.admin_headers,
        )
        self.assertEqual(res_put.status_code, 200)
        updated = res_put.json()
        self.assertEqual(updated["id"], 1)
        self.assertEqual(updated["name"], "Mechanical Keyboard Elite")
        self.assertEqual(updated["brand"], "Keychron")
        self.assertEqual(updated["price"], 3400.0)
        self.assertEqual(updated["stock_quantity"], 18)
        self.assertEqual(
            updated["attributes"],
            {"switch_type": "Blue", "layout": "UA"},
        )
        self.assertEqual(
            updated["description"],
            "Оновлена клавіатура з українською розкладкою.",
        )

        # Часткове оновлення через PATCH (очищення кастомного опису + зміна залишку)
        res_patch = self.client.patch(
            "/products/1",
            json={"stock_quantity": 7, "description": ""},
            headers=self.admin_headers,
        )
        self.assertEqual(res_patch.status_code, 200)
        patched = res_patch.json()
        self.assertEqual(patched["stock_quantity"], 7)
        self.assertEqual(
            patched["description"],
            "Keyboard with Blue switches and UA layout.",
        )

        # Некоректні дані повертають 400
        res_bad = self.client.put(
            "/products/1",
            json={**update_payload, "price": -100},
            headers=self.admin_headers,
        )
        self.assertEqual(res_bad.status_code, 400)

        # Неіснуючий товар повертає 404
        res_missing = self.client.put(
            "/products/999",
            json=update_payload,
            headers=self.admin_headers,
        )
        self.assertEqual(res_missing.status_code, 404)

    def test_public_registration_always_creates_customer_even_if_admin_role_submitted(self):
        response = self.client.post(
            "/auth/register",
            json={
                "name": "Attempted Admin",
                "email": "attempted.admin@nexora.ua",
                "password": "Password123!",
                "role": "Admin",
            },
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["user"]["role"], "Customer")

        payload = verify_access_token(data["access_token"])
        self.assertIsNotNone(payload)
        self.assertEqual(payload["role"], "Customer")

        # Цей користувач не може отримати доступ до адмінських ендпоінтів
        headers = {"Authorization": f"Bearer {data['access_token']}"}
        res_create = self.client.post(
            "/products",
            json={
                "name": "Unauthorized Item",
                "brand": "Logitech",
                "category": "mouse",
                "price": 999.0,
                "stock_quantity": 5,
            },
            headers=headers,
        )
        self.assertEqual(res_create.status_code, 403)


if __name__ == "__main__":
    unittest.main()
