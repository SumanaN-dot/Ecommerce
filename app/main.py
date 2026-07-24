import os
from decimal import Decimal
from typing import Generator

from fastapi import Depends, FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from sqlalchemy import Integer, Numeric, String, create_engine, select
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, sessionmaker

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./shop.db")
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(DATABASE_URL, pool_pre_ping=True, connect_args=connect_args)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

class Base(DeclarativeBase):
    pass

class Product(Base):
    __tablename__ = "products"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    description: Mapped[str] = mapped_column(String(500), default="")
    price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    inventory: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

class Order(Base):
    __tablename__ = "orders"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    customer_email: Mapped[str] = mapped_column(String(255), nullable=False)
    product_id: Mapped[int] = mapped_column(Integer, nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    total: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="created")

class ProductOut(BaseModel):
    id: int
    name: str
    description: str
    price: Decimal
    inventory: int
    model_config = {"from_attributes": True}

class OrderCreate(BaseModel):
    customer_email: str = Field(min_length=3, max_length=255)
    product_id: int
    quantity: int = Field(ge=1, le=20)

class OrderOut(BaseModel):
    id: int
    customer_email: str
    product_id: int
    quantity: int
    total: Decimal
    status: str
    model_config = {"from_attributes": True}

app = FastAPI(title="GKE Store", version="1.0.0")

def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.on_event("startup")
def startup() -> None:
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        if not db.scalar(select(Product.id).limit(1)):
            db.add_all([
                Product(name="Cloud Hoodie", description="Soft developer hoodie", price=Decimal("59.00"), inventory=30),
                Product(name="Kubernetes Mug", description="A mug for resilient mornings", price=Decimal("18.50"), inventory=75),
                Product(name="GKE Sticker Pack", description="Five weatherproof stickers", price=Decimal("8.00"), inventory=200),
            ])
            db.commit()

@app.get("/", include_in_schema=False)
def storefront():
    return FileResponse("app/static/index.html")

@app.get("/healthz")
def healthz():
    return {"status": "ok"}

@app.get("/readyz")
def readyz(db: Session = Depends(get_db)):
    db.execute(select(1))
    return {"status": "ready"}

@app.get("/api/products", response_model=list[ProductOut])
def list_products(db: Session = Depends(get_db)):
    return list(db.scalars(select(Product).order_by(Product.id)))

@app.post("/api/orders", response_model=OrderOut, status_code=201)
def create_order(payload: OrderCreate, db: Session = Depends(get_db)):
    product = db.get(Product, payload.product_id)
    if not product:
        raise HTTPException(404, "Product not found")
    if product.inventory < payload.quantity:
        raise HTTPException(409, "Insufficient inventory")

    product.inventory -= payload.quantity
    order = Order(
        customer_email=payload.customer_email,
        product_id=product.id,
        quantity=payload.quantity,
        total=product.price * payload.quantity,
        status="created",
    )
    db.add(order)
    db.commit()
    db.refresh(order)
    return order
