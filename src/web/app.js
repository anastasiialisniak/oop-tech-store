const products = [
  {
    id: 1,
    name: "Mechanical Keyboard",
    brand: "Logitech",
    category: "keyboard",
    price: 2500,
    stock: 10,
    image: "images/mechanical-keyboard.jpg.jpg",
  },
  {
    id: 2,
    name: "Gaming Mouse",
    brand: "Logitech",
    category: "mouse",
    price: 1500,
    stock: 20,
    image: "images/gaming-mouse.jpg.jpg",
  },
  {
    id: 3,
    name: "Gaming Headset",
    brand: "HyperX",
    category: "headphones",
    price: 3200,
    stock: 15,
    image: "images/gaming-headset.jpg.jpg",
  },
  {
    id: 4,
    name: "Full HD Webcam",
    brand: "Logitech",
    category: "webcam",
    price: 2200,
    stock: 8,
    image: "images/full-hd-webcam.jpg.jpg",
  },

  {
    id: 5,
    name: "Wireless Keyboard",
    brand: "Logitech",
    category: "keyboard",
    price: 1800,
    stock: 12,
    image: "images/wireless-keyboard.jpg.jpg",
  },
  {
    id: 6,
    name: "Gaming Mouse Pro",
    brand: "Razer",
    category: "mouse",
    price: 2800,
    stock: 7,
    image: "images/gaming-mouse-pro.jpg.jpg",
  },
  {
    id: 7,
    name: "Wireless Headphones",
    brand: "Sony",
    category: "headphones",
    price: 4500,
    stock: 5,
    image: "images/wireless-headphones.jpg.jpg",
  },
  {
    id: 8,
    name: "Streaming Webcam",
    brand: "AverMedia",
    category: "webcam",
    price: 3900,
    stock: 4,
    image: "images/streaming-webcam.jpg.jpg",
  },
];

const cart = [];
const savedOrders = localStorage.getItem("nexora-orders");

const orders = savedOrders ? JSON.parse(savedOrders) : [];
function saveOrders() {
  localStorage.setItem("nexora-orders", JSON.stringify(orders));
}

const pages = document.querySelectorAll(".page");
const navigationButtons = document.querySelectorAll("[data-page]");

const productList = document.querySelector("#product-list");
const searchInput = document.querySelector("#search");
const categoryFilter = document.querySelector("#category-filter");
const sortSelect = document.querySelector("#sort");

const cartItems = document.querySelector("#cart-items");
const cartTotal = document.querySelector("#cart-total");
const cartCount = document.querySelector("#cart-count");

const checkoutForm = document.querySelector("#checkout-form");
const checkoutMessage = document.querySelector("#checkout-message");
const ordersTable = document.querySelector("#orders-table");
const adminOrdersTable = document.querySelector("#admin-orders-table");
const productForm = document.querySelector("#product-form");
const adminProductList = document.querySelector("#admin-product-list");

function showPage(pageId) {
  pages.forEach((page) => {
    page.classList.toggle("hidden", page.id !== pageId);
  });
}

navigationButtons.forEach((button) => {
  button.addEventListener("click", () => {
    const pageId = button.dataset.page;

    if (pageId === "checkout") {
      checkoutMessage.textContent = "";
    }

    showPage(pageId);
  });
});

function formatPrice(price) {
  return `${price.toLocaleString("uk-UA")} грн`;
}

function renderProducts() {
  const search = searchInput.value.trim().toLowerCase();
  const category = categoryFilter.value;
  const sort = sortSelect.value;

  const maxPrice = document.querySelector("#price-filter")
    ? Number(document.querySelector("#price-filter").value)
    : 10000;

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

  productList.replaceChildren();

  if (filteredProducts.length === 0) {
    productList.textContent = "Товарів не знайдено.";
    return;
  }

  filteredProducts.forEach((product) => {
    const card = document.createElement("article");
    card.className = "product-card";

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

function addToCart(productId) {
  const product = products.find((item) => item.id === productId);

  if (!product || product.stock <= 0) {
    alert("Цей товар зараз недоступний.");
    return;
  }

  const cartItem = cart.find((item) => item.productId === productId);

  if (cartItem) {
    if (cartItem.quantity >= product.stock) {
      alert("Недостатньо товару на складі.");
      return;
    }

    cartItem.quantity += 1;
  } else {
    cart.push({ productId, quantity: 1 });
  }

  renderCart();
  renderProducts();
}

function renderCart() {
  cartItems.replaceChildren();

  let total = 0;
  let totalQuantity = 0;

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
    cartCount.textContent = "0";
    return;
  }

  cart.forEach((item) => {
    const product = products.find(
      (candidate) => candidate.id === item.productId,
    );

    if (!product) return;

    total += product.price * item.quantity;
    totalQuantity += item.quantity;

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
    description.textContent =
      `${product.name} × ${item.quantity} — ` +
      formatPrice(product.price * item.quantity);

    const decreaseButton = document.createElement("button");
    decreaseButton.textContent = "−";
    decreaseButton.setAttribute("aria-label", "Зменшити кількість");

    decreaseButton.addEventListener("click", () => {
      item.quantity -= 1;

      if (item.quantity <= 0) {
        cart.splice(cart.indexOf(item), 1);
      }

      renderCart();
    });

    const increaseButton = document.createElement("button");
    increaseButton.textContent = "+";
    increaseButton.setAttribute("aria-label", "Збільшити кількість");

    increaseButton.addEventListener("click", () => {
      if (item.quantity >= product.stock) {
        alert("Недостатньо товару на складі.");
        return;
      }

      item.quantity += 1;
      renderCart();
    });

    const removeButton = document.createElement("button");
    removeButton.textContent = "Видалити";

    removeButton.addEventListener("click", () => {
      cart.splice(cart.indexOf(item), 1);
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
  cartCount.textContent = totalQuantity;
}

function renderOrders() {
  ordersTable.replaceChildren();

  orders.forEach((order) => {
    const row = document.createElement("tr");

    const deliveryNames = {
      pickup: "Самовивіз",
      "nova-poshta": "Нова пошта",
      ukrposhta: "Укрпошта",
      courier: "Кур'єрська доставка",
    };

    const values = [
      order.id,
      order.customer,
      formatPrice(order.total),
      order.date,
      deliveryNames[order.delivery] || order.delivery,
      order.status,
    ];

    values.forEach((value) => {
      const cell = document.createElement("td");
      cell.textContent = value;
      row.append(cell);
    });

    ordersTable.append(row);
  });
}

function renderAdminOrders() {
  adminOrdersTable.replaceChildren();

  const deliveryNames = {
    pickup: "Самовивіз",
    "nova-poshta": "Нова пошта",
    ukrposhta: "Укрпошта",
    courier: "Кур'єрська доставка",
  };

  const statusOptions = [
    { value: "Нове", label: "Нове" },
    { value: "Підтверджено", label: "Підтверджено" },
    { value: "Відправлено", label: "Відправлено" },
    { value: "Виконано", label: "Виконано" },
    { value: "Скасовано", label: "Скасовано" },
  ];

  orders.forEach((order) => {
    const row = document.createElement("tr");

    const values = [
      order.id,
      order.customer,
      formatPrice(order.total),
      order.date,
      deliveryNames[order.delivery] || order.delivery,
    ];

    values.forEach((value) => {
      const cell = document.createElement("td");
      cell.textContent = value;
      row.append(cell);
    });

    const statusCell = document.createElement("td");
    const statusSelect = document.createElement("select");

    statusOptions.forEach((option) => {
      const element = document.createElement("option");
      element.value = option.value;
      element.textContent = option.label;
      statusSelect.append(element);
    });

    statusSelect.value = order.status;

    statusSelect.addEventListener("change", () => {
      order.status = statusSelect.value;
      renderOrders();
    });

    statusCell.append(statusSelect);

    const actionCell = document.createElement("td");
    const saveButton = document.createElement("button");
    saveButton.textContent = "Зберегти статус";

    saveButton.addEventListener("click", () => {
      order.status = statusSelect.value;
      renderOrders();
      alert(`Статус замовлення №${order.id} змінено.`);
    });

    actionCell.append(saveButton);
    row.append(statusCell, actionCell);
    adminOrdersTable.append(row);
  });
}

function renderAdminProducts() {
  adminProductList.replaceChildren();

  products.forEach((product) => {
    const row = document.createElement("div");
    row.className = "product-card";

    const description = document.createElement("p");
    description.textContent =
      `${product.name} — ${formatPrice(product.price)}, ` +
      `залишок: ${product.stock}`;

    const deleteButton = document.createElement("button");
    deleteButton.textContent = "Видалити товар";

    deleteButton.addEventListener("click", () => {
      const index = products.findIndex((item) => item.id === product.id);

      if (index !== -1) {
        products.splice(index, 1);
      }

      const cartIndex = cart.findIndex((item) => item.productId === product.id);

      if (cartIndex !== -1) {
        cart.splice(cartIndex, 1);
      }

      renderProducts();
      renderCart();
      renderAdminProducts();
    });

    row.append(description, deleteButton);
    adminProductList.append(row);
  });
}

searchInput.addEventListener("input", renderProducts);
categoryFilter.addEventListener("change", renderProducts);
sortSelect.addEventListener("change", renderProducts);

const priceFilter = document.querySelector("#price-filter");
const priceFilterValue = document.querySelector("#price-filter-value");

const brandFilters = document.querySelectorAll('input[name="brand-filter"]');

// Фільтр за максимальною ціною
if (priceFilter) {
  priceFilter.addEventListener("input", () => {
    priceFilterValue.textContent =
      Number(priceFilter.value).toLocaleString("uk-UA") + " грн";

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

// Синхронізація активної категорії з випадаючим списком
categoryFilter.addEventListener("change", () => {
  document.querySelectorAll(".category-button").forEach((button) => {
    button.classList.toggle(
      "active",
      button.dataset.category === categoryFilter.value,
    );
  });
});

// Перемикання вигляду товарів
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

document.querySelector("#clear-cart").addEventListener("click", () => {
  cart.length = 0;
  renderCart();
  renderProducts();
});

checkoutForm.addEventListener("submit", (event) => {
  event.preventDefault();

  if (cart.length === 0) {
    checkoutMessage.textContent = "Спочатку додайте товари в кошик.";
    return;
  }

  for (const item of cart) {
    const product = products.find(
      (candidate) => candidate.id === item.productId,
    );

    if (!product || item.quantity > product.stock) {
      checkoutMessage.textContent =
        "Замовлення неможливо оформити: перевірте наявність товарів.";
      return;
    }
  }

  const customer = document.querySelector("#customer-name").value.trim();
  const email = document.querySelector("#customer-email").value.trim();

  if (!customer || !email) {
    checkoutMessage.textContent = "Заповніть дані покупця.";
    return;
  }

  const total = cart.reduce((sum, item) => {
    const product = products.find(
      (candidate) => candidate.id === item.productId,
    );

    return sum + product.price * item.quantity;
  }, 0);

  cart.forEach((item) => {
    const product = products.find(
      (candidate) => candidate.id === item.productId,
    );

    product.stock -= item.quantity;
  });

  orders.push({
    id: orders.length + 1,
    customer,
    email,
    total,
    date: new Date().toLocaleDateString("uk-UA"),
    delivery: document.querySelector("#delivery").value,
    payment: document.querySelector("#payment").value,
    status: "Нове",
  });
  saveOrders();
  cart.length = 0;

  checkoutMessage.textContent = `Замовлення успішно створено! Сума: ${formatPrice(total)}.`;

  checkoutForm.reset();
  checkoutMessage.textContent = "";

  renderCart();
  renderProducts();
  renderOrders();
  renderAdminProducts();
  renderAdminOrders();

  showPage("orders");
});

productForm.addEventListener("submit", (event) => {
  event.preventDefault();

  const name = document.querySelector("#product-name").value.trim();
  const category = document.querySelector("#product-category").value;
  const brand = document.querySelector("#product-brand").value;
  const price = Number(document.querySelector("#product-price").value);
  const stock = Number(document.querySelector("#product-stock").value);

  if (
    !name ||
    !Number.isFinite(price) ||
    price <= 0 ||
    !Number.isInteger(stock) ||
    stock < 0
  ) {
    alert("Перевірте назву, ціну та кількість товару.");
    return;
  }

  products.push({
    id: Math.max(0, ...products.map((item) => item.id)) + 1,
    name,
    brand,
    category,
    price,
    stock,
  });

  productForm.reset();
  renderProducts();
  renderAdminProducts();
});

renderCart();
renderProducts();
renderOrders();
renderAdminProducts();
renderAdminOrders();
showPage("orders");

document.querySelector("#browse-products").addEventListener("click", () => {
  showPage("catalog");
  document.querySelector("#product-list").scrollIntoView({
    behavior: "smooth",
    block: "start",
  });
});
showPage("catalog");
