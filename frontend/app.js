const API_BASE_URL = "http://136.111.161.172";

const productLooks = {
  mug: {
    image: "/images/product-mug.svg",
    background: "#e2dac8",
  },
  lamp: {
    image: "/images/product-lamp.svg",
    background: "#d8d9c7",
  },
  carafe: {
    image: "/images/product-carafe.svg",
    background: "#d2d8c9",
  },
  tote: {
    image: "/images/product-tote.svg",
    background: "#e3d2b9",
  },
};

const defaultLookOrder = ["mug", "lamp", "carafe", "tote"];

function getLook(product) {
  const name = `${product.name} ${product.category}`.toLowerCase();

  if (name.includes("mug") || name.includes("cup")) {
    return productLooks.mug;
  }

  if (name.includes("lamp") || name.includes("light")) {
    return productLooks.lamp;
  }

  if (
    name.includes("carafe") ||
    name.includes("bottle") ||
    name.includes("kitchen")
  ) {
    return productLooks.carafe;
  }

  if (name.includes("tote") || name.includes("bag")) {
    return productLooks.tote;
  }

  const key =
    defaultLookOrder[(product.id - 1) % defaultLookOrder.length];

  return productLooks[key];
}

let products = [];

let cart = {
  items: [],
  item_count: 0,
  subtotal: "0.00",
};

const productGrid = document.querySelector("#productGrid");
const accountLink = document.querySelector("#accountLink");
const cartButton = document.querySelector("#cartButton");
const cartCount = document.querySelector("#cartCount");
const cartDrawer = document.querySelector("#cartDrawer");
const cartItems = document.querySelector("#cartItems");
const subtotal = document.querySelector("#subtotal");
const closeCartButton = document.querySelector("#closeCart");
const checkoutButton = document.querySelector("#checkoutButton");
const overlay = document.querySelector("#overlay");
const toast = document.querySelector("#toast");
const newsletterForm = document.querySelector("#newsletterForm");


function money(value) {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
  }).format(Number(value));
}


function getAccessToken() {
  return localStorage.getItem("accessToken");
}


function getCurrentUser() {
  return JSON.parse(
    localStorage.getItem("currentUser") || "null"
  );
}


function clearSession() {
  localStorage.removeItem("accessToken");
  localStorage.removeItem("currentUser");
}


async function apiRequest(path, options = {}) {
  const headers = {
    "Content-Type": "application/json",
    ...(options.headers || {}),
  };

  const token = getAccessToken();

  if (token) {
    headers.Authorization = `Bearer ${token}`;
  }

  let response;

  try {
    response = await fetch(`${API_BASE_URL}${path}`, {
      ...options,
      headers,
    });
  } catch {
    throw new Error("Unable to connect to the backend.");
  }

  const body = await response.json().catch(() => ({}));

  if (response.status === 401) {
    clearSession();
    updateAccountLink();

    cart = {
      items: [],
      item_count: 0,
      subtotal: "0.00",
    };

    renderCart();

    throw new Error("Your login expired. Please log in again.");
  }

  if (!response.ok) {
    throw new Error(
      body.detail || `Request failed with status ${response.status}`
    );
  }

  return body;
}


function updateAccountLink() {
  const user = getCurrentUser();

  if (user) {
    accountLink.textContent = user.full_name;
    accountLink.href = "/checkout.html";
  } else {
    accountLink.textContent = "Log in";
    accountLink.href = "/auth.html";
  }
}


async function loadProducts() {
  try {
    products = await apiRequest("/api/products");
    renderProducts();
  } catch (error) {
    productGrid.innerHTML = `
      <p class="empty">
        Products could not be loaded.
      </p>
    `;

    showToast(error.message);
  }
}


function renderProducts() {
  productGrid.innerHTML = products
    .map((product) => {
      const look = getLook(product);

      return `
        <article class="product-card">
          <div
            class="product-image"
            style="background:${look.background}"
          >
            <img
              src="${look.image}"
              alt="${product.name}"
              loading="lazy"
            />
          </div>

          <div class="product-meta">
            <h3>${product.name}</h3>

            <p>
              ${product.category} · ${money(product.price)}
            </p>

            <button
              type="button"
              aria-label="Add ${product.name} to cart"
              onclick="addToCart(${product.id})"
            >
              +
            </button>
          </div>
        </article>
      `;
    })
    .join("");
}


async function loadCart() {
  if (!getAccessToken()) {
    cart = {
      items: [],
      item_count: 0,
      subtotal: "0.00",
    };

    renderCart();
    return;
  }

  try {
    cart = await apiRequest("/api/cart");
    renderCart();
  } catch (error) {
    showToast(error.message);
  }
}


window.addToCart = async function addToCart(productId) {
  if (!getAccessToken()) {
    window.location.href = "/auth.html";
    return;
  }

  const product = products.find(
    (item) => item.id === productId
  );

  try {
    cart = await apiRequest("/api/cart/items", {
      method: "POST",
      body: JSON.stringify({
        product_id: productId,
        quantity: 1,
      }),
    });

    renderCart();

    if (product) {
      showToast(`${product.name} added to your bag`);
    }
  } catch (error) {
    showToast(error.message);
  }
};


window.changeQuantity = async function changeQuantity(
  productId,
  quantity
) {
  if (quantity < 1) {
    await removeCartItem(productId);
    return;
  }

  try {
    cart = await apiRequest(
      `/api/cart/items/${productId}`,
      {
        method: "PUT",
        body: JSON.stringify({
          quantity,
        }),
      }
    );

    renderCart();
  } catch (error) {
    showToast(error.message);
  }
};


window.removeCartItem = async function removeCartItem(
  productId
) {
  try {
    cart = await apiRequest(
      `/api/cart/items/${productId}`,
      {
        method: "DELETE",
      }
    );

    renderCart();
  } catch (error) {
    showToast(error.message);
  }
};


function renderCart() {
  cartCount.textContent = cart.item_count || 0;

  if (!cart.items.length) {
    cartItems.innerHTML = `
      <p class="empty">
        Your bag is empty.
      </p>
    `;

    subtotal.textContent = money(0);
    return;
  }

  cartItems.innerHTML = cart.items
    .map(
      (item) => {
        const look = getLook({
          id: item.product_id,
          name: item.name || "",
          category: item.category || "",
        });

        return `
        <div class="cart-item">
          <div class="cart-swatch">
            <img src="${look.image}" alt="" />
            <span>${item.quantity}</span>
          </div>

          <div>
            <h4>${item.name}</h4>
            <p>${item.category}</p>

            <div class="cart-controls">
              <button
                type="button"
                aria-label="Decrease quantity"
                onclick="changeQuantity(
                  ${item.product_id},
                  ${item.quantity - 1}
                )"
              >
                −
              </button>

              <span>${item.quantity}</span>

              <button
                type="button"
                aria-label="Increase quantity"
                onclick="changeQuantity(
                  ${item.product_id},
                  ${item.quantity + 1}
                )"
              >
                +
              </button>

              <button
                type="button"
                class="remove-item"
                onclick="removeCartItem(${item.product_id})"
              >
                Remove
              </button>
            </div>
          </div>

          <strong>
            ${money(item.line_total)}
          </strong>
        </div>
      `;
      }
    )
    .join("");

  subtotal.textContent = money(cart.subtotal || 0);
}


function toggleCart(open) {
  cartDrawer.classList.toggle("open", open);
  overlay.classList.toggle("open", open);

  cartDrawer.setAttribute(
    "aria-hidden",
    String(!open)
  );

  overlay.setAttribute(
    "aria-hidden",
    String(!open)
  );
}


function showToast(message) {
  toast.textContent = message;
  toast.classList.add("show");

  window.setTimeout(() => {
    toast.classList.remove("show");
  }, 2200);
}


cartButton.addEventListener("click", async () => {
  if (!getAccessToken()) {
    window.location.href = "/auth.html";
    return;
  }

  await loadCart();
  toggleCart(true);
});


closeCartButton.addEventListener("click", () => {
  toggleCart(false);
});


overlay.addEventListener("click", () => {
  toggleCart(false);
});


checkoutButton.addEventListener("click", () => {
  if (!getAccessToken()) {
    window.location.href = "/auth.html";
    return;
  }

  window.location.href = "/checkout.html";
});


if (newsletterForm) {
  newsletterForm.addEventListener("submit", (event) => {
    event.preventDefault();

    showToast("You’re on the list. Welcome!");
    newsletterForm.reset();
  });
}


const viewAllButton = document.querySelector("#viewAll");

if (viewAllButton) {
  viewAllButton.addEventListener("click", () => {
    window.location.href = "/shop.html";
  });
}


async function initializeStorefront() {
  updateAccountLink();

  await Promise.all([
    loadProducts(),
    loadCart(),
  ]);
}


initializeStorefront();