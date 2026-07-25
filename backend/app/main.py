from decimal import Decimal
from typing import Annotated
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field


app = FastAPI(
    title="Ecommerce API",
    version="1.0.0",
    description="Backend API for the GKE ecommerce application",
)

# This is open for initial testing.
# Replace "*" with your real frontend domain before production.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


class Product(BaseModel):
    id: int
    name: str
    description: str
    price: Decimal
    image_url: str
    category: str
    inventory: int


class CartItem(BaseModel):
    product_id: int
    quantity: Annotated[int, Field(ge=1, le=20)]


class CartRequest(BaseModel):
    items: list[CartItem]


class CartLine(BaseModel):
    product_id: int
    name: str
    quantity: int
    unit_price: Decimal
    line_total: Decimal


class CartSummary(BaseModel):
    items: list[CartLine]
    subtotal: Decimal
    item_count: int


class Customer(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    email: str = Field(min_length=5, max_length=200)


class CreateOrderRequest(BaseModel):
    customer: Customer
    items: list[CartItem]


class OrderResponse(BaseModel):
    order_id: str
    status: str
    customer: Customer
    subtotal: Decimal
    item_count: int


PRODUCTS: list[Product] = [
    Product(
        id=1,
        name="Classic Everyday Tote",
        description="A lightweight tote designed for work and everyday use.",
        price=Decimal("48.00"),
        image_url="https://images.unsplash.com/photo-1553062407-98eeb64c6a62",
        category="Bags",
        inventory=25,
    ),
    Product(
        id=2,
        name="Minimal Leather Wallet",
        description="Compact wallet with a clean, understated design.",
        price=Decimal("34.00"),
        image_url="https://images.unsplash.com/photo-1627123424574-724758594e93",
        category="Accessories",
        inventory=40,
    ),
    Product(
        id=3,
        name="Modern Desk Lamp",
        description="A warm LED desk lamp for focused workspaces.",
        price=Decimal("65.00"),
        image_url="https://images.unsplash.com/photo-1507473885765-e6ed057f782c",
        category="Home",
        inventory=18,
    ),
    Product(
        id=4,
        name="Essential Sneakers",
        description="Comfortable low-profile sneakers for daily wear.",
        price=Decimal("89.00"),
        image_url="https://images.unsplash.com/photo-1542291026-7eec264c27ff",
        category="Shoes",
        inventory=30,
    ),
]


def find_product(product_id: int) -> Product:
    product = next(
        (item for item in PRODUCTS if item.id == product_id),
        None,
    )

    if product is None:
        raise HTTPException(status_code=404, detail="Product not found")

    return product


def calculate_cart(items: list[CartItem]) -> CartSummary:
    if not items:
        raise HTTPException(
            status_code=400,
            detail="The cart must contain at least one item",
        )

    lines: list[CartLine] = []
    subtotal = Decimal("0.00")
    item_count = 0

    for item in items:
        product = find_product(item.product_id)

        if item.quantity > product.inventory:
            raise HTTPException(
                status_code=400,
                detail=f"Only {product.inventory} units of {product.name} are available",
            )

        line_total = product.price * item.quantity
        subtotal += line_total
        item_count += item.quantity

        lines.append(
            CartLine(
                product_id=product.id,
                name=product.name,
                quantity=item.quantity,
                unit_price=product.price,
                line_total=line_total,
            )
        )

    return CartSummary(
        items=lines,
        subtotal=subtotal,
        item_count=item_count,
    )


@app.get("/")
def root() -> dict[str, str]:
    return {
        "message": "Ecommerce backend is running",
        "documentation": "/docs",
    }


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "healthy"}


@app.get("/api/products", response_model=list[Product])
def list_products(
    category: str | None = None,
    search: Annotated[str | None, Query(max_length=100)] = None,
) -> list[Product]:
    results = PRODUCTS

    if category:
        results = [
            product
            for product in results
            if product.category.lower() == category.lower()
        ]

    if search:
        query = search.lower()
        results = [
            product
            for product in results
            if query in product.name.lower()
            or query in product.description.lower()
        ]

    return results


@app.get("/api/products/{product_id}", response_model=Product)
def get_product(product_id: int) -> Product:
    return find_product(product_id)


@app.post("/api/cart/summary", response_model=CartSummary)
def cart_summary(cart: CartRequest) -> CartSummary:
    return calculate_cart(cart.items)


@app.post("/api/orders", response_model=OrderResponse, status_code=201)
def create_order(order: CreateOrderRequest) -> OrderResponse:
    cart = calculate_cart(order.items)

    return OrderResponse(
        order_id=str(uuid4()),
        status="created",
        customer=order.customer,
        subtotal=cart.subtotal,
        item_count=cart.item_count,
    )