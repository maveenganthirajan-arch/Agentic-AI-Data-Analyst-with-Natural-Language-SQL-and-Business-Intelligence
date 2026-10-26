"""
SQLAlchemy database models and schema definition for the Enterprise Sales Data Analyst.
"""

from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Float, DateTime, ForeignKey, Index, Text, create_engine
)
from sqlalchemy.orm import declarative_base, relationship, sessionmaker
import os

Base = declarative_base()

class Customer(Base):
    __tablename__ = "customers"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False)
    email = Column(String(120), unique=True, nullable=False)
    segment = Column(String(50), nullable=False)  # Consumer, Corporate, Small Business
    region = Column(String(50), nullable=False)   # North America, Europe, Asia-Pacific, Latin America
    country = Column(String(50), nullable=False)
    signup_date = Column(DateTime, default=datetime.utcnow)

    orders = relationship("Order", back_populates="customer", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Customer {self.name} ({self.segment})>"


class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(150), nullable=False)
    category = Column(String(80), nullable=False)  # Electronics, Apparel, Home & Kitchen, etc.
    brand = Column(String(80), nullable=False)
    unit_cost = Column(Float, nullable=False)
    unit_price = Column(Float, nullable=False)
    stock_quantity = Column(Integer, default=0)

    order_items = relationship("OrderItem", back_populates="product")
    returns = relationship("Return", back_populates="product")

    def __repr__(self):
        return f"<Product {self.name} - ${self.unit_price}>"


class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, autoincrement=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False)
    order_date = Column(DateTime, nullable=False, index=True)
    channel = Column(String(50), nullable=False)  # Online, In-Store, Wholesale
    status = Column(String(50), default="Completed")  # Completed, Returned, Cancelled
    total_amount = Column(Float, nullable=False)
    discount_amount = Column(Float, default=0.0)

    customer = relationship("Customer", back_populates="orders")
    items = relationship("OrderItem", back_populates="order", cascade="all, delete-orphan")
    returns = relationship("Return", back_populates="order", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Order #{self.id} - ${self.total_amount:.2f} on {self.order_date.strftime('%Y-%m-%d')}>"


class OrderItem(Base):
    __tablename__ = "order_items"

    id = Column(Integer, primary_key=True, autoincrement=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False, index=True)
    quantity = Column(Integer, nullable=False)
    unit_price = Column(Float, nullable=False)
    total_revenue = Column(Float, nullable=False)

    order = relationship("Order", back_populates="items")
    product = relationship("Product", back_populates="order_items")

    def __repr__(self):
        return f"<OrderItem #{self.id} - Product {self.product_id} x{self.quantity}>"


class Return(Base):
    __tablename__ = "returns"

    id = Column(Integer, primary_key=True, autoincrement=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    return_date = Column(DateTime, nullable=False)
    refund_amount = Column(Float, nullable=False)
    reason = Column(String(120), default="Defective")

    order = relationship("Order", back_populates="returns")
    product = relationship("Product", back_populates="returns")

    def __repr__(self):
        return f"<Return #{self.id} - ${self.refund_amount:.2f}>"


class MarketingSpend(Base):
    __tablename__ = "marketing_spend"

    id = Column(Integer, primary_key=True, autoincrement=True)
    spend_date = Column(DateTime, nullable=False, index=True)
    channel = Column(String(50), nullable=False)  # Digital Ads, Social Media, Influencer, SEO, Email
    spend_amount = Column(Float, nullable=False)

    def __repr__(self):
        return f"<MarketingSpend {self.channel}: ${self.spend_amount:.2f}>"


# Helper function to get database engine and session
def get_db_path():
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    data_dir = os.path.join(base_dir, "data")
    os.makedirs(data_dir, exist_ok=True)
    return os.path.join(data_dir, "sales.db")


def get_engine(db_path=None):
    if db_path is None:
        db_path = get_db_path()
    return create_engine(f"sqlite:///{db_path}", echo=False)


def get_session(engine=None):
    if engine is None:
        engine = get_engine()
    Session = sessionmaker(bind=engine)
    return Session()


def init_db(engine=None):
    if engine is None:
        engine = get_engine()
    Base.metadata.create_all(engine)
    return engine
