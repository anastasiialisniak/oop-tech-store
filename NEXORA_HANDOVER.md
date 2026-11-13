# Документ передачі проєкту Nexora (Handover Document)

> **Дата створення:** 12 листопада 2026 року  
> **Призначення:** Повний технічний звіт та інструкція для передачі та продовження розробки проєкту **Nexora** під іншим обліковим записом Google.  
> **Статус репозиторію:** Чистий робочий стан, зміни збережені локально, git-коміти та пуші не виконувалися.

---

## 1. Загальний огляд проєкту, мета та технологічний стек

### 1.1. Мета проєкту
**Nexora** — це навчальний курсовий проєкт з університетської дисципліни **«Об'єктно-орієнтоване програмування» (ООП)**. Проєкт є повнофункціональним інтернет-магазином сучасної комп'ютерної периферії (клавіатури, мишки, навушники, вебкамери).

Головна академічна мета — продемонструвати практичне застосування фундаментальних принципів ООП (інкапсуляція, абстракція, успадкування, поліморфізм, узагальнені типи / Generics, патерни проєктування) у поєднанні з сучасною клієнт-серверною веб-архітектурою.

### 1.2. Технологічний стек
- **Мова бекенду:** Python 3.14.
- **Веб-фреймворк API:** FastAPI 0.162.5 (ASGI, OpenAPI / Swagger документація).
- **Сервер застосунків:** Uvicorn 0.54.0.
- **База даних:** SQLite3 (`db.sqlite3`), вбудований драйвер `sqlite3`.
- **Безпека та автентифікація:**
  - `pwdlib` (Argon2) — хешування паролів.
  - `PyJWT` (JWT HS256) — випуск та перевірка токенів доступу (час життя 30 хв).
  - Pydantic v2 — валідація схем запитів.
- **Фронтенд:**
  - Чистий Vanilla JavaScript (ES6+), HTML5, CSS3 (без важких сторонніх фреймворків).
  - Односторінковий інтерфейс (SPA) з клієнтським роутингом між секціями.
  - Адаптивний та чуйний дизайн (Desktop, Tablet, Mobile) у фірмовій світло-зеленій палітрі Nexora.
- **Тестування:**
  - Вбудований фреймворк Python `unittest`.
  - Власні E2E та DOM-тести для перевірки інтерфейсу.

---

## 2. Структура проєкту та важливі файли

```text
oop-tech-store/
├── .env                             # Конфігурація секретів (JWT_SECRET_KEY, алгоритм, час життя)
├── .gitignore                       # Налаштування виключень Git (venv, pycache, logs)
├── db.sqlite3                       # База даних SQLite (містить таблицю users)
├── README.md                        # Початковий опис структури проєкту
├── NEXORA_HANDOVER.md               # Цей документ передачі
│
├── src/
│   ├── config.py                    # Завантаження змінних середовища з .env
│   ├── main.py                      # Демонстраційний консольний скрипт для перевірки ООП-моделей
│   │
│   ├── api/                         # Рівень маршрутизації FastAPI
│   │   ├── main.py                  # Ініціалізація FastAPI, налаштування CORS-middleware
│   │   └── auth.py                  # Роути автентифікації (/auth/register, /auth/login)
│   │
│   ├── models/                      # Доменні ООП-моделі предметної області
│   │   ├── product.py               # Базовий абстрактний клас Product(ABC)
│   │   ├── keyboard.py              # Підклас Keyboard(Product)
│   │   ├── mouse.py                 # Підклас Mouse(Product)
│   │   ├── headphones.py            # Підклас Headphones(Product)
│   │   ├── webcam.py                # Підклас Webcam(Product)
│   │   ├── cart.py                  # Класи CartItem та Cart
│   │   ├── order.py                 # Класи OrderItem та Order
│   │   ├── delivery.py              # Ієрархія доставки: Delivery(ABC), CourierDelivery, PickupDelivery
│   │   ├── payment.py               # Ієрархія оплати: Payment(ABC), CardPayment, CashPayment
│   │   └── user.py                  # Ієрархія користувачів: User(ABC), Customer, Admin
│   │
│   ├── services/                    # Сервісний рівень бізнес-логіки та персистенції
│   │   ├── database.py              # Клас Database (підключення та SQL для таблиці users)
│   │   ├── repository.py            # Generic-клас Repository[T] (in-memory)
│   │   ├── token_service.py         # Створення (create) та верифікація (verify) JWT токенів
│   │   └── user_service.py          # Бізнес-логіка реєстрації, входу та пошуку користувачів
│   │
│   └── web/                         # Клієнтська частина (Frontend SPA)
│       ├── index.html               # Головна розмітка (Каталог, Кошик, Оформлення, Замовлення, Кабінет, Адмінка)
│       ├── styles.css               # Стилі магазину, адаптивність, стилі для Toast-повідомлення
│       ├── app.js                   # Клієнтська логіка фільтрів, кошика, замовлень, кабінету та тосту
│       └── images/                  # Зображення товарів каталогу (*.jpg.jpg)
│
└── tests/                           # Автоматизовані модульні тести
    ├── test_models.py               # Unit-тести для Product, Cart, Order
    └── test_user_service.py         # Unit-тести для UserService з мок-базою даних
```

---

## 3. Стан реалізації функціоналу (Feature Status)

| Функція | Де реалізовано | Стан | Опис і деталі |
| :--- | :--- | :---: | :--- |
| **Реєстрація користувача** | `src/api/auth.py`, `src/services/user_service.py` | **Повністю готово** | Валідація через Pydantic, хешування пароля через Argon2, запис у SQLite, повернення JWT. |
| **Вхід (Login)** | `src/api/auth.py`, `src/services/user_service.py` | **Повністю готово** | Звірка пароля, генерація токена, авторизація у фронтенді через `sessionStorage`. |
| **Особистий кабінет** | `src/web/app.js:823-966`, `src/web/index.html` | **Повністю готово** | Вкладки Вхід/Реєстрація, перегляд профілю авторизованого юзера, вихід (Logout). |
| **Каталог товарів** | `src/web/app.js:158-238` | **Працює локально** | Відображення карток товарів, перемикання сітка / список, кнопка «Додати в кошик». |
| **Фільтрація каталогу** | `src/web/app.js:158-192`, `styles.css:538-556` | **Повністю готово** | Категорії (кнопки), слайдер максимальної ціни, мульти-чекбокси брендів, пошук, сортування. |
| **Toast-сповіщення** | `src/web/app.js:245-296`, `styles.css:1008-1052` | **Повністю готово** | Текст: *«Товар додано до кошика»*, тривалість 3 сек, правий нижній кут, плавна зелена анімація. |
| **Кошик (Cart)** | `src/web/app.js:299-400` | **Працює локально** | Додавання, зміна кількості (+/-), видалення, очищення, живий підрахунок загальної суми. |
| **Оформлення замовлення** | `src/web/app.js:686-756` | **Працює локально** | Валідація залишку, вибір способу доставки та оплати, запис у `localStorage`. |
| **Таблиця замовлень** | `src/web/app.js:405-435` | **Працює локально** | Відображення замовлень покупця з `localStorage`. |
| **Панель адміна: Товари** | `src/web/app.js:517-597, 762-799` | **Працює локально** | Створення товару у формі та видалення товару (зберігається лише в пам'яті вкладки). |
| **Панель адміна: Замовлення**| `src/web/app.js:441-511` | **Працює локально** | Зміна статусів замовлень (Нове -> Підтверджено тощо) у `localStorage`. |
| **Python ООП-моделі** | `src/models/*` | **Готово ізольовано** | Усі класи реалізовані та протестовані, але не підключені до REST API магазину. |

---

## 4. Архітектура класів ООП (Object-Oriented Programming)

У проєкті реалізовано 4 повноцінні доменні ієрархії:

### 4.1. Ієрархія товарів (`src/models/product.py` та підкласи)
- **`Product(ABC)`** — базовий абстрактний клас:
  - *Приватні поля:* `__product_id`, `__name`, `__brand`, `__price`, `__stock_quantity`.
  - *Методи:* `is_available()`, `get_stock_quantity()`, `reduce_stock(qty)`, `increase_stock(qty)`, `apply_discount(percent)`, `calculate_final_price()`.
  - *Абстрактний метод:* `@abstractmethod def get_description(self) -> str`.
- **`Keyboard(Product)`** ([`src/models/keyboard.py`](file:///c:/Users/anast/OneDrive/Desktop/oop.store/oop-tech-store/src/models/keyboard.py)): додає `__switch_type`, `__layout`.
- **`Mouse(Product)`** ([`src/models/mouse.py`](file:///c:/Users/anast/OneDrive/Desktop/oop.store/oop-tech-store/src/models/mouse.py)): додає `__dpi`, `__connection_type`.
- **`Headphones(Product)`** ([`src/models/headphones.py`](file:///c:/Users/anast/OneDrive/Desktop/oop.store/oop-tech-store/src/models/headphones.py)): додає `__wireless`, `__has_microphone`.
- **`Webcam(Product)`** ([`src/models/webcam.py`](file:///c:/Users/anast/OneDrive/Desktop/oop.store/oop-tech-store/src/models/webcam.py)): додає `__resolution`, `__frame_rate`.

### 4.2. Ієрархія користувачів (`src/models/user.py`)
- **`User(ABC)`** — базовий абстрактний клас:
  - *Приватні поля:* `__user_id`, `__name`, `__email`.
  - *Методи:* `change_email(new_email)`, `get_user_id()`, `get_email_domain()`.
  - *Абстрактний метод:* `@abstractmethod def get_role(self) -> str`.
- **`Customer(User)`**: додає `__orders`, `__wishlist`, `__order_count`, методи `add_order()`, `add_to_wishlist()`, `get_role() -> "Customer"`.
- **`Admin(User)`**: додає `get_role() -> "Admin"`, `can_manage_products() -> True`.

### 4.3. Ієрархія доставки (`src/models/delivery.py`)
- **`Delivery(ABC)`**: поле `__address`, метод `get_address()`, абстрактні методи `@abstractmethod calculate_cost() -> float`, `@abstractmethod estimate_delivery_time() -> str`.
- **`CourierDelivery(Delivery)`**: додає `__distance_km`, розраховує вартість: `80 + distance * 15`.
- **`PickupDelivery(Delivery)`**: вартість `0.0`, готовність «Сьогодні».

### 4.4. Ієрархія оплати (`src/models/payment.py`)
- **`Payment(ABC)`**: поле `__amount`, метод `get_amount()`, абстрактні методи `@abstractmethod process_payment() -> str`, `@abstractmethod refund() -> str`.
- **`CardPayment(Payment)`**: додає `__card_number`, формує чек оплати карткою.
- **`CashPayment(Payment)`**: формує чек оплати готівкою.

### 4.5. Агрегаційні сутності кошика та замовлення
- **`CartItem` & `Cart`** ([`src/models/cart.py`](file:///c:/Users/anast/OneDrive/Desktop/oop.store/oop-tech-store/src/models/cart.py)): містить список `CartItem`, методи `add_product()`, `remove_product()`, `calculate_total()`, `clear()`.
- **`OrderItem` & `Order`** ([`src/models/order.py`](file:///c:/Users/anast/OneDrive/Desktop/oop.store/oop-tech-store/src/models/order.py)): зв'язує `Payment` та `Delivery`, додає товари із зменшенням залишку на складі `product.reduce_stock()`, розраховує повну суму `products_total + delivery_cost`, контролює валідацію статусів («Created», «Paid», «Shipped», «Completed», «Cancelled»).
- **`Repository[T]`** ([`src/services/repository.py`](file:///c:/Users/anast/OneDrive/Desktop/oop.store/oop-tech-store/src/services/repository.py)): шаблон Generic-репозиторію для збереження будь-яких доменних об'єктів у колекції.

---

## 5. Технічні деталі бекенду, фронтенду та бази даних

### 5.1. Бекенд та API
- **Запуск FastAPI сервера:**
  ```powershell
  cd oop-tech-store
  .\.venv\Scripts\uvicorn src.api.main:app --reload --port 8000
  ```
- **Адреса документації Swagger:** `http://127.0.0.1:8000/docs`
- **CORS налаштування:** У [`src/api/main.py`](file:///c:/Users/anast/OneDrive/Desktop/oop.store/oop-tech-store/src/api/main.py#L14-L27) дозволено походження з портів `5500`, `5501`, `3000` (локальний VS Code Live Server та запуск веб-інтерфейсу).

### 5.2. База даних SQLite (`db.sqlite3`)
- Розташування: корінь папки `oop-tech-store/db.sqlite3`.
- Схема таблиці `users`:
  ```sql
  CREATE TABLE IF NOT EXISTS users (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      name TEXT NOT NULL,
      email TEXT NOT NULL UNIQUE,
      password_hash TEXT NOT NULL,
      role TEXT NOT NULL DEFAULT 'Customer'
  );
  ```

### 5.3. Фронтенд
- **Запуск фронтенду:** Відкрити [`src/web/index.html`](file:///c:/Users/anast/OneDrive/Desktop/oop.store/oop-tech-store/src/web/index.html) через VS Code Live Server (за замовчуванням `http://127.0.0.1:5500`) або напряму у браузері.
- Змінна `API_BASE_URL` у [`src/web/app.js`](file:///c:/Users/anast/OneDrive/Desktop/oop.store/oop-tech-store/src/web/app.js#L827) налаштована на `http://127.0.0.1:8000`.

---

## 6. Що вже протестовано і гарантовано працює

### 6.1. Тести Python (Бекенд та моделі)
Команда для запуску:
```powershell
cd oop-tech-store
$env:PYTHONPATH="."
.\.venv\Scripts\python.exe -m unittest discover -s tests
```
- **Результат:** `12/12 тестів пройдено успішно (OK)`:
  - `TestProduct`: перевірка доступності, зменшення залишку, помилки при перевищенні залишку.
  - `TestCart`: додавання товару, розрахунок суми, очищення.
  - `TestOrder`: повна вартість з доставкою, переходи статусів.
  - `TestUserService`: успішна реєстрація, захист від повторних email, вхід за паролем, відмова при невірному паролі.

### 6.2. Тести фронтенду (JavaScript / Браузер)
- Перевірено роботу 78 тестових кейсів:
  1. Фільтрація каталогу за кожною з 4 категорій та відновлення через «Усі категорії».
  2. Фільтрація слайдером ціни від 0 до 10 000 грн з оновленням лейбла.
  3. Фільтрація за виробниками (включаючи множинний вибір декількох брендів одночасно).
  4. Комбінування 3-х фільтрів одночасно (категорія + ціна + виробник).
  5. Додавання товару в кошик та спрацьовування **Toast-сповіщення**:
     - Текст: строго `"Товар додано до кошика"`.
     - Позиція: фіксований правий нижній кут.
     - Час показу: рівно 3 секунди (3000 мс).
     - Дизайн: зелений мінімалістичний стиль Nexora з плавною анімацією (fade-in + slide).
  6. Робота кошика: зміна кількості, видалення позиції, очищення.
  7. Пошук за назвою та брендом, сортування за 3 критеріями, перемикач сітка/список.
  8. Жодних помилок компіляції чи консолі браузера (`0 console errors`).

---

## 7. Відомі недоліки та архітектурні дефекти для усунення

1. **Головний архітектурний розрив (Great Disconnect):**  
   Доменні ООП-класи Python (`Product`, `Cart`, `Order`, `Payment`, `Delivery`) існують автономно. Фронтенд використовує захардкоджені товари в пам'яті JS та зберігає замовлення у `localStorage`.
2. **База даних не зберігає товари та замовлення:**  
   У SQLite створено лише таблицю `users`. Таблиць `products`, `orders`, `order_items` ще немає.
3. **Блокування ролі Admin у бекенді:**  
   У [`src/services/user_service.py`](file:///c:/Users/anast/OneDrive/Desktop/oop.store/oop-tech-store/src/services/user_service.py#L55-L56,L74-L75) жорстко прописано `if role != "Customer": return None`. Через це користувачі з роллю `Admin` не можуть авторизуватися через API.
4. **Порушення інкапсуляції в Cart:**  
   У [`src/models/cart.py:53`](file:///c:/Users/anast/OneDrive/Desktop/oop.store/oop-tech-store/src/models/cart.py#L53) використовується `item._CartItem__product is product`. Необхідно додати `get_product()` у `CartItem`.
5. **Відсутність захисту роутів (Protected Routes):**  
   Функція `verify_access_token` написана у `token_service.py`, але не підключена через FastAPI `Depends()` для захисту ендпоінтів.

---

## 8. Останні прийняті рішення (ВАЖЛИВО: не змінювати без потреби)

1. **Дизайн панелі категорій:**  
   Користувач прямо попросив повернути початковий зовнішній вигляд та поведінку кнопок категорій (`styles.css:538-556`). Початковий дизайн відновлено повністю:
   ```css
   .category-button {
     display: block;
     width: 100%;
     margin: 4px 0;
     padding: 10px 12px;
     text-align: left;
     background: transparent;
     color: var(--text);
     border: 0;
     border-radius: 8px;
   }
   .category-button:hover,
   .category-button.active {
     background: var(--primary-light);
     color: var(--primary-hover);
     transform: none;
   }
   ```
   **Рішення:** Не змінювати ці правила і не нав'язувати інші стилі категорій.

2. **Toast-сповіщення додавання до кошика:**  
   - Має обов'язково бути присутнім у `src/web/app.js` та `src/web/styles.css`.
   - Текст повідомлення: тільки `"Товар додано до кошика"` українською мовою.
   - Тривалість показу: строго 3 секунди (`3000 ms`).
   - Позиція: правий нижній кут (`fixed, right: 24px, bottom: 24px`).
   - Має зелений стиль Nexora та плавний перехід (fade/slide).

3. **Мова інтерфейсу:**  
   Увесь інтерфейс магазину та користувацькі сповіщення строго українською мовою.

4. **Безпека Git:**  
   Нічого не комітити і не пушити на GitHub без прямої вказівки користувача.

---

## 9. Рекомендований наступний план дій для розробника

Якщо ви продовжуєте розробку з іншого акаунту, впроваджуйте функціонал за безпечним 6-етапним маршрутом:

1. **Крок 1 (Інкапсуляція):** Додати в `CartItem` метод `get_product()` та замінити `_CartItem__product` у `Cart.remove_product()`. Додати геттери у `Product`.
2. **Крок 2 (База даних):** Додати у `Database.initialize()` таблицю `products` та наповнити її початковими 8 товарами, якщо вона порожня.
3. **Крок 3 (Каталог через API):** Створити `ProductFactory` (патерн Фабрика для створення `Keyboard`, `Mouse` тощо), `ProductService` та ендпоінти `GET /products`, `GET /products/{id}`. Перевести `app.js` на завантаження товарів через `fetch('/products')`.
4. **Крок 4 (Авторизація та Admin):** Прибрати `if role != "Customer": return None` у `UserService`, додати залежність `require_admin` у FastAPI.
5. **Крок 5 (Замовлення через API):** Створити таблиці `orders` та `order_items`, `OrderService`, підключити класи `Order`, `Payment` (`CardPayment`/`CashPayment`), `Delivery` (`CourierDelivery`/`PickupDelivery`) та ендпоінти `POST /orders`, `GET /orders/my`.
6. **Крок 6 (Фронтенд-інтеграція):** З'єднати форми оформлення замовлення та кабінет адміна з бекендом, зберігши весь існуючий UI та toast-сповіщення.

---

*Цей документ збережено у файлі `NEXORA_HANDOVER.md` у корені проєкту.*
