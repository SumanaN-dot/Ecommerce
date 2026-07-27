import os
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Annotated
import jwt
from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt.exceptions import InvalidTokenError
from pydantic import BaseModel, ConfigDict, EmailStr, Field
from pwdlib import PasswordHash
from sqlalchemy import DECIMAL, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, create_engine, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, sessionmaker
DATABASE_URL = os.getenv('DATABASE_URL', 'mysql+pymysql://ecommerce:ecommercepassword@mysql:3306/ecommerce')
JWT_SECRET = os.getenv('JWT_SECRET', 'replace-this-development-secret')
engine = create_engine(DATABASE_URL, pool_pre_ping=True, pool_recycle=1800)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
JWT_SECRET = os.getenv('JWT_SECRET', 'replace-this-development-secret')
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_MINUTES = 60
password_hash = PasswordHash.recommended()
bearer = HTTPBearer()

class Base(DeclarativeBase):
    pass

class User(Base):
    __tablename__ = 'users'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(200), unique=True, index=True)
    full_name: Mapped[str] = mapped_column(String(100))
    password_hash: Mapped[str] = mapped_column(String(255))

class Product(Base):
    __tablename__ = 'products'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(150))
    description: Mapped[str] = mapped_column(Text)
    price: Mapped[Decimal] = mapped_column(DECIMAL(10, 2))
    image_url: Mapped[str] = mapped_column(String(500), default='')
    category: Mapped[str] = mapped_column(String(100))
    inventory: Mapped[int] = mapped_column(Integer, default=0)

class CartItem(Base):
    __tablename__ = 'cart_items'
    __table_args__ = (UniqueConstraint('user_id', 'product_id'),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id', ondelete='CASCADE'), index=True)
    product_id: Mapped[int] = mapped_column(ForeignKey('products.id', ondelete='CASCADE'))
    quantity: Mapped[int] = mapped_column(Integer)

class Order(Base):
    __tablename__ = 'orders'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id'), index=True)
    customer_name: Mapped[str] = mapped_column(String(100))
    customer_email: Mapped[str] = mapped_column(String(200))
    address_line1: Mapped[str] = mapped_column(String(200))
    address_line2: Mapped[str | None] = mapped_column(String(200), nullable=True)
    city: Mapped[str] = mapped_column(String(100))
    state: Mapped[str] = mapped_column(String(100))
    postal_code: Mapped[str] = mapped_column(String(30))
    country: Mapped[str] = mapped_column(String(100))
    status: Mapped[str] = mapped_column(String(50), default='placed')
    subtotal: Mapped[Decimal] = mapped_column(DECIMAL(10, 2))
    shipping: Mapped[Decimal] = mapped_column(DECIMAL(10, 2))
    tax: Mapped[Decimal] = mapped_column(DECIMAL(10, 2))
    total: Mapped[Decimal] = mapped_column(DECIMAL(10, 2))
    item_count: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

class OrderItem(Base):
    __tablename__ = 'order_items'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey('orders.id', ondelete='CASCADE'))
    product_id: Mapped[int] = mapped_column(Integer)
    product_name: Mapped[str] = mapped_column(String(150))
    quantity: Mapped[int] = mapped_column(Integer)
    unit_price: Mapped[Decimal] = mapped_column(DECIMAL(10, 2))
    line_total: Mapped[Decimal] = mapped_column(DECIMAL(10, 2))

class Register(BaseModel):
    full_name: str = Field(min_length=2, max_length=100)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)

class Login(BaseModel):
    email: EmailStr
    password: str

class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    email: str
    full_name: str

class TokenOut(BaseModel):
    access_token: str
    token_type: str = 'bearer'
    user: UserOut

class ProductOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    description: str
    price: Decimal
    image_url: str
    category: str
    inventory: int

class AddCart(BaseModel):
    product_id: int
    quantity: Annotated[int, Field(ge=1, le=20)]

class UpdateCart(BaseModel):
    quantity: Annotated[int, Field(ge=1, le=20)]

class CartLine(BaseModel):
    product_id: int
    name: str
    category: str
    quantity: int
    unit_price: Decimal
    line_total: Decimal

class CartOut(BaseModel):
    user_id: int
    items: list[CartLine]
    item_count: int
    subtotal: Decimal

class Checkout(BaseModel):
    customer_name: str
    customer_email: EmailStr
    address_line1: str
    address_line2: str | None = None
    city: str
    state: str
    postal_code: str
    country: str

class CheckoutOut(BaseModel):
    order_id: int
    status: str
    subtotal: Decimal
    shipping: Decimal
    tax: Decimal
    total: Decimal
    item_count: int

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def token_for(u):
    now = datetime.now(timezone.utc)
    return jwt.encode({'sub': str(u.id), 'iat': now, 'exp': now + timedelta(minutes=60)}, JWT_SECRET, algorithm='HS256')

def current(c: HTTPAuthorizationCredentials=Depends(bearer), db: Session=Depends(get_db)):
    try:
        uid = int(jwt.decode(c.credentials, JWT_SECRET, algorithms=['HS256'])['sub'])
    except (InvalidTokenError, KeyError, ValueError):
        raise HTTPException(401, 'Invalid or expired login')
    u = db.get(User, uid)
    if not u:
        raise HTTPException(401, 'Invalid login')
    return u

def seed(db):
    if db.scalar(select(Product.id).limit(1)) is None:
        db.add_all([Product(name='Stoneware Mug', description='Hand-finished stoneware mug', price=Decimal('28'), image_url='', category='Tableware', inventory=30), Product(name='Moss Table Lamp', description='Soft ambient lighting', price=Decimal('119'), image_url='', category='Lighting', inventory=12), Product(name='Olive Carafe', description='Sculptural glass carafe', price=Decimal('44'), image_url='', category='Kitchen', inventory=20), Product(name='Canvas Market Tote', description='Durable everyday tote', price=Decimal('36'), image_url='', category='Everyday carry', inventory=25)])
    for e, n, p in [('user1@example.com', 'Test User One', 'UserOne123!'), ('user2@example.com', 'Test User Two', 'UserTwo123!')]:
        if db.scalar(select(User).where(User.email == e)) is None:
            db.add(User(email=e, full_name=n, password_hash=password_hash.hash(p)))
    db.commit()

@asynccontextmanager
async def lifespan(app):
    Base.metadata.create_all(engine)
    db = SessionLocal()
    seed(db)
    db.close()
    yield
app = FastAPI(lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=['*'], allow_methods=['*'], allow_headers=['*'])

def cart(uid, db):
    rows = db.execute(select(CartItem, Product).join(Product, Product.id == CartItem.product_id).where(CartItem.user_id == uid)).all()
    items = []
    sub = Decimal('0')
    count = 0
    for ci, p in rows:
        lt = p.price * ci.quantity
        items.append(CartLine(product_id=p.id, name=p.name, category=p.category, quantity=ci.quantity, unit_price=p.price, line_total=lt))
        sub += lt
        count += ci.quantity
    return CartOut(user_id=uid, items=items, item_count=count, subtotal=sub)

@app.get('/health')
def health(db: Session=Depends(get_db)):
    db.execute(select(1))
    return {'status': 'healthy', 'database': 'mysql'}

@app.post('/api/auth/register', response_model=TokenOut, status_code=201)
def register(r: Register, db: Session=Depends(get_db)):
    if db.scalar(select(User).where(User.email == r.email.lower())):
        raise HTTPException(409, 'Email is already registered')
    u = User(email=r.email.lower(), full_name=r.full_name, password_hash=password_hash.hash(r.password))
    db.add(u)
    db.commit()
    db.refresh(u)
    return TokenOut(access_token=token_for(u), user=UserOut.model_validate(u))

@app.post('/api/auth/login', response_model=TokenOut)
def login(r: Login, db: Session=Depends(get_db)):
    u = db.scalar(select(User).where(User.email == r.email.lower()))
    if not u or not password_hash.verify(r.password, u.password_hash):
        raise HTTPException(401, 'Incorrect email or password')
    return TokenOut(access_token=token_for(u), user=UserOut.model_validate(u))

@app.get('/api/products', response_model=list[ProductOut])
def products(db: Session=Depends(get_db)):
    return list(db.scalars(select(Product).order_by(Product.id)).all())

@app.get('/api/cart', response_model=CartOut)
def get_cart(u: User=Depends(current), db: Session=Depends(get_db)):
    return cart(u.id, db)

@app.post('/api/cart/items', response_model=CartOut)
def add(r: AddCart, u: User=Depends(current), db: Session=Depends(get_db)):
    p = db.get(Product, r.product_id)
    if not p:
        raise HTTPException(404, 'Product not found')
    i = db.scalar(select(CartItem).where(CartItem.user_id == u.id, CartItem.product_id == r.product_id))
    q = r.quantity + (i.quantity if i else 0)
    if q > p.inventory:
        raise HTTPException(400, 'Not enough inventory')
    if i:
        i.quantity = q
    else:
        db.add(CartItem(user_id=u.id, product_id=p.id, quantity=r.quantity))
    db.commit()
    return cart(u.id, db)

@app.put('/api/cart/items/{pid}', response_model=CartOut)
def update(pid: int, r: UpdateCart, u: User=Depends(current), db: Session=Depends(get_db)):
    p = db.get(Product, pid)
    i = db.scalar(select(CartItem).where(CartItem.user_id == u.id, CartItem.product_id == pid))
    if not p or not i:
        raise HTTPException(404, 'Cart item not found')
    if r.quantity > p.inventory:
        raise HTTPException(400, 'Not enough inventory')
    i.quantity = r.quantity
    db.commit()
    return cart(u.id, db)

@app.delete('/api/cart/items/{pid}', response_model=CartOut)
def remove(pid: int, u: User=Depends(current), db: Session=Depends(get_db)):
    i = db.scalar(select(CartItem).where(CartItem.user_id == u.id, CartItem.product_id == pid))
    if not i:
        raise HTTPException(404, 'Cart item not found')
    db.delete(i)
    db.commit()
    return cart(u.id, db)

@app.post('/api/checkout', response_model=CheckoutOut, status_code=201)
def checkout(r: Checkout, u: User=Depends(current), db: Session=Depends(get_db)):
    rows = db.execute(select(CartItem, Product).join(Product, Product.id == CartItem.product_id).where(CartItem.user_id == u.id).with_for_update()).all()
    if not rows:
        raise HTTPException(400, 'Your cart is empty')
    sub = sum((p.price * ci.quantity for ci, p in rows), Decimal('0'))
    count = sum((ci.quantity for ci, p in rows))
    shipping = Decimal('0') if sub >= 75 else Decimal('7.99')
    tax = (sub * Decimal('0.07')).quantize(Decimal('0.01'))
    total = sub + shipping + tax
    o = Order(user_id=u.id, customer_name=r.customer_name, customer_email=str(r.customer_email), address_line1=r.address_line1, address_line2=r.address_line2, city=r.city, state=r.state, postal_code=r.postal_code, country=r.country, status='placed', subtotal=sub, shipping=shipping, tax=tax, total=total, item_count=count, created_at=datetime.now(timezone.utc))
    db.add(o)
    db.flush()
    for ci, p in rows:
        db.add(OrderItem(order_id=o.id, product_id=p.id, product_name=p.name, quantity=ci.quantity, unit_price=p.price, line_total=p.price * ci.quantity))
        p.inventory -= ci.quantity
        db.delete(ci)
    db.commit()
    return CheckoutOut(order_id=o.id, status=o.status, subtotal=sub, shipping=shipping, tax=tax, total=total, item_count=count)