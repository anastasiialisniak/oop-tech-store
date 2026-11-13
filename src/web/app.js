// =====================================
// API CONFIGURATION & CENTRALIZED HTTP HELPER
// =====================================

const DEFAULT_API_BASE_URL = "http://127.0.0.1:8000";

function resolveApiBaseUrl() {
  const configuredUrl =
    window.NEXORA_API_BASE_URL ||
    document.documentElement?.dataset?.apiBaseUrl ||
    localStorage.getItem("nexora-api-base-url");

  if (typeof configuredUrl === "string" && configuredUrl.trim()) {
    return configuredUrl.trim().replace(/\/+$/, "");
  }

  if (
    window.location.protocol.startsWith("http") &&
    window.location.port === "8000"
  ) {
    return window.location.origin;
  }

  return DEFAULT_API_BASE_URL;
}

const API_BASE_URL = resolveApiBaseUrl();

// Токен та профіль зберігаються в sessionStorage (без паролів)
const TOKEN_STORAGE_KEY = "nexora-access-token";
const USER_STORAGE_KEY = "nexora-current-user";

let products = [];
let isCatalogLoading = false;
let catalogError = null;
let currentUser = null;

function parseJwtPayload(token) {
  if (typeof token !== "string") return null;

  const parts = token.split(".");
  if (parts.length !== 3) return null;

  try {
    const base64Url = parts[1];
    const base64 = base64Url.replace(/-/g, "+").replace(/_/g, "/");
    const padded = base64.padEnd(
      base64.length + ((4 - (base64.length % 4)) % 4),
      "=",
    );
    const binary = window.atob(padded);
    const bytes = Uint8Array.from(binary, (char) => char.charCodeAt(0));
    const jsonString = new TextDecoder("utf-8").decode(bytes);
    const payload = JSON.parse(jsonString);

    return payload && typeof payload === "object" ? payload : null;
  } catch {
    return null;
  }
}

function isTokenExpired(token) {
  const payload = parseJwtPayload(token);
  if (!payload || typeof payload.exp !== "number") {
    return true;
  }

  const nowSeconds = Math.floor(Date.now() / 1000);
  return payload.exp <= nowSeconds;
}

function getAccessToken() {
  const token = sessionStorage.getItem(TOKEN_STORAGE_KEY);
  if (!token) return null;

  if (isTokenExpired(token)) {
    sessionStorage.removeItem(TOKEN_STORAGE_KEY);
    sessionStorage.removeItem(USER_STORAGE_KEY);
    currentUser = null;
    if (typeof navigationButtons !== "undefined" && navigationButtons) {
      navigationButtons.forEach((button) => {
        if (
          button.dataset.page === "admin" ||
          button.dataset.page === "admin-orders"
        ) {
          button.classList.add("hidden");
          button.hidden = true;
          button.classList.remove("active");
        }
      });
    }
    if (typeof adminAccessNotice !== "undefined" && adminAccessNotice && adminContent) {
      adminAccessNotice.classList.remove("hidden");
      adminContent.classList.add("hidden");
    }
    if (
      typeof adminOrdersAccessNotice !== "undefined" &&
      adminOrdersAccessNotice &&
      adminOrdersContent
    ) {
      adminOrdersAccessNotice.classList.remove("hidden");
      adminOrdersContent.classList.add("hidden");
    }
    return null;
  }

  return token;
}

function getAuthHeaders(extraHeaders = {}) {
  const headers = { ...extraHeaders };
  const token = getAccessToken();

  if (token) {
    headers.Authorization = `Bearer ${token}`;
  }

  return headers;
}

function translateApiError(data, statusCode, endpoint = "") {
  const detail = data?.detail;

  if (Array.isArray(detail)) {
    const messages = detail.map((item) => {
      const field = Array.isArray(item?.loc)
        ? String(item.loc[item.loc.length - 1])
        : "";
      if (field === "email") {
        return "Введіть коректну адресу електронної пошти.";
      }
      if (field === "password") {
        return "Пароль повинен містити щонайменше 8 символів.";
      }
      if (field === "name") {
        return "Введіть коректне ім'я.";
      }
      return "Перевірте правильність введених даних.";
    });
    return Array.from(new Set(messages)).join(" ");
  }

  if (typeof detail === "string" && detail.trim()) {
    const normalized = detail.trim();
    const translations = {
      "Invalid email or password": "Невірна електронна пошта або пароль.",
      "A user with this email already exists.":
        "Користувач із цією електронною поштою вже зареєстрований.",
      "User with this email already exists.":
        "Користувач із цією електронною поштою вже зареєстрований.",
      "Name cannot be empty.": "Ім'я не може бути порожнім.",
      "User name cannot be empty.": "Ім'я не може бути порожнім.",
      "Invalid email address.": "Введіть коректну адресу електронної пошти.",
      "Password must contain at least 8 characters.":
        "Пароль повинен містити щонайменше 8 символів.",
      "Password must be at least 8 characters long.":
        "Пароль повинен містити щонайменше 8 символів.",
      "Invalid or expired token":
        "Сесія завершилася або токен недійсний. Будь ласка, увійдіть знову.",
      "Missing or invalid Authorization header":
        "Необхідна авторизація для виконання дії.",
      "Authentication required":
        "Для перегляду замовлень необхідно увійти в акаунт.",
      "Invalid authorization header format":
        "Некоректний заголовок авторизації.",
      "User not found":
        "Користувача не знайдено. Будь ласка, увійдіть у систему знову.",
      "Admin privileges required":
        "Недостатньо прав для виконання цієї дії.",
      "Product not found": "Товар не знайдено.",
      "Not enough items in stock.": "Недостатньо товару на складі.",
      "Quantity must be positive.": "Кількість товару має бути додатною.",
      "Address cannot be empty.": "Адреса доставки не може бути порожньою.",
      "Distance must be positive.":
        "Відстань доставки має бути додатним числом.",
      "Payment amount must be positive.": "Сума оплати має бути додатною.",
      "Invalid card number.": "Некоректний номер картки.",
      "Product name cannot be empty.": "Назва товару не може бути порожньою.",
      "Product brand cannot be empty.": "Виробник товару не може бути порожнім.",
      "Product category cannot be empty.": "Категорія товару не може бути порожньою.",
      "Price must be a valid number.": "Ціна має бути коректним числом.",
      "Price must be a finite number.": "Ціна має бути скінченним числом.",
      "Price cannot be negative.": "Ціна не може бути від'ємною.",
      "Stock quantity must be an integer.": "Кількість на складі має бути цілим числом.",
      "Stock quantity cannot be negative.": "Кількість на складі не може бути від'ємною.",
      "Product image must be a string or None.": "Некоректне посилання на зображення товару.",
      "Product description must be a string or None.": "Некоректний опис товару.",
      "Product attributes must be a dictionary.": "Характеристики товару мають бути словником.",
      "Keyboard attributes must contain 'switch_type' and 'layout'.":
        "Для клавіатури необхідно вказати обидва поля: тип перемикачів та розкладку.",
      "Keyboard 'switch_type' must be a non-empty string.":
        "Тип перемикачів клавіатури не може бути порожнім.",
      "Keyboard 'layout' must be a non-empty string.":
        "Розкладка клавіатури не може бути порожньою.",
      "Mouse attributes must contain 'dpi' and 'connection_type'.":
        "Для мишки необхідно вказати обидва поля: чутливість DPI та тип підключення.",
      "Mouse 'dpi' must be a positive integer.":
        "Чутливість DPI мишки має бути додатним цілим числом.",
      "Mouse 'connection_type' must be a non-empty string.":
        "Тип підключення мишки не може бути порожнім.",
      "Headphones attributes must contain 'wireless' and 'has_microphone'.":
        "Для навушників необхідно вказати обидва поля: тип підключення та наявність мікрофона.",
      "Headphones 'wireless' must be a boolean.":
        "Некоректне значення типу підключення навушників.",
      "Headphones 'has_microphone' must be a boolean.":
        "Некоректне значення наявності мікрофона.",
      "Webcam attributes must contain 'resolution' and 'frame_rate'.":
        "Для вебкамери необхідно вказати обидва поля: роздільну здатність та частоту кадрів (FPS).",
      "Webcam 'resolution' must be a non-empty string.":
        "Роздільна здатність вебкамери не може бути порожньою.",
      "Webcam 'frame_rate' must be a positive integer.":
        "Частота кадрів (FPS) вебкамери має бути додатним цілим числом.",
      "Order cannot be cancelled.":
        "Замовлення у цьому статусі вже не можна скасувати.",
      "Invalid order status.": "Некоректний статус замовлення.",
    };

    if (translations[normalized]) {
      return translations[normalized];
    }

    if (normalized.startsWith("Unsupported product category:")) {
      return "Непідтримувана категорія товару.";
    }

    if (normalized.startsWith("Неможливо змінити статус замовлення у стані")) {
      return "Неможливо змінити статус завершеного або скасованого замовлення.";
    }

    return normalized;
  }

  if (statusCode === 401 && endpoint === "/auth/login") {
    return "Невірна електронна пошта або пароль.";
  }

  if (statusCode === 401) {
    return "Сесія завершилася. Будь ласка, увійдіть у свій акаунт знову.";
  }

  if (statusCode === 403) {
    return "Недостатньо прав для виконання цієї дії.";
  }

  return data?.message || "Не вдалося виконати запит до сервера.";
}

async function apiRequest(endpoint, options = {}) {
  const {
    method = "GET",
    body = undefined,
    headers = {},
    includeAuth = true,
    requiresAuth = false,
  } = options;

  let requestHeaders = { ...headers };

  if (includeAuth || requiresAuth) {
    const token = getAccessToken();
    if (requiresAuth && !token) {
      if (typeof renderAccount === "function") {
        renderAccount();
      }
      throw new Error(
        "Сесія завершилася. Будь ласка, увійдіть у свій акаунт знову.",
      );
    }
    requestHeaders = getAuthHeaders(requestHeaders);
  }

  const fetchOptions = {
    method,
    headers: requestHeaders,
  };

  if (body !== undefined) {
    requestHeaders["Content-Type"] = "application/json";
    fetchOptions.body = JSON.stringify(body);
  }

  let response;
  try {
    response = await fetch(`${API_BASE_URL}${endpoint}`, fetchOptions);
  } catch {
    throw new Error(
      "Не вдалося з'єднатися із сервером. Переконайтеся, що FastAPI запущений.",
    );
  }

  let data = null;
  try {
    data = await response.json();
  } catch {
    throw new Error("Сервер повернув некоректну відповідь.");
  }

  if (!response.ok) {
    if (
      response.status === 401 &&
      endpoint !== "/auth/login" &&
      endpoint !== "/auth/register"
    ) {
      if (typeof clearAuthenticatedUser === "function") {
        clearAuthenticatedUser();
      }
    }
    throw new Error(translateApiError(data, response.status, endpoint));
  }

  return data;
}

const CART_STORAGE_KEY = "nexora-cart";

function loadSavedCart() {
  try {
    const raw = localStorage.getItem(CART_STORAGE_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw);
    if (!Array.isArray(parsed)) return [];

    const merged = new Map();
    parsed.forEach((entry) => {
      const productId = Number(entry?.productId ?? entry?.product_id);
      const quantity = Number(entry?.quantity);
      if (
        Number.isInteger(productId) &&
        productId > 0 &&
        Number.isInteger(quantity) &&
        quantity > 0
      ) {
        merged.set(productId, (merged.get(productId) || 0) + quantity);
      }
    });

    return Array.from(merged.entries()).map(([productId, quantity]) => ({
      productId,
      quantity,
    }));
  } catch {
    localStorage.removeItem(CART_STORAGE_KEY);
    return [];
  }
}

const cart = loadSavedCart();

function saveCart() {
  try {
    localStorage.setItem(CART_STORAGE_KEY, JSON.stringify(cart));
  } catch (error) {
    console.error("Не вдалося зберегти кошик:", error);
  }
}

let customerOrders = [];
let isOrdersLoading = false;
let ordersError = null;
let isSubmittingOrder = false;

let adminOrders = [];
let isAdminOrdersLoading = false;
let adminOrdersError = null;
let editingProductId = null;
let isSubmittingProduct = false;

const ORDER_STATUS_LABELS = {
  Created: "Нове",
  Paid: "Підтверджено",
  Shipped: "Відправлено",
  Completed: "Виконано",
  Cancelled: "Скасовано",
};

const DELIVERY_TYPE_LABELS = {
  pickup: "Самовивіз",
  "nova-poshta": "Нова пошта",
  ukrposhta: "Укрпошта",
  courier: "Кур'єрська доставка",
};

const PAYMENT_TYPE_LABELS = {
  card: "Картка",
  cash: "Готівка",
};

const CATEGORY_LABELS = {
  keyboard: "Клавіатура",
  mouse: "Мишка",
  headphones: "Навушники",
  webcam: "Вебкамера",
};

// Вартість доставки відповідає правилам PaymentDeliveryFactory на бекенді:
// PickupDelivery -> 0 грн; CourierDelivery (5 км за замовчуванням) -> 80 + 5 * 15 = 155 грн
const DEFAULT_DELIVERY_COST = 155;

const savedOrders = localStorage.getItem("nexora-orders");
const orders = savedOrders ? JSON.parse(savedOrders) : [];

function saveOrders() {
  localStorage.setItem("nexora-orders", JSON.stringify(orders));
}

// =====================================
// ELEMENTS
// =====================================

const pages = document.querySelectorAll(".page");
const navigationButtons = document.querySelectorAll(".navigation [data-page]");

const productList = document.querySelector("#product-list");
const searchInput = document.querySelector("#search");
const categoryFilter = document.querySelector("#category-filter");
const sortSelect = document.querySelector("#sort");

const cartItems = document.querySelector("#cart-items");
const cartTotal = document.querySelector("#cart-total");

const checkoutForm = document.querySelector("#checkout-form");
const checkoutMessage = document.querySelector("#checkout-message");
const customerNameInput = document.querySelector("#customer-name");
const customerEmailInput = document.querySelector("#customer-email");
const deliverySelect = document.querySelector("#delivery");
const deliveryAddressGroup = document.querySelector("#delivery-address-group");
const deliveryAddressInput = document.querySelector("#delivery-address");
const paymentSelect = document.querySelector("#payment");
const checkoutItemsTotalEl = document.querySelector("#checkout-items-total");
const checkoutDeliveryCostEl = document.querySelector("#checkout-delivery-cost");
const checkoutTotalAmountEl = document.querySelector("#checkout-total-amount");
const checkoutSubmitButton =
  document.querySelector("#checkout-submit") ||
  document.querySelector('#checkout-form button[type="submit"]');

const ordersTable = document.querySelector("#orders-table");
const adminOrdersTable = document.querySelector("#admin-orders-table");
const productForm = document.querySelector("#product-form");
const adminProductList = document.querySelector("#admin-product-list");
const adminAccessNotice = document.querySelector("#admin-access-notice");
const adminContent = document.querySelector("#admin-content");
const adminOrdersAccessNotice = document.querySelector(
  "#admin-orders-access-notice",
);
const adminOrdersContent = document.querySelector("#admin-orders-content");
const adminProductMessage = document.querySelector("#admin-product-message");
const adminOrdersMessage = document.querySelector("#admin-orders-message");
const adminOrderDetails = document.querySelector("#admin-order-details");

// =====================================
// ROLE & ADMIN ACCESS HELPERS
// =====================================

function isAdminUser() {
  const token = getAccessToken();
  if (!token || !currentUser) {
    return false;
  }
  const payload = parseJwtPayload(token);
  return payload?.role === "Admin" && currentUser.role === "Admin";
}

function renderAdminNoticeBox(container) {
  if (!container) return;
  container.replaceChildren();

  const text = document.createElement("p");
  text.textContent = !getAccessToken()
    ? "Увійдіть через вкладку «Вхід» під службовим обліковим записом адміністратора (Admin), щоб отримати доступ до панелі керування."
    : "Доступ заборонено: ця сторінка доступна лише адміністраторам (Admin). Публічна реєстрація створює лише облікові записи покупців (Customer) — для входу як адміністратор вийдіть із поточного акаунта в Особистому кабінеті та увійдіть через вкладку «Вхід» під службовим акаунтом Admin.";

  const actionButton = document.createElement("button");
  actionButton.type = "button";
  actionButton.textContent = !getAccessToken()
    ? "Увійти в кабінет"
    : "Повернутися до каталогу";
  actionButton.addEventListener("click", () => {
    showPage(!getAccessToken() ? "account" : "catalog");
  });

  container.append(text, actionButton);
}

function updateAdminNavigationVisibility() {
  const isAdmin = isAdminUser();

  navigationButtons.forEach((button) => {
    if (
      button.dataset.page === "admin" ||
      button.dataset.page === "admin-orders"
    ) {
      button.classList.toggle("hidden", !isAdmin);
      button.hidden = !isAdmin;
      if (!isAdmin) {
        button.classList.remove("active");
      }
    }
  });

  if (adminAccessNotice && adminContent) {
    adminAccessNotice.classList.toggle("hidden", isAdmin);
    adminContent.classList.toggle("hidden", !isAdmin);
    if (!isAdmin) {
      renderAdminNoticeBox(adminAccessNotice);
    }
  }

  if (adminOrdersAccessNotice && adminOrdersContent) {
    adminOrdersAccessNotice.classList.toggle("hidden", isAdmin);
    adminOrdersContent.classList.toggle("hidden", !isAdmin);
    if (!isAdmin) {
      renderAdminNoticeBox(adminOrdersAccessNotice);
    }
  }
}

// =====================================
// PAGE NAVIGATION
// =====================================

function showPage(pageId) {
  updateAdminNavigationVisibility();

  pages.forEach((page) => {
    page.classList.toggle("hidden", page.id !== pageId);
  });

  navigationButtons.forEach((button) => {
    const isTarget = button.dataset.page === pageId;
    const isAdminTab =
      button.dataset.page === "admin" || button.dataset.page === "admin-orders";
    button.classList.toggle("active", isTarget && (!isAdminTab || isAdminUser()));
  });

  if (pageId === "checkout") {
    prefillCheckoutCustomerData();
    updateDeliveryFields();
    updateCheckoutSummary();
  } else if (pageId === "orders") {
    if (getAccessToken()) {
      loadCustomerOrders();
    } else {
      renderOrders();
    }
  } else if (pageId === "admin") {
    if (isAdminUser()) {
      renderAdminProducts();
    }
  } else if (pageId === "admin-orders") {
    if (isAdminUser()) {
      loadAdminOrders();
    } else {
      adminOrders = [];
      renderAdminOrders();
    }
  }
}

navigationButtons.forEach((button) => {
  button.addEventListener("click", () => {
    const pageId = button.dataset.page;

    if (pageId === "checkout") {
      showCheckoutMessage("");
    }

    showPage(pageId);
  });
});

// Кнопки переходу між сторінками всередині сторінок
document.querySelectorAll(".page [data-page]").forEach((button) => {
  button.addEventListener("click", () => {
    const pageId = button.dataset.page;

    if (pageId === "checkout") {
      showCheckoutMessage("");
    }

    showPage(pageId);
  });
});

// =====================================
// PRICE FORMAT
// =====================================

function formatPrice(price) {
  return `${price.toLocaleString("uk-UA")} грн`;
}

// =====================================
// PRODUCT CATALOG
// =====================================

function normalizeProduct(rawProduct) {
  const stockQuantity = Number.isInteger(rawProduct?.stock_quantity)
    ? rawProduct.stock_quantity
    : Number(rawProduct?.stock ?? 0);

  return {
    id: Number(rawProduct.id),
    name: String(rawProduct.name || ""),
    brand: String(rawProduct.brand || ""),
    category: String(rawProduct.category || ""),
    price: Number(rawProduct.price || 0),
    stock: stockQuantity,
    stock_quantity: stockQuantity,
    available:
      typeof rawProduct.available === "boolean"
        ? rawProduct.available
        : stockQuantity > 0,
    image: rawProduct.image || "",
    attributes:
      rawProduct.attributes && typeof rawProduct.attributes === "object"
        ? rawProduct.attributes
        : {},
    description: String(rawProduct.description || ""),
  };
}

async function fetchProductById(productId) {
  const data = await apiRequest(
    `/products/${encodeURIComponent(productId)}`,
    { includeAuth: false },
  );
  return normalizeProduct(data);
}

async function loadProducts() {
  isCatalogLoading = true;
  catalogError = null;
  renderProducts();

  try {
    const data = await apiRequest("/products", { includeAuth: false });
    if (!Array.isArray(data)) {
      throw new Error("Сервер повернув некоректний формат каталогу товарів.");
    }

    products = data.map(normalizeProduct);
    catalogError = null;
  } catch (error) {
    console.error("Помилка завантаження каталогу:", error);
    products = [];
    catalogError =
      error.message ||
      "Не вдалося завантажити товари із сервера. Переконайтеся, що FastAPI запущений.";
  } finally {
    isCatalogLoading = false;
    renderProducts();
    renderCart();
    renderAdminProducts();
  }
}

function renderProducts() {
  productList.replaceChildren();

  if (isCatalogLoading) {
    const loadingState = document.createElement("p");
    loadingState.className = "catalog-status";
    loadingState.textContent = "Завантаження товарів...";
    productList.append(loadingState);
    return;
  }

  if (catalogError) {
    const errorBox = document.createElement("div");
    errorBox.className = "catalog-status catalog-error";

    const errorText = document.createElement("p");
    errorText.textContent = catalogError;

    const retryButton = document.createElement("button");
    retryButton.type = "button";
    retryButton.textContent = "Спробувати знову";
    retryButton.addEventListener("click", () => {
      loadProducts();
    });

    errorBox.append(errorText, retryButton);
    productList.append(errorBox);
    return;
  }

  const search = searchInput.value.trim().toLowerCase();
  const category = categoryFilter.value;
  const sort = sortSelect.value;

  const priceInput = document.querySelector("#price-filter");
  const maxPrice = priceInput ? Number(priceInput.value) : 10000;

  const selectedBrands = Array.from(
    document.querySelectorAll('input[name="brand-filter"]:checked'),
  ).map((checkbox) => checkbox.value);

  let filteredProducts = products.filter((product) => {
    const matchesSearch =
      product.name.toLowerCase().includes(search) ||
      product.brand.toLowerCase().includes(search);

    const matchesCategory = category === "all" || product.category === category;

    const matchesPrice = product.price <= maxPrice;

    const matchesBrand =
      selectedBrands.length === 0 || selectedBrands.includes(product.brand);

    return matchesSearch && matchesCategory && matchesPrice && matchesBrand;
  });

  if (sort === "price-asc") {
    filteredProducts.sort((a, b) => a.price - b.price);
  } else if (sort === "price-desc") {
    filteredProducts.sort((a, b) => b.price - a.price);
  } else {
    filteredProducts.sort((a, b) => a.name.localeCompare(b.name));
  }

  if (filteredProducts.length === 0) {
    productList.textContent = "Товарів не знайдено.";
    return;
  }

  filteredProducts.forEach((product) => {
    const card = document.createElement("article");
    card.className = "product-card";
    card.dataset.productId = String(product.id);
    if (product.description) {
      card.title = product.description;
    }

    const image = document.createElement("img");
    image.className = "product-image";
    image.src = product.image;
    image.alt = product.name;
    image.loading = "lazy";

    image.addEventListener("error", () => {
      image.style.display = "none";
    });

    const title = document.createElement("h3");
    title.textContent = product.name;

    const brand = document.createElement("p");
    brand.textContent = `Виробник: ${product.brand}`;

    const price = document.createElement("p");
    price.textContent = formatPrice(product.price);

    const stock = document.createElement("p");
    stock.textContent =
      product.stock > 0 ? `У наявності: ${product.stock}` : "Немає в наявності";

    const addButton = document.createElement("button");
    addButton.textContent = "Додати в кошик";
    addButton.disabled = product.stock === 0;

    addButton.addEventListener("click", () => {
      addToCart(product.id);
    });

    card.append(image, title, brand, price, stock, addButton);
    productList.append(card);
  });
}

// =====================================
// SHOPPING CART
// =====================================

// Зелене сповіщення
function showToast(message = "Товар додано до кошика") {
  let toast = document.querySelector("#nexora-toast");

  if (!toast) {
    toast = document.createElement("div");
    toast.id = "nexora-toast";
    toast.className = "toast";
    toast.setAttribute("role", "status");
    toast.setAttribute("aria-live", "polite");
    document.body.append(toast);
  }

  toast.textContent = message;

  // Перезапускаємо анімацію та таймер сповіщення
  window.clearTimeout(showToast.timeoutId);
  toast.classList.remove("show");
  void toast.offsetWidth; // Примусовий reflow для повторної анімації
  toast.classList.add("show");

  showToast.timeoutId = window.setTimeout(() => {
    toast.classList.remove("show");
  }, 3000);
}

// Додавання товару в кошик
function addToCart(productId) {
  const numericId = Number(productId);
  if (!Number.isInteger(numericId) || numericId <= 0) {
    alert("Некоректний ідентифікатор товару.");
    return;
  }

  const product = products.find((item) => item.id === numericId);

  if (!product || product.stock <= 0) {
    alert("Цей товар зараз недоступний.");
    return;
  }

  const cartItem = cart.find((item) => item.productId === numericId);

  if (cartItem) {
    if (cartItem.quantity >= product.stock) {
      alert("Недостатньо товару на складі.");
      return;
    }

    cartItem.quantity += 1;
  } else {
    cart.push({
      productId: numericId,
      quantity: 1,
    });
  }

  saveCart();
  renderCart();
  renderProducts();

  showToast("Товар додано до кошика");
}

function calculateCartSubtotal() {
  return cart.reduce((sum, item) => {
    const product = products.find(
      (candidate) => candidate.id === item.productId,
    );
    if (!product) return sum;
    return sum + product.price * item.quantity;
  }, 0);
}

// Відображення кошика
function renderCart() {
  cartItems.replaceChildren();

  let total = 0;

  if (cart.length === 0) {
    const emptyMessage = document.createElement("div");
    emptyMessage.className = "empty-cart";

    const message = document.createElement("p");
    message.textContent = "Ваш кошик поки порожній";

    const catalogButton = document.createElement("button");
    catalogButton.textContent = "Перейти до каталогу";

    catalogButton.addEventListener("click", () => {
      showPage("catalog");
    });

    emptyMessage.append(message, catalogButton);
    cartItems.append(emptyMessage);

    cartTotal.textContent = "0";
    if (typeof updateCheckoutSummary === "function") {
      updateCheckoutSummary();
    }
    return;
  }

  cart.forEach((item) => {
    const product = products.find(
      (candidate) => candidate.id === item.productId,
    );

    if (!product) {
      if (!isCatalogLoading && !catalogError) {
        const unavailableRow = document.createElement("div");
        unavailableRow.className = "product-card cart-product-card";

        const placeholder = document.createElement("div");
        placeholder.className = "cart-product-image";

        const description = document.createElement("p");
        description.textContent = `Товар (ID #${item.productId}) більше недоступний у каталозі`;

        const spacer1 = document.createElement("span");
        const spacer2 = document.createElement("span");

        const removeButton = document.createElement("button");
        removeButton.type = "button";
        removeButton.textContent = "Видалити";
        removeButton.addEventListener("click", () => {
          cart.splice(cart.indexOf(item), 1);
          saveCart();
          renderCart();
          renderProducts();
        });

        unavailableRow.append(
          placeholder,
          description,
          spacer1,
          spacer2,
          removeButton,
        );
        cartItems.append(unavailableRow);
      }
      return;
    }

    total += product.price * item.quantity;

    const row = document.createElement("div");
    row.className = "product-card cart-product-card";

    const image = document.createElement("img");
    image.className = "cart-product-image";
    image.src = product.image;
    image.alt = product.name;

    image.addEventListener("error", () => {
      image.style.display = "none";
    });

    const description = document.createElement("p");
    let stockWarning = "";
    if (product.stock <= 0) {
      stockWarning = " (Немає в наявності)";
    } else if (item.quantity > product.stock) {
      stockWarning = ` (Доступно лише ${product.stock} шт.)`;
    }
    description.textContent =
      `${product.name} × ${item.quantity} — ` +
      formatPrice(product.price * item.quantity) +
      stockWarning;

    const decreaseButton = document.createElement("button");
    decreaseButton.type = "button";
    decreaseButton.textContent = "−";
    decreaseButton.setAttribute("aria-label", "Зменшити кількість");

    decreaseButton.addEventListener("click", () => {
      item.quantity -= 1;

      if (item.quantity <= 0) {
        cart.splice(cart.indexOf(item), 1);
      }

      saveCart();
      renderCart();
      renderProducts();
    });

    const increaseButton = document.createElement("button");
    increaseButton.type = "button";
    increaseButton.textContent = "+";
    increaseButton.setAttribute("aria-label", "Збільшити кількість");
    increaseButton.disabled = item.quantity >= product.stock;

    increaseButton.addEventListener("click", () => {
      if (item.quantity >= product.stock) {
        alert("Недостатньо товару на складі.");
        return;
      }

      item.quantity += 1;
      saveCart();
      renderCart();
    });

    const removeButton = document.createElement("button");
    removeButton.type = "button";
    removeButton.textContent = "Видалити";

    removeButton.addEventListener("click", () => {
      cart.splice(cart.indexOf(item), 1);
      saveCart();
      renderCart();
      renderProducts();
    });

    row.append(
      image,
      description,
      decreaseButton,
      increaseButton,
      removeButton,
    );

    cartItems.append(row);
  });

  cartTotal.textContent = total.toLocaleString("uk-UA");
  if (typeof updateCheckoutSummary === "function") {
    updateCheckoutSummary();
  }
}

// =====================================
// CUSTOMER ORDERS (GET /orders/my)
// =====================================

function formatOrderStatus(status) {
  return ORDER_STATUS_LABELS[status] || status || "Нове";
}

function formatOrderItems(items) {
  if (!Array.isArray(items) || items.length === 0) {
    return "—";
  }

  return items
    .map((item) => {
      const name = item.product_name || `Товар #${item.product_id}`;
      const qty = Number(item.quantity || 1);
      return `${name} × ${qty}`;
    })
    .join(", ");
}

function formatOrderTotal(order) {
  const totalAmount = Number(order.total_amount ?? order.total ?? 0);
  const deliveryCost = Number(order.delivery_cost ?? 0);

  if (deliveryCost > 0) {
    return `${formatPrice(totalAmount)} (доставка: ${formatPrice(deliveryCost)})`;
  }

  return formatPrice(totalAmount);
}

function formatOrderDelivery(order) {
  const deliveryType = order.delivery_type || order.delivery || "";
  const label = DELIVERY_TYPE_LABELS[deliveryType] || deliveryType || "—";
  const address =
    typeof order.delivery_address === "string"
      ? order.delivery_address.trim()
      : "";

  if (address && deliveryType !== "pickup") {
    return `${label} (${address})`;
  }

  return label;
}

function renderOrdersTableNotice(
  message,
  isError = false,
  actionLabel = null,
  onAction = null,
) {
  ordersTable.replaceChildren();

  const row = document.createElement("tr");
  const cell = document.createElement("td");
  cell.colSpan = 7;
  cell.className = isError
    ? "orders-table-status error"
    : "orders-table-status";

  const text = document.createElement("p");
  text.textContent = message;
  cell.append(text);

  if (actionLabel && typeof onAction === "function") {
    const button = document.createElement("button");
    button.type = "button";
    button.textContent = actionLabel;
    button.addEventListener("click", onAction);
    cell.append(button);
  }

  row.append(cell);
  ordersTable.append(row);
}

async function loadCustomerOrders() {
  const token = getAccessToken();
  if (!token) {
    customerOrders = [];
    ordersError = null;
    isOrdersLoading = false;
    renderOrders();
    return [];
  }

  isOrdersLoading = true;
  ordersError = null;
  renderOrders();

  try {
    const data = await apiRequest("/orders/my", { requiresAuth: true });
    if (!Array.isArray(data)) {
      throw new Error("Сервер повернув некоректний формат списку замовлень.");
    }

    customerOrders = data;
    ordersError = null;
    return customerOrders;
  } catch (error) {
    console.error("Помилка завантаження замовлень:", error);
    customerOrders = [];
    ordersError =
      error.message || "Не вдалося завантажити історію замовлень.";
    return [];
  } finally {
    isOrdersLoading = false;
    renderOrders();
  }
}

function renderOrders() {
  if (!ordersTable) return;

  ordersTable.replaceChildren();

  if (!getAccessToken()) {
    renderOrdersTableNotice(
      "Увійдіть у свій обліковий запис, щоб переглянути історію замовлень.",
      false,
      "Увійти в кабінет",
      () => showPage("account"),
    );
    return;
  }

  if (isOrdersLoading) {
    renderOrdersTableNotice("Завантаження замовлень...");
    return;
  }

  if (ordersError) {
    renderOrdersTableNotice(
      ordersError,
      true,
      "Спробувати знову",
      () => loadCustomerOrders(),
    );
    return;
  }

  if (customerOrders.length === 0) {
    renderOrdersTableNotice("У вас ще немає оформлених замовлень.");
    return;
  }

  customerOrders.forEach((order) => {
    const row = document.createElement("tr");

    const values = [
      order.id,
      order.customer_name || order.customer || "—",
      formatOrderItems(order.items),
      formatOrderTotal(order),
      order.date || "—",
      formatOrderDelivery(order),
      formatOrderStatus(order.status),
    ];

    values.forEach((value, index) => {
      const cell = document.createElement("td");
      cell.textContent = value;
      if (index === 6 && order.status) {
        cell.dataset.status = String(order.status);
      }
      row.append(cell);
    });

    ordersTable.append(row);
  });
}

// =====================================
// ADMIN ORDER MANAGEMENT (GET /orders, PATCH /orders/{id}/status)
// =====================================

function showAdminOrdersMessage(message, isError = false) {
  if (!adminOrdersMessage) return;
  adminOrdersMessage.textContent = message;
  adminOrdersMessage.classList.toggle("error", isError);
  adminOrdersMessage.classList.toggle(
    "success",
    !isError && Boolean(message),
  );
}

function renderAdminOrdersTableNotice(
  message,
  isError = false,
  actionLabel = null,
  onAction = null,
) {
  if (!adminOrdersTable) return;
  adminOrdersTable.replaceChildren();

  const row = document.createElement("tr");
  const cell = document.createElement("td");
  cell.colSpan = 8;
  cell.className = isError
    ? "orders-table-status error"
    : "orders-table-status";

  const text = document.createElement("p");
  text.textContent = message;
  cell.append(text);

  if (actionLabel && typeof onAction === "function") {
    const button = document.createElement("button");
    button.type = "button";
    button.textContent = actionLabel;
    button.addEventListener("click", onAction);
    cell.append(button);
  }

  row.append(cell);
  adminOrdersTable.append(row);
}

function renderAdminOrderDetailsPanel(order) {
  if (!adminOrderDetails) return;
  if (!order) {
    adminOrderDetails.classList.add("hidden");
    adminOrderDetails.replaceChildren();
    return;
  }

  adminOrderDetails.replaceChildren();
  adminOrderDetails.classList.remove("hidden");

  const header = document.createElement("div");
  header.className = "admin-order-details-header";

  const title = document.createElement("h3");
  title.textContent = `Деталі замовлення №${order.id}`;

  const closeButton = document.createElement("button");
  closeButton.type = "button";
  closeButton.className = "secondary-button";
  closeButton.textContent = "Закрити";
  closeButton.addEventListener("click", () => {
    renderAdminOrderDetailsPanel(null);
  });

  header.append(title, closeButton);

  const meta = document.createElement("div");
  meta.className = "admin-order-details-meta";

  const customerType =
    order.user_id == null ? "Гість" : `Користувач #${order.user_id}`;
  const paymentLabel =
    PAYMENT_TYPE_LABELS[order.payment_type] || order.payment_type || "—";

  const metaLines = [
    `Покупець: ${order.customer_name || "—"} (${customerType})`,
    `Електронна пошта: ${order.customer_email || "—"}`,
    `Дата оформлення: ${order.date || "—"}`,
    `Спосіб доставки: ${formatOrderDelivery(order)}`,
    `Спосіб оплати: ${paymentLabel}`,
    `Статус: ${formatOrderStatus(order.status)} (${order.status || "Created"})`,
    `Сума товарів: ${formatPrice(Number(order.items_total ?? 0))}`,
    `Вартість доставки: ${formatPrice(Number(order.delivery_cost ?? 0))}`,
    `Загальна сума: ${formatPrice(Number(order.total_amount ?? 0))}`,
  ];

  metaLines.forEach((lineText) => {
    const p = document.createElement("p");
    p.textContent = lineText;
    meta.append(p);
  });

  const itemsTitle = document.createElement("h4");
  itemsTitle.textContent = "Замовлені товари:";

  const itemsList = document.createElement("ul");
  itemsList.className = "admin-order-details-items";

  const items = Array.isArray(order.items) ? order.items : [];
  items.forEach((item) => {
    const li = document.createElement("li");
    const unitPrice = Number(item.price || 0);
    const qty = Number(item.quantity || 1);
    const lineTotal = unitPrice * qty;
    li.textContent = `${item.product_name || `Товар #${item.product_id}`} — ${qty} шт. × ${formatPrice(unitPrice)} = ${formatPrice(lineTotal)}`;
    itemsList.append(li);
  });

  adminOrderDetails.append(header, meta, itemsTitle, itemsList);
}

async function loadAdminOrders() {
  if (!isAdminUser()) {
    adminOrders = [];
    adminOrdersError = null;
    isAdminOrdersLoading = false;
    renderAdminOrders();
    return [];
  }

  isAdminOrdersLoading = true;
  adminOrdersError = null;
  renderAdminOrders();

  try {
    const data = await apiRequest("/orders", { requiresAuth: true });
    if (!Array.isArray(data)) {
      throw new Error("Сервер повернув некоректний формат списку замовлень.");
    }
    adminOrders = data;
    adminOrdersError = null;
    return adminOrders;
  } catch (error) {
    console.error("Помилка завантаження замовлень адміністратора:", error);
    adminOrders = [];
    adminOrdersError =
      error.message || "Не вдалося завантажити список усіх замовлень.";
    return [];
  } finally {
    isAdminOrdersLoading = false;
    renderAdminOrders();
  }
}

async function updateAdminOrderStatus(orderId, newStatus, buttonEl = null) {
  if (!isAdminUser()) {
    showAdminOrdersMessage("Доступ дозволено лише адміністраторам.", true);
    return;
  }

  if (buttonEl) {
    buttonEl.disabled = true;
  }
  showAdminOrdersMessage(`Оновлюємо статус замовлення №${orderId}...`);

  try {
    const updatedOrder = await apiRequest(
      `/orders/${encodeURIComponent(orderId)}/status`,
      {
        method: "PATCH",
        body: { status: newStatus },
        requiresAuth: true,
      },
    );

    const statusLabel = formatOrderStatus(updatedOrder.status);
    showAdminOrdersMessage(
      `Статус замовлення №${updatedOrder.id} змінено на «${statusLabel}».`,
      false,
    );
    showToast(`Статус замовлення №${updatedOrder.id}: ${statusLabel}`);

    await loadAdminOrders();
    await loadProducts();
    if (getAccessToken()) {
      await loadCustomerOrders();
    }
  } catch (error) {
    console.error("Помилка оновлення статусу замовлення:", error);
    showAdminOrdersMessage(
      error.message || "Не вдалося оновити статус замовлення.",
      true,
    );
    await loadAdminOrders();
  } finally {
    if (buttonEl) {
      buttonEl.disabled = false;
    }
  }
}

function renderAdminOrders() {
  if (!adminOrdersTable) return;
  adminOrdersTable.replaceChildren();

  if (!isAdminUser()) {
    renderAdminOrdersTableNotice(
      "Доступ до керування замовленнями дозволено лише адміністраторам.",
      false,
      !getAccessToken() ? "Увійти в кабінет" : "До каталогу",
      () => showPage(!getAccessToken() ? "account" : "catalog"),
    );
    return;
  }

  if (isAdminOrdersLoading) {
    renderAdminOrdersTableNotice("Завантаження всіх замовлень...");
    return;
  }

  if (adminOrdersError) {
    renderAdminOrdersTableNotice(
      adminOrdersError,
      true,
      "Спробувати знову",
      () => loadAdminOrders(),
    );
    return;
  }

  if (adminOrders.length === 0) {
    renderAdminOrdersTableNotice("У магазині поки немає оформлених замовлень.");
    return;
  }

  const statusOptions = [
    { value: "Created", label: "Нове" },
    { value: "Paid", label: "Підтверджено" },
    { value: "Shipped", label: "Відправлено" },
    { value: "Completed", label: "Виконано" },
    { value: "Cancelled", label: "Скасовано" },
  ];

  adminOrders.forEach((order) => {
    const row = document.createElement("tr");
    row.dataset.orderId = String(order.id);

    // 1. № замовлення
    const idCell = document.createElement("td");
    idCell.textContent = String(order.id);

    // 2. Покупець (ім'я, email, тип: гість чи зареєстрований)
    const customerCell = document.createElement("td");
    const customerNameEl = document.createElement("strong");
    customerNameEl.textContent =
      order.customer_name || order.customer || "—";

    const customerEmailEl = document.createElement("div");
    customerEmailEl.className = "admin-order-subtext";
    customerEmailEl.textContent = order.customer_email || "";

    const customerTypeEl = document.createElement("span");
    customerTypeEl.className = "admin-order-badge";
    customerTypeEl.textContent =
      order.user_id == null ? "Гість" : `Користувач #${order.user_id}`;

    customerCell.append(customerNameEl, customerEmailEl, customerTypeEl);

    // 3. Замовлені товари (назва, кількість, ціна за одиницю)
    const itemsCell = document.createElement("td");
    const items = Array.isArray(order.items) ? order.items : [];
    if (items.length === 0) {
      itemsCell.textContent = "—";
    } else {
      items.forEach((item) => {
        const line = document.createElement("div");
        line.className = "admin-order-item-line";
        const unitPrice = Number(item.price || 0);
        const qty = Number(item.quantity || 1);
        line.textContent = `${item.product_name || `Товар #${item.product_id}`} × ${qty} (${formatPrice(unitPrice)})`;
        itemsCell.append(line);
      });
    }

    // 4. Загальна сума
    const totalCell = document.createElement("td");
    totalCell.textContent = formatOrderTotal(order);

    // 5. Дата
    const dateCell = document.createElement("td");
    dateCell.textContent = order.date || "—";

    // 6. Доставка та оплата
    const deliveryPaymentCell = document.createElement("td");
    const deliveryLine = document.createElement("div");
    deliveryLine.textContent = formatOrderDelivery(order);

    const paymentLine = document.createElement("div");
    paymentLine.className = "admin-order-subtext";
    const paymentLabel =
      PAYMENT_TYPE_LABELS[order.payment_type] || order.payment_type || "—";
    paymentLine.textContent = `Оплата: ${paymentLabel}`;

    deliveryPaymentCell.append(deliveryLine, paymentLine);

    // 7. Статус (випадаючий список з українськими назвами)
    const statusCell = document.createElement("td");
    const statusSelect = document.createElement("select");
    statusSelect.className = "admin-order-status-select";
    statusSelect.setAttribute(
      "aria-label",
      `Статус замовлення №${order.id}`,
    );

    const currentStatus = order.status || "Created";
    const isFinalStatus =
      currentStatus === "Completed" || currentStatus === "Cancelled";

    statusOptions.forEach((option) => {
      const element = document.createElement("option");
      element.value = option.value;
      element.textContent = option.label;
      if (
        option.value === "Cancelled" &&
        currentStatus === "Shipped"
      ) {
        element.disabled = true;
      }
      statusSelect.append(element);
    });

    statusSelect.value = currentStatus;
    statusSelect.disabled = isFinalStatus;
    statusCell.append(statusSelect);

    // 8. Дія (Зберегти статус + Деталі)
    const actionCell = document.createElement("td");
    actionCell.className = "admin-order-actions";

    const saveButton = document.createElement("button");
    saveButton.type = "button";
    saveButton.textContent = "Зберегти статус";
    saveButton.disabled = isFinalStatus;

    saveButton.addEventListener("click", () =>
      updateAdminOrderStatus(order.id, statusSelect.value, saveButton),
    );

    const detailsButton = document.createElement("button");
    detailsButton.type = "button";
    detailsButton.className = "secondary-button";
    detailsButton.textContent = "Деталі";
    detailsButton.addEventListener("click", async () => {
      try {
        const fullOrder = await apiRequest(
          `/orders/${encodeURIComponent(order.id)}`,
          { requiresAuth: true },
        );
        renderAdminOrderDetailsPanel(fullOrder);
      } catch {
        renderAdminOrderDetailsPanel(order);
      }
    });

    actionCell.append(saveButton, detailsButton);

    row.append(
      idCell,
      customerCell,
      itemsCell,
      totalCell,
      dateCell,
      deliveryPaymentCell,
      statusCell,
      actionCell,
    );
    adminOrdersTable.append(row);
  });
}

// =====================================
// ADMIN PRODUCT MANAGEMENT (POST / PUT / DELETE /products)
// =====================================

function showAdminProductMessage(message, isError = false) {
  if (!adminProductMessage) return;
  adminProductMessage.textContent = message;
  adminProductMessage.classList.toggle("error", isError);
  adminProductMessage.classList.toggle(
    "success",
    !isError && Boolean(message),
  );
}

function updateProductCategoryAttributesFields() {
  const categorySelect = document.querySelector("#product-category");
  const selectedCategory = categorySelect ? categorySelect.value : "keyboard";
  const groups = document.querySelectorAll("[data-category-attrs]");

  groups.forEach((group) => {
    group.classList.toggle(
      "hidden",
      group.dataset.categoryAttrs !== selectedCategory,
    );
  });
}

function clearProductCategoryAttributeInputs() {
  const switchTypeInput = document.querySelector("#attr-switch-type");
  const layoutInput = document.querySelector("#attr-layout");
  const dpiInput = document.querySelector("#attr-dpi");
  const connectionTypeInput = document.querySelector("#attr-connection-type");
  const wirelessSelect = document.querySelector("#attr-wireless");
  const hasMicSelect = document.querySelector("#attr-has-microphone");
  const resolutionInput = document.querySelector("#attr-resolution");
  const frameRateInput = document.querySelector("#attr-frame-rate");

  if (switchTypeInput) switchTypeInput.value = "";
  if (layoutInput) layoutInput.value = "";
  if (dpiInput) dpiInput.value = "";
  if (connectionTypeInput) connectionTypeInput.value = "";
  if (wirelessSelect) wirelessSelect.value = "";
  if (hasMicSelect) hasMicSelect.value = "";
  if (resolutionInput) resolutionInput.value = "";
  if (frameRateInput) frameRateInput.value = "";
}

function populateProductCategoryAttributeInputs(category, attributes = {}) {
  clearProductCategoryAttributeInputs();
  if (!attributes || typeof attributes !== "object") return;

  if (category === "keyboard") {
    const switchTypeInput = document.querySelector("#attr-switch-type");
    const layoutInput = document.querySelector("#attr-layout");
    if (switchTypeInput && attributes.switch_type) {
      switchTypeInput.value = String(attributes.switch_type);
    }
    if (layoutInput && attributes.layout) {
      layoutInput.value = String(attributes.layout);
    }
  } else if (category === "mouse") {
    const dpiInput = document.querySelector("#attr-dpi");
    const connectionTypeInput = document.querySelector("#attr-connection-type");
    if (dpiInput && attributes.dpi !== undefined) {
      dpiInput.value = String(attributes.dpi);
    }
    if (connectionTypeInput && attributes.connection_type) {
      connectionTypeInput.value = String(attributes.connection_type);
    }
  } else if (category === "headphones") {
    const wirelessSelect = document.querySelector("#attr-wireless");
    const hasMicSelect = document.querySelector("#attr-has-microphone");
    if (wirelessSelect && typeof attributes.wireless === "boolean") {
      wirelessSelect.value = String(attributes.wireless);
    }
    if (hasMicSelect && typeof attributes.has_microphone === "boolean") {
      hasMicSelect.value = String(attributes.has_microphone);
    }
  } else if (category === "webcam") {
    const resolutionInput = document.querySelector("#attr-resolution");
    const frameRateInput = document.querySelector("#attr-frame-rate");
    if (resolutionInput && attributes.resolution) {
      resolutionInput.value = String(attributes.resolution);
    }
    if (frameRateInput && attributes.frame_rate !== undefined) {
      frameRateInput.value = String(attributes.frame_rate);
    }
  }
}

function collectAndValidateProductAttributes(category) {
  if (category === "keyboard") {
    const switchType = (
      document.querySelector("#attr-switch-type")?.value || ""
    ).trim();
    const layout = (document.querySelector("#attr-layout")?.value || "").trim();

    if (!switchType && !layout) {
      return {};
    }
    if (!switchType || !layout) {
      throw new Error(
        "Для клавіатури заповніть обидва поля характеристик (тип перемикачів та розкладку) або залиште обидва порожніми.",
      );
    }
    return { switch_type: switchType, layout };
  }

  if (category === "mouse") {
    const dpiRaw = (document.querySelector("#attr-dpi")?.value || "").trim();
    const connectionType = (
      document.querySelector("#attr-connection-type")?.value || ""
    ).trim();

    if (!dpiRaw && !connectionType) {
      return {};
    }
    if (!dpiRaw || !connectionType) {
      throw new Error(
        "Для мишки заповніть обидва поля характеристик (DPI та тип підключення) або залиште обидва порожніми.",
      );
    }
    const dpi = Number(dpiRaw);
    if (!Number.isInteger(dpi) || dpi <= 0) {
      throw new Error("Чутливість DPI мишки має бути додатним цілим числом.");
    }
    return { dpi, connection_type: connectionType };
  }

  if (category === "headphones") {
    const wirelessRaw = document.querySelector("#attr-wireless")?.value || "";
    const hasMicRaw =
      document.querySelector("#attr-has-microphone")?.value || "";

    if (!wirelessRaw && !hasMicRaw) {
      return {};
    }
    if (!wirelessRaw || !hasMicRaw) {
      throw new Error(
        "Для навушників оберіть обидва параметри характеристик (підключення та мікрофон) або залиште обидва як «Не вказано».",
      );
    }
    return {
      wireless: wirelessRaw === "true",
      has_microphone: hasMicRaw === "true",
    };
  }

  if (category === "webcam") {
    const resolution = (
      document.querySelector("#attr-resolution")?.value || ""
    ).trim();
    const frameRateRaw = (
      document.querySelector("#attr-frame-rate")?.value || ""
    ).trim();

    if (!resolution && !frameRateRaw) {
      return {};
    }
    if (!resolution || !frameRateRaw) {
      throw new Error(
        "Для вебкамери заповніть обидва поля характеристик (роздільну здатність та FPS) або залиште обидва порожніми.",
      );
    }
    const frameRate = Number(frameRateRaw);
    if (!Number.isInteger(frameRate) || frameRate <= 0) {
      throw new Error(
        "Частота кадрів (FPS) вебкамери має бути додатним цілим числом.",
      );
    }
    return { resolution, frame_rate: frameRate };
  }

  return {};
}

function ensureBrandOptionExists(brandValue) {
  const brandSelect = document.querySelector("#product-brand");
  if (!brandSelect || !brandValue) return;

  const options = Array.from(brandSelect.options || []);
  const exists = options.some((opt) => opt.value === brandValue);
  if (!exists) {
    const newOpt = document.createElement("option");
    newOpt.value = brandValue;
    newOpt.textContent = brandValue;
    brandSelect.append(newOpt);
  }
}

function resetProductFormMode() {
  editingProductId = null;
  productForm?.reset();
  clearProductCategoryAttributeInputs();
  updateProductCategoryAttributesFields();

  const formTitle = document.querySelector("#product-form-title");
  if (formTitle) {
    formTitle.textContent = "Додати новий товар";
  }

  const submitButton =
    document.querySelector("#product-submit") ||
    document.querySelector('#product-form button[type="submit"]');
  if (submitButton) {
    submitButton.textContent = "Додати товар";
  }

  const cancelEditButton = document.querySelector("#product-cancel-edit");
  if (cancelEditButton) {
    cancelEditButton.classList.add("hidden");
  }
}

function startEditingProduct(product) {
  if (!product) return;
  editingProductId = product.id;

  const nameInput = document.querySelector("#product-name");
  const categorySelect = document.querySelector("#product-category");
  const brandSelect = document.querySelector("#product-brand");
  const priceInput = document.querySelector("#product-price");
  const stockInput = document.querySelector("#product-stock");
  const imageInput = document.querySelector("#product-image");
  const descriptionInput = document.querySelector("#product-description");

  if (nameInput) nameInput.value = product.name || "";
  if (categorySelect) {
    categorySelect.value = product.category || "keyboard";
  }
  updateProductCategoryAttributesFields();

  ensureBrandOptionExists(product.brand);
  if (brandSelect) {
    brandSelect.value = product.brand || "Logitech";
  }
  if (priceInput) priceInput.value = String(product.price ?? "");
  if (stockInput) stockInput.value = String(product.stock ?? 0);
  if (imageInput) imageInput.value = product.image || "";
  if (descriptionInput) descriptionInput.value = product.description || "";

  populateProductCategoryAttributeInputs(product.category, product.attributes);

  const formTitle = document.querySelector("#product-form-title");
  if (formTitle) {
    formTitle.textContent = `Редагування товару #${product.id}: ${product.name}`;
  }

  const submitButton =
    document.querySelector("#product-submit") ||
    document.querySelector('#product-form button[type="submit"]');
  if (submitButton) {
    submitButton.textContent = "Зберегти зміни";
  }

  const cancelEditButton = document.querySelector("#product-cancel-edit");
  if (cancelEditButton) {
    cancelEditButton.classList.remove("hidden");
  }

  showAdminProductMessage(
    `Редагування товару «${product.name}» (ID #${product.id}). Внесіть зміни та натисніть «Зберегти зміни».`,
    false,
  );

  productForm?.scrollIntoView?.({ behavior: "smooth", block: "start" });
}

async function deleteAdminProduct(product, buttonEl = null) {
  if (!isAdminUser()) {
    showAdminProductMessage("Доступ дозволено лише адміністраторам.", true);
    return;
  }

  const confirmed = confirm(`Видалити товар "${product.name}"?`);
  if (!confirmed) return;

  if (buttonEl) {
    buttonEl.disabled = true;
  }

  try {
    await apiRequest(`/products/${encodeURIComponent(product.id)}`, {
      method: "DELETE",
      requiresAuth: true,
    });

    const cartIndex = cart.findIndex((item) => item.productId === product.id);
    if (cartIndex !== -1) {
      cart.splice(cartIndex, 1);
      saveCart();
    }

    if (editingProductId === product.id) {
      resetProductFormMode();
    }

    showAdminProductMessage(
      `Товар «${product.name}» успішно видалено з каталогу.`,
      false,
    );
    showToast("Товар видалено");

    await loadProducts();
  } catch (error) {
    console.error("Помилка видалення товару:", error);
    showAdminProductMessage(
      error.message || "Не вдалося видалити товар.",
      true,
    );
    if (buttonEl) {
      buttonEl.disabled = false;
    }
  }
}

function renderAdminProducts() {
  if (!adminProductList) return;
  adminProductList.replaceChildren();

  if (isCatalogLoading) {
    const loadingEl = document.createElement("p");
    loadingEl.className = "catalog-status";
    loadingEl.textContent = "Завантаження списку товарів...";
    adminProductList.append(loadingEl);
    return;
  }

  if (catalogError) {
    const errorBox = document.createElement("div");
    errorBox.className = "catalog-status catalog-error";

    const errorText = document.createElement("p");
    errorText.textContent = catalogError;

    const retryButton = document.createElement("button");
    retryButton.type = "button";
    retryButton.textContent = "Спробувати знову";
    retryButton.addEventListener("click", () => loadProducts());

    errorBox.append(errorText, retryButton);
    adminProductList.append(errorBox);
    return;
  }

  if (products.length === 0) {
    const emptyEl = document.createElement("p");
    emptyEl.className = "catalog-status";
    emptyEl.textContent = "У каталозі поки немає товарів.";
    adminProductList.append(emptyEl);
    return;
  }

  products.forEach((product) => {
    const row = document.createElement("div");
    row.className = "admin-product-card";
    row.dataset.productId = String(product.id);

    // Зображення товару
    const imageContainer = document.createElement("div");
    imageContainer.className = "admin-product-image-container";

    const image = document.createElement("img");
    image.className = "admin-product-image";
    image.src = product.image || "";
    image.alt = product.name;

    image.addEventListener("error", () => {
      image.style.display = "none";
      imageContainer.classList.add("no-image");
      imageContainer.textContent = "Немає фото";
    });

    if (!product.image) {
      image.style.display = "none";
      imageContainer.classList.add("no-image");
      imageContainer.textContent = "Немає фото";
    }

    imageContainer.append(image);

    // Інформація про товар
    const info = document.createElement("div");
    info.className = "admin-product-info";

    const name = document.createElement("h3");
    name.textContent = `#${product.id} · ${product.name}`;

    const categoryLabel =
      CATEGORY_LABELS[product.category] || product.category || "—";
    const meta = document.createElement("p");
    meta.textContent = `Категорія: ${categoryLabel} · Виробник: ${product.brand}`;

    const price = document.createElement("p");
    price.className = "admin-product-price";
    price.textContent = formatPrice(product.price);

    const stock = document.createElement("p");
    stock.className = "admin-product-stock";
    stock.textContent = `На складі: ${product.stock} шт.`;

    info.append(name, meta, price, stock);

    if (product.description) {
      const desc = document.createElement("p");
      desc.className = "admin-product-description";
      desc.textContent = `Опис: ${product.description}`;
      info.append(desc);
    }

    // Блок кнопок дій (Редагувати + Видалити)
    const actionsBox = document.createElement("div");
    actionsBox.className = "admin-product-actions";

    const editButton = document.createElement("button");
    editButton.type = "button";
    editButton.className = "admin-edit-button";
    editButton.textContent = "Редагувати";
    editButton.addEventListener("click", () => {
      startEditingProduct(product);
    });

    const deleteButton = document.createElement("button");
    deleteButton.type = "button";
    deleteButton.className = "admin-delete-button";
    deleteButton.textContent = "Видалити";
    deleteButton.addEventListener("click", () =>
      deleteAdminProduct(product, deleteButton),
    );

    actionsBox.append(editButton, deleteButton);

    row.append(imageContainer, info, actionsBox);
    adminProductList.append(row);
  });
}

// =====================================
// SEARCH, FILTERS AND SORTING
// =====================================

searchInput.addEventListener("input", renderProducts);
categoryFilter.addEventListener("change", renderProducts);
sortSelect.addEventListener("change", renderProducts);

const priceFilter = document.querySelector("#price-filter");
const priceFilterValue = document.querySelector("#price-filter-value");

const brandFilters = document.querySelectorAll('input[name="brand-filter"]');

// Фільтр за максимальною ціною
if (priceFilter) {
  priceFilter.addEventListener("input", () => {
    if (priceFilterValue) {
      priceFilterValue.textContent =
        Number(priceFilter.value).toLocaleString("uk-UA") + " грн";
    }

    renderProducts();
  });
}

// Фільтр за виробником
brandFilters.forEach((checkbox) => {
  checkbox.addEventListener("change", renderProducts);
});

// Кнопки категорій у бічній панелі
document.querySelectorAll(".category-button").forEach((button) => {
  button.addEventListener("click", () => {
    categoryFilter.value = button.dataset.category;

    document.querySelectorAll(".category-button").forEach((item) => {
      item.classList.toggle("active", item === button);
    });

    renderProducts();
  });
});

// Синхронізація активної категорії
// з випадаючим списком
categoryFilter.addEventListener("change", () => {
  document.querySelectorAll(".category-button").forEach((button) => {
    button.classList.toggle(
      "active",
      button.dataset.category === categoryFilter.value,
    );
  });
});

// =====================================
// GRID AND LIST VIEW
// =====================================

const gridViewButton = document.querySelector("#grid-view");
const listViewButton = document.querySelector("#list-view");

gridViewButton.addEventListener("click", () => {
  productList.classList.remove("list-view");
  gridViewButton.classList.add("active");
  listViewButton.classList.remove("active");
});

listViewButton.addEventListener("click", () => {
  productList.classList.add("list-view");
  listViewButton.classList.add("active");
  gridViewButton.classList.remove("active");
});

// =====================================
// CLEAR CART
// =====================================

document.querySelector("#clear-cart").addEventListener("click", () => {
  cart.length = 0;
  saveCart();
  renderCart();
  renderProducts();
});

// =====================================
// CHECKOUT (POST /orders)
// =====================================

function requiresDeliveryAddress(deliveryType) {
  return Boolean(deliveryType && deliveryType !== "pickup");
}

function getExpectedDeliveryCost(deliveryType) {
  if (!deliveryType || deliveryType === "pickup") {
    return 0;
  }
  return DEFAULT_DELIVERY_COST;
}

function showCheckoutMessage(message, isError = false) {
  if (!checkoutMessage) return;

  checkoutMessage.textContent = message;
  checkoutMessage.classList.toggle("error", isError);
  checkoutMessage.classList.toggle("success", !isError && Boolean(message));
}

function prefillCheckoutCustomerData() {
  if (!currentUser) return;

  if (customerNameInput && !customerNameInput.value.trim() && currentUser.name) {
    customerNameInput.value = currentUser.name;
  }

  if (
    customerEmailInput &&
    !customerEmailInput.value.trim() &&
    currentUser.email
  ) {
    customerEmailInput.value = currentUser.email;
  }
}

function updateDeliveryFields() {
  const deliveryType = deliverySelect ? deliverySelect.value : "pickup";
  const needsAddress = requiresDeliveryAddress(deliveryType);

  if (deliveryAddressGroup) {
    deliveryAddressGroup.classList.toggle("hidden", !needsAddress);
  }

  if (deliveryAddressInput) {
    deliveryAddressInput.required = needsAddress;
  }

  updateCheckoutSummary();
}

function updateCheckoutSummary(confirmedOrder = null) {
  if (confirmedOrder) {
    const itemsTotal = Number(confirmedOrder.items_total ?? 0);
    const deliveryCost = Number(confirmedOrder.delivery_cost ?? 0);
    const totalAmount = Number(confirmedOrder.total_amount ?? 0);

    if (checkoutItemsTotalEl) {
      checkoutItemsTotalEl.textContent = formatPrice(itemsTotal);
    }
    if (checkoutDeliveryCostEl) {
      checkoutDeliveryCostEl.textContent = formatPrice(deliveryCost);
    }
    if (checkoutTotalAmountEl) {
      checkoutTotalAmountEl.textContent = formatPrice(totalAmount);
    }
    return;
  }

  const subtotal = calculateCartSubtotal();
  const deliveryType = deliverySelect ? deliverySelect.value : "pickup";
  const deliveryCost =
    cart.length > 0 ? getExpectedDeliveryCost(deliveryType) : 0;
  const totalAmount = subtotal + deliveryCost;

  if (checkoutItemsTotalEl) {
    checkoutItemsTotalEl.textContent = formatPrice(subtotal);
  }
  if (checkoutDeliveryCostEl) {
    checkoutDeliveryCostEl.textContent = formatPrice(deliveryCost);
  }
  if (checkoutTotalAmountEl) {
    checkoutTotalAmountEl.textContent = formatPrice(totalAmount);
  }
}

deliverySelect?.addEventListener("change", () => {
  updateDeliveryFields();
});

checkoutForm.addEventListener("submit", async (event) => {
  event.preventDefault();

  if (isSubmittingOrder) {
    return;
  }

  if (cart.length === 0) {
    showCheckoutMessage("Спочатку додайте товари в кошик.", true);
    return;
  }

  for (const item of cart) {
    if (
      !Number.isInteger(item.productId) ||
      item.productId <= 0 ||
      !Number.isInteger(item.quantity) ||
      item.quantity <= 0
    ) {
      showCheckoutMessage("У кошику виявлено некоректні дані товару.", true);
      return;
    }

    const product = products.find(
      (candidate) => candidate.id === item.productId,
    );

    if (!product || product.stock <= 0 || item.quantity > product.stock) {
      showCheckoutMessage(
        "Замовлення неможливо оформити: перевірте наявність товарів.",
        true,
      );
      return;
    }
  }

  const customerName = customerNameInput ? customerNameInput.value.trim() : "";
  const customerEmail = customerEmailInput
    ? customerEmailInput.value.trim()
    : "";
  const deliveryType = deliverySelect ? deliverySelect.value : "pickup";
  const deliveryAddress = deliveryAddressInput
    ? deliveryAddressInput.value.trim()
    : "";
  const paymentType = paymentSelect ? paymentSelect.value : "card";

  if (!customerName || !customerEmail) {
    showCheckoutMessage("Заповніть дані покупця.", true);
    return;
  }

  if (!customerEmail.includes("@")) {
    showCheckoutMessage("Вкажіть коректну електронну пошту покупця.", true);
    return;
  }

  if (requiresDeliveryAddress(deliveryType) && !deliveryAddress) {
    showCheckoutMessage("Вкажіть адресу доставки або відділення.", true);
    return;
  }

  const orderPayload = {
    customer_name: customerName,
    customer_email: customerEmail,
    delivery_type: deliveryType,
    delivery_address:
      deliveryType === "pickup" ? deliveryAddress || null : deliveryAddress,
    payment_type: paymentType,
    items: cart.map((item) => ({
      product_id: Number(item.productId),
      quantity: Number(item.quantity),
    })),
  };

  isSubmittingOrder = true;
  if (checkoutSubmitButton) {
    checkoutSubmitButton.disabled = true;
  }
  showCheckoutMessage("Оформлюємо замовлення...");

  try {
    const createdOrder = await apiRequest("/orders", {
      method: "POST",
      body: orderPayload,
      includeAuth: true,
    });

    // Очищуємо кошик ТІЛЬКИ після успішного підтвердження від бекенду
    cart.length = 0;
    saveCart();
    renderCart();

    checkoutForm.reset();
    prefillCheckoutCustomerData();
    updateDeliveryFields();
    updateCheckoutSummary(createdOrder);

    const itemsTotal = Number(createdOrder.items_total ?? 0);
    const deliveryCost = Number(createdOrder.delivery_cost ?? 0);
    const totalAmount = Number(createdOrder.total_amount ?? 0);

    showCheckoutMessage(
      `Замовлення №${createdOrder.id} успішно створено! Товари: ${formatPrice(itemsTotal)}, доставка: ${formatPrice(deliveryCost)}, разом до сплати: ${formatPrice(totalAmount)}.`,
      false,
    );

    // Оновлюємо залишки товарів із бекенду
    await loadProducts();

    // Якщо користувач авторизований, оновлюємо його історію замовлень
    if (getAccessToken()) {
      await loadCustomerOrders();
    }
  } catch (error) {
    console.error("Помилка оформлення замовлення:", error);

    showCheckoutMessage(
      error.message ||
        "Не вдалося оформити замовлення. Перевірте наявність товарів і спробуйте ще раз.",
      true,
    );

    // Синхронізуємо залишки з бекендом, зберігаючи вміст кошика незмінним
    await loadProducts();
  } finally {
    isSubmittingOrder = false;
    if (checkoutSubmitButton) {
      checkoutSubmitButton.disabled = false;
    }
  }
});

// =====================================
// ADD / EDIT PRODUCT (POST /products, PUT /products/{id})
// =====================================

document
  .querySelector("#product-category")
  ?.addEventListener("change", () => {
    clearProductCategoryAttributeInputs();
    updateProductCategoryAttributesFields();
  });

document
  .querySelector("#product-cancel-edit")
  ?.addEventListener("click", () => {
    resetProductFormMode();
    showAdminProductMessage("Редагування скасовано.", false);
  });

productForm?.addEventListener("submit", async (event) => {
  event.preventDefault();

  if (isSubmittingProduct) {
    return;
  }

  if (!isAdminUser()) {
    showAdminProductMessage("Доступ дозволено лише адміністраторам.", true);
    return;
  }

  const name = (document.querySelector("#product-name")?.value || "").trim();
  const category = document.querySelector("#product-category")?.value || "";
  const brand = (document.querySelector("#product-brand")?.value || "").trim();
  const priceRaw = document.querySelector("#product-price")?.value ?? "";
  const stockRaw = document.querySelector("#product-stock")?.value ?? "";
  const imageRaw = (
    document.querySelector("#product-image")?.value || ""
  ).trim();
  const descriptionRaw = (
    document.querySelector("#product-description")?.value || ""
  ).trim();

  const price = Number(priceRaw);
  const stock = Number(stockRaw);

  if (!name) {
    showAdminProductMessage("Вкажіть назву товару.", true);
    return;
  }

  if (!brand) {
    showAdminProductMessage("Оберіть або вкажіть виробника товару.", true);
    return;
  }

  if (!category || !CATEGORY_LABELS[category]) {
    showAdminProductMessage("Оберіть коректну категорію товару.", true);
    return;
  }

  if (
    String(priceRaw).trim() === "" ||
    !Number.isFinite(price) ||
    price <= 0
  ) {
    showAdminProductMessage(
      "Ціна товару має бути додатним числом (більше 0 грн).",
      true,
    );
    return;
  }

  if (
    String(stockRaw).trim() === "" ||
    !Number.isInteger(stock) ||
    stock < 0
  ) {
    showAdminProductMessage(
      "Кількість на складі має бути невід'ємним цілим числом.",
      true,
    );
    return;
  }

  let attributes = {};
  try {
    attributes = collectAndValidateProductAttributes(category);
  } catch (validationError) {
    showAdminProductMessage(validationError.message, true);
    return;
  }

  const payload = {
    name,
    brand,
    category,
    price,
    stock_quantity: stock,
    image: imageRaw || null,
    attributes,
    description: descriptionRaw || null,
  };

  const submitButton =
    document.querySelector("#product-submit") ||
    document.querySelector('#product-form button[type="submit"]');

  isSubmittingProduct = true;
  if (submitButton) {
    submitButton.disabled = true;
  }

  const isEditing = editingProductId !== null;
  showAdminProductMessage(
    isEditing ? "Зберігаємо зміни товару..." : "Додаємо новий товар...",
  );

  try {
    if (isEditing) {
      const updated = await apiRequest(
        `/products/${encodeURIComponent(editingProductId)}`,
        {
          method: "PUT",
          body: payload,
          requiresAuth: true,
        },
      );

      resetProductFormMode();
      showAdminProductMessage(
        `Товар «${updated.name}» (ID #${updated.id}) успішно оновлено.`,
        false,
      );
      showToast("Товар успішно оновлено");
    } else {
      const created = await apiRequest("/products", {
        method: "POST",
        body: payload,
        requiresAuth: true,
      });

      resetProductFormMode();
      showAdminProductMessage(
        `Товар «${created.name}» (ID #${created.id}) успішно додано до каталогу.`,
        false,
      );
      showToast("Товар додано до каталогу");
    }

    await loadProducts();
  } catch (error) {
    console.error("Помилка збереження товару:", error);
    showAdminProductMessage(
      error.message || "Не вдалося зберегти товар.",
      true,
    );
  } finally {
    isSubmittingProduct = false;
    if (submitButton) {
      submitButton.disabled = false;
    }
  }
});

// =====================================
// INITIAL RENDER
// =====================================

updateProductCategoryAttributesFields();
renderCart();
renderOrders();
renderAdminProducts();
renderAdminOrders();
loadProducts();

showPage("catalog");

// Кнопка переходу до каталогу з головного банера
document.querySelector("#browse-products").addEventListener("click", () => {
  showPage("catalog");

  document.querySelector("#product-list").scrollIntoView({
    behavior: "smooth",
    block: "start",
  });
});

// =====================================
// ACCOUNT: REGISTRATION AND LOGIN
// =====================================

const loginForm = document.querySelector("#login-form");
const registerForm = document.querySelector("#register-form");
const authMessage = document.querySelector("#auth-message");
const authTabs = document.querySelectorAll("[data-auth-tab]");
const accountContainer = document.querySelector(".account-container");

function sanitizeAuthenticatedUser(rawUser, token) {
  const payload = parseJwtPayload(token);
  const trustedRole =
    payload && (payload.role === "Admin" || payload.role === "Customer")
      ? payload.role
      : rawUser?.role === "Admin"
        ? "Admin"
        : "Customer";

  return {
    name: String(rawUser?.name || "").trim(),
    email: String(rawUser?.email || "").trim(),
    role: trustedRole,
  };
}

function restoreAuthenticatedSession() {
  const token = getAccessToken();
  if (!token) {
    sessionStorage.removeItem(USER_STORAGE_KEY);
    currentUser = null;
    return;
  }

  try {
    const savedUserRaw = sessionStorage.getItem(USER_STORAGE_KEY);
    if (!savedUserRaw) {
      sessionStorage.removeItem(TOKEN_STORAGE_KEY);
      currentUser = null;
      return;
    }

    const parsedUser = JSON.parse(savedUserRaw);
    currentUser = sanitizeAuthenticatedUser(parsedUser, token);
    sessionStorage.setItem(USER_STORAGE_KEY, JSON.stringify(currentUser));
  } catch (error) {
    console.error("Не вдалося прочитати дані користувача:", error);
    sessionStorage.removeItem(TOKEN_STORAGE_KEY);
    sessionStorage.removeItem(USER_STORAGE_KEY);
    currentUser = null;
  }
}

// Повідомлення для користувача
function showAuthMessage(message, isError = false) {
  if (!authMessage) return;

  authMessage.textContent = message;
  authMessage.classList.toggle("error", isError);
  authMessage.classList.toggle("success", !isError && Boolean(message));
}

// Перемикання між входом і реєстрацією
function switchAuthTab(tabName) {
  const showLogin = tabName === "login";

  if (!loginForm || !registerForm) return;

  loginForm.classList.toggle("hidden", !showLogin);
  registerForm.classList.toggle("hidden", showLogin);

  authTabs.forEach((tab) => {
    tab.classList.toggle("active", tab.dataset.authTab === tabName);
  });

  showAuthMessage("");
}

authTabs.forEach((tab) => {
  tab.addEventListener("click", () => {
    switchAuthTab(tab.dataset.authTab);
  });
});

// Збереження авторизованого користувача (без пароля, роль верифікується за JWT/бекендом)
function saveAuthenticatedUser(user, token) {
  if (!token || isTokenExpired(token)) {
    throw new Error("Отримано недійсний або прострочений токен авторизації.");
  }

  const sanitizedUser = sanitizeAuthenticatedUser(user, token);
  sessionStorage.setItem(TOKEN_STORAGE_KEY, token);
  sessionStorage.setItem(USER_STORAGE_KEY, JSON.stringify(sanitizedUser));
  currentUser = sanitizedUser;

  prefillCheckoutCustomerData();
  updateAdminNavigationVisibility();
  renderAccount();
  loadCustomerOrders();

  if (isAdminUser()) {
    loadAdminOrders();
    renderAdminProducts();
  } else {
    adminOrders = [];
    renderAdminOrders();
  }
}

// Вихід з акаунта
function clearAuthenticatedUser() {
  sessionStorage.removeItem(TOKEN_STORAGE_KEY);
  sessionStorage.removeItem(USER_STORAGE_KEY);

  currentUser = null;
  customerOrders = [];
  ordersError = null;
  isOrdersLoading = false;

  adminOrders = [];
  adminOrdersError = null;
  isAdminOrdersLoading = false;
  resetProductFormMode();
  showAdminProductMessage("");
  showAdminOrdersMessage("");
  renderAdminOrderDetailsPanel(null);

  loginForm?.reset();
  registerForm?.reset();

  updateAdminNavigationVisibility();
  renderAccount();
  renderOrders();
  renderAdminOrders();

  const adminPageEl = document.querySelector("#admin");
  const adminOrdersPageEl = document.querySelector("#admin-orders");
  const adminSectionVisible =
    (adminPageEl && !adminPageEl.classList.contains("hidden")) ||
    (adminOrdersPageEl && !adminOrdersPageEl.classList.contains("hidden"));
  if (adminSectionVisible) {
    showPage("account");
  }
}

// Відображення особистого кабінету
function renderAccount() {
  if (!accountContainer || !loginForm || !registerForm || !authMessage) {
    return;
  }

  let profile = document.querySelector("#account-profile");

  if (!profile) {
    profile = document.createElement("div");
    profile.id = "account-profile";
    profile.className = "account-profile hidden";
    accountContainer.append(profile);
  }

  const token = getAccessToken();
  if (token && currentUser) {
    currentUser = sanitizeAuthenticatedUser(currentUser, token);
  } else {
    currentUser = null;
  }

  const isLoggedIn = Boolean(currentUser && token);

  loginForm.classList.toggle("hidden", isLoggedIn);
  registerForm.classList.add("hidden");

  const tabsContainer = document.querySelector(".auth-tabs");

  if (tabsContainer) {
    tabsContainer.classList.toggle("hidden", isLoggedIn);
  }

  authMessage.classList.toggle("hidden", isLoggedIn);
  profile.classList.toggle("hidden", !isLoggedIn);

  if (!isLoggedIn) {
    switchAuthTab("login");
    return;
  }

  profile.replaceChildren();

  const heading = document.createElement("h3");
  heading.textContent = "Ваш обліковий запис";

  const greeting = document.createElement("p");
  greeting.textContent = `Вітаємо, ${currentUser.name || "користувачу"}!`;

  const email = document.createElement("p");
  email.textContent = `Електронна пошта: ${currentUser.email || "Не вказана"}`;

  const role = document.createElement("p");
  role.textContent = `Тип облікового запису: ${currentUser.role || "Customer"}`;

  const logoutButton = document.createElement("button");
  logoutButton.type = "button";
  logoutButton.textContent = "Вийти з акаунта";

  logoutButton.addEventListener("click", () => {
    clearAuthenticatedUser();
    showAuthMessage("Ви вийшли з акаунта.");
  });

  profile.append(heading, greeting, email, role, logoutButton);
}

// Запит авторизації через централізований apiRequest
async function sendAuthRequest(endpoint, payload) {
  return apiRequest(endpoint, {
    method: "POST",
    body: payload,
    includeAuth: false,
  });
}

// =====================================
// REGISTRATION
// =====================================

registerForm?.addEventListener("submit", async (event) => {
  event.preventDefault();

  const name = document.querySelector("#register-name").value.trim();
  const email = document.querySelector("#register-email").value.trim();
  const password = document.querySelector("#register-password").value;

  if (!name) {
    showAuthMessage("Ім'я не може бути порожнім.", true);
    return;
  }

  if (!email || !email.includes("@")) {
    showAuthMessage("Введіть коректну адресу електронної пошти.", true);
    return;
  }

  if (password.length < 8) {
    showAuthMessage("Пароль повинен містити щонайменше 8 символів.", true);
    return;
  }

  showAuthMessage("Створюємо акаунт...");

  try {
    const data = await sendAuthRequest("/auth/register", {
      name,
      email,
      password,
    });

    registerForm.reset();

    if (data.access_token) {
      const user = data.user || {
        name,
        email,
        role: "Customer",
      };

      saveAuthenticatedUser(user, data.access_token);
      showAuthMessage("Акаунт успішно створено!");
    } else {
      switchAuthTab("login");

      const loginEmail = document.querySelector("#login-email");
      if (loginEmail) {
        loginEmail.value = email;
      }

      showAuthMessage("Акаунт успішно створено. Тепер увійдіть у систему.");
    }
  } catch (error) {
    console.error("Помилка реєстрації:", error);

    showAuthMessage(
      error.message ||
        "Не вдалося зареєструватися. Перевірте з'єднання із сервером.",
      true,
    );
  }
});

// =====================================
// LOGIN
// =====================================

loginForm?.addEventListener("submit", async (event) => {
  event.preventDefault();

  const email = document.querySelector("#login-email").value.trim();
  const password = document.querySelector("#login-password").value;

  if (!email || !email.includes("@")) {
    showAuthMessage("Введіть коректну адресу електронної пошти.", true);
    return;
  }

  if (!password) {
    showAuthMessage("Введіть пароль.", true);
    return;
  }

  showAuthMessage("Виконується вхід...");

  try {
    const data = await sendAuthRequest("/auth/login", {
      email,
      password,
    });

    if (!data.access_token) {
      throw new Error("Сервер не повернув токен авторизації.");
    }

    loginForm.reset();

    const user = data.user || {
      name: email.split("@")[0],
      email,
      role: "Customer",
    };

    saveAuthenticatedUser(user, data.access_token);

    showAuthMessage("Ви успішно увійшли!");
  } catch (error) {
    console.error("Помилка входу:", error);

    showAuthMessage(
      error.message || "Не вдалося увійти. Перевірте пошту та пароль.",
      true,
    );
  }
});

// Відновлення сесії та кабінету після перезавантаження сторінки
restoreAuthenticatedSession();
updateAdminNavigationVisibility();
prefillCheckoutCustomerData();
updateDeliveryFields();
renderAccount();
if (getAccessToken()) {
  loadCustomerOrders();
  if (isAdminUser()) {
    loadAdminOrders();
  }
} else {
  renderOrders();
}
