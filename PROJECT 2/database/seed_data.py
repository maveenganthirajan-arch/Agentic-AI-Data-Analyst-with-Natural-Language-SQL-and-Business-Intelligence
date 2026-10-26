"""
Seed database with realistic multi-year sales, customers, products, returns, and marketing spend.
Includes a deliberately modeled scenario where the Electronics category drives the revenue decline in the most recent quarter.
"""

import random
from datetime import datetime, timedelta
import numpy as np
import pandas as pd
from sqlalchemy.orm import Session
from database.schema import (
    Base, Customer, Product, Order, OrderItem, Return, MarketingSpend,
    get_engine, init_db
)

def generate_sample_data(seed: int = 42):
    random.seed(seed)
    np.random.seed(seed)

    # 1. Product catalog
    products_data = [
        # Electronics
        {"name": "Watch Nike Series 7", "category": "Electronics", "brand": "Apple", "cost": 260.00, "price": 399.00, "stock": 100},
        {"name": "iPhone 13 Pro", "category": "Electronics", "brand": "Apple", "cost": 750.00, "price": 999.00, "stock": 45},
        {"name": "iPhone 12 Mini", "category": "Electronics", "brand": "Apple", "cost": 480.00, "price": 699.00, "stock": 110},
        {"name": "MacBook Air M2", "category": "Electronics", "brand": "Apple", "cost": 850.00, "price": 1199.00, "stock": 60},
        {"name": "Sony WH-1000XM5 Headphones", "category": "Electronics", "brand": "Sony", "cost": 240.00, "price": 399.00, "stock": 85},
        {"name": "Dell XPS 15 Laptop", "category": "Electronics", "brand": "Dell", "cost": 1100.00, "price": 1599.00, "stock": 35},
        {"name": "Samsung Galaxy S23", "category": "Electronics", "brand": "Samsung", "cost": 550.00, "price": 799.00, "stock": 90},
        {"name": "iPad Air 5th Gen", "category": "Electronics", "brand": "Apple", "cost": 420.00, "price": 599.00, "stock": 70},

        # Apparel
        {"name": "Nike Dri-FIT Legend T-Shirt", "category": "Apparel", "brand": "Nike", "cost": 14.00, "price": 35.00, "stock": 250},
        {"name": "Adidas Ultraboost Light", "category": "Apparel", "brand": "Adidas", "cost": 95.00, "price": 190.00, "stock": 140},
        {"name": "Levi's 501 Original Fit Jeans", "category": "Apparel", "brand": "Levi's", "cost": 35.00, "price": 79.50, "stock": 180},
        {"name": "Patagonia Better Sweater Fleece", "category": "Apparel", "brand": "Patagonia", "cost": 70.00, "price": 149.00, "stock": 95},
        {"name": "Lululemon Align High-Rise Pant", "category": "Apparel", "brand": "Lululemon", "cost": 42.00, "price": 98.00, "stock": 160},
        {"name": "Nike Club Fleece Hoodie", "category": "Apparel", "brand": "Nike", "cost": 28.00, "price": 65.00, "stock": 210},

        # Home & Kitchen
        {"name": "Nespresso Vertuo Pop+", "category": "Home & Kitchen", "brand": "Nespresso", "cost": 75.00, "price": 129.00, "stock": 120},
        {"name": "Dyson V12 Detect Slim", "category": "Home & Kitchen", "brand": "Dyson", "cost": 420.00, "price": 649.99, "stock": 40},
        {"name": "Instant Pot Duo 7-in-1", "category": "Home & Kitchen", "brand": "Instant Pot", "cost": 48.00, "price": 99.95, "stock": 175},
        {"name": "Le Creuset Enameled Cast Iron Oven", "category": "Home & Kitchen", "brand": "Le Creuset", "cost": 190.00, "price": 380.00, "stock": 50},
        {"name": "Ninja Air Fryer Pro", "category": "Home & Kitchen", "brand": "Ninja", "cost": 55.00, "price": 119.99, "stock": 130},

        # Sports & Fitness
        {"name": "Bowflex SelectTech 552 Dumbbells", "category": "Sports & Fitness", "brand": "Bowflex", "cost": 260.00, "price": 429.00, "stock": 55},
        {"name": "Garmin Forerunner 265", "category": "Sports & Fitness", "brand": "Garmin", "cost": 280.00, "price": 449.99, "stock": 65},
        {"name": "Manduka PRO Yoga Mat", "category": "Sports & Fitness", "brand": "Manduka", "cost": 58.00, "price": 128.00, "stock": 115},
        {"name": "Hydro Flask Wide Mouth 32 oz", "category": "Sports & Fitness", "brand": "Hydro Flask", "cost": 18.00, "price": 44.95, "stock": 280},

        # Beauty & Wellness
        {"name": "Dyson Supersonic Hair Dryer", "category": "Beauty & Wellness", "brand": "Dyson", "cost": 270.00, "price": 429.99, "stock": 45},
        {"name": "Kiehl's Ultra Facial Cream", "category": "Beauty & Wellness", "brand": "Kiehl's", "cost": 16.00, "price": 38.00, "stock": 190},
        {"name": "Theragun Prime Percussion Massager", "category": "Beauty & Wellness", "brand": "Therabody", "cost": 180.00, "price": 299.00, "stock": 60},
    ]

    # 2. Customers
    first_names = ["Alex", "Jordan", "Taylor", "Morgan", "Sam", "Chris", "Pat", "Riley", "Casey", "Avery",
                   "Cameron", "Logan", "Dakota", "Reese", "Skyler", "Jesse", "Finley", "Kendall", "Harper", "Rowan"]
    last_names = ["Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis", "Rodriguez", "Martinez",
                  "Hernandez", "Lopez", "Gonzalez", "Wilson", "Anderson", "Thomas", "Taylor", "Moore", "Jackson", "Martin"]
    
    segments = ["Consumer", "Corporate", "Small Business"]
    segment_weights = [0.65, 0.20, 0.15]

    regions = ["North America", "Europe", "Asia-Pacific", "Latin America"]
    region_countries = {
        "North America": ["United States", "Canada"],
        "Europe": ["United Kingdom", "Germany", "France", "Netherlands"],
        "Asia-Pacific": ["Japan", "Singapore", "Australia", "India"],
        "Latin America": ["Brazil", "Mexico", "Chile"]
    }

    customers_data = []
    used_emails = set()
    num_customers = 150

    start_date = datetime(2024, 1, 1)
    end_date = datetime(2025, 12, 31)
    total_days = (end_date - start_date).days

    for i in range(1, num_customers + 1):
        fn = random.choice(first_names)
        ln = random.choice(last_names)
        full_name = f"{fn} {ln}"
        base_email = f"{fn.lower()}.{ln.lower()}{i}@example.com"
        segment = np.random.choice(segments, p=segment_weights)
        region = random.choice(regions)
        country = random.choice(region_countries[region])
        signup_offset = random.randint(0, int(total_days * 0.75))
        signup = start_date + timedelta(days=signup_offset)

        customers_data.append({
            "name": full_name,
            "email": base_email,
            "segment": segment,
            "region": region,
            "country": country,
            "signup_date": signup
        })

    return products_data, customers_data


def seed_database(engine=None, reset: bool = True):
    if engine is None:
        engine = get_engine()

    if reset:
        Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)

    products_data, customers_data = generate_sample_data(seed=42)

    session = Session(engine)
    try:
        # Insert Products
        db_products = []
        for p in products_data:
            prod = Product(
                name=p["name"],
                category=p["category"],
                brand=p["brand"],
                unit_cost=p["cost"],
                unit_price=p["price"],
                stock_quantity=p["stock"]
            )
            session.add(prod)
            db_products.append(prod)
        session.flush()

        # Insert Customers
        db_customers = []
        for c in customers_data:
            cust = Customer(
                name=c["name"],
                email=c["email"],
                segment=c["segment"],
                region=c["region"],
                country=c["country"],
                signup_date=c["signup_date"]
            )
            session.add(cust)
            db_customers.append(cust)
        session.flush()

        # 3. Create realistic Orders spanning 8 quarters: 2024-Q1 through 2025-Q4
        # We model the quarterly revenue trajectory:
        # 2024-Q1: Base
        # 2024-Q2: +8%
        # 2024-Q3: +10%
        # 2024-Q4: +25% (Holiday peak)
        # 2025-Q1: -12% (Post-holiday dip)
        # 2025-Q2: +15% (Summer rebound)
        # 2025-Q3: High ($385k overall, with Electronics ~$195k)
        # 2025-Q4 (Last Quarter): Notable decline overall (~$310k), where Electronics drops by ~$85k (due to supply disruption)
        # while Apparel (+10k), Home & Kitchen (+5k), Sports (+-0k) remain stable!
        
        quarter_configs = [
            # (year, quarter, start_month, end_month, order_count, electronics_mult)
            (2024, 1, 1, 3, 220, 1.0),
            (2024, 2, 4, 6, 245, 1.05),
            (2024, 3, 7, 9, 270, 1.1),
            (2024, 4, 10, 12, 350, 1.3),
            (2025, 1, 1, 3, 260, 1.1),
            (2025, 2, 4, 6, 290, 1.15),
            (2025, 3, 7, 9, 340, 1.35), # Previous quarter (2025-Q3)
            (2025, 4, 10, 12, 280, 0.65), # Last quarter (2025-Q4) -> Electronics drops sharply!
        ]

        channels = ["Online", "In-Store", "Wholesale"]
        channel_weights = [0.60, 0.28, 0.12]
        return_reasons = ["Defective", "Customer Mind Change", "Wrong Size/Color", "Arrived Damaged"]

        # Category maps for fast lookup
        electronics_products = [p for p in db_products if p.category == "Electronics"]
        non_electronics_products = [p for p in db_products if p.category != "Electronics"]

        total_orders = 0
        total_items = 0
        total_returns = 0

        for year, quarter, sm, em, order_count, elec_mult in quarter_configs:
            for _ in range(order_count):
                # Pick customer
                cust = random.choice(db_customers)
                
                # Order date within quarter months
                month = random.randint(sm, em)
                day = random.randint(1, 28)
                hour = random.randint(8, 22)
                minute = random.randint(0, 59)
                order_dt = datetime(year, month, day, hour, minute)

                channel = np.random.choice(channels, p=channel_weights)
                status = "Completed"

                # Items per order (1 to 4)
                num_items = random.choices([1, 2, 3, 4], weights=[0.55, 0.28, 0.12, 0.05])[0]
                
                order_total = 0.0
                order_item_objs = []

                # Select products taking into account elec_mult
                # If elec_mult is low, probability of selecting electronics is reduced
                elec_prob = 0.40 * elec_mult
                non_elec_prob = max(0.1, 1.0 - elec_prob)
                p_dist = [elec_prob, non_elec_prob]
                p_dist = [p / sum(p_dist) for p in p_dist]

                chosen_products = set()
                for _ in range(num_items):
                    pick_elec = np.random.choice([True, False], p=p_dist)
                    pool = electronics_products if pick_elec else non_electronics_products
                    prod = random.choice(pool)
                    if prod.id in chosen_products:
                        continue
                    chosen_products.add(prod.id)

                    qty = 1 if prod.category == "Electronics" else random.choices([1, 2, 3], weights=[0.7, 0.2, 0.1])[0]
                    item_rev = round(prod.unit_price * qty, 2)
                    order_total += item_rev

                    order_item_objs.append((prod, qty, item_rev))

                discount = 0.0
                if cust.segment == "Corporate" and order_total > 500:
                    discount = round(order_total * 0.10, 2)
                elif random.random() < 0.15:
                    discount = round(order_total * 0.05, 2)

                final_total = max(0.0, round(order_total - discount, 2))

                order = Order(
                    customer_id=cust.id,
                    order_date=order_dt,
                    channel=channel,
                    status=status,
                    total_amount=final_total,
                    discount_amount=discount
                )
                session.add(order)
                session.flush()
                total_orders += 1

                for prod, qty, item_rev in order_item_objs:
                    oi = OrderItem(
                        order_id=order.id,
                        product_id=prod.id,
                        quantity=qty,
                        unit_price=prod.unit_price,
                        total_revenue=item_rev
                    )
                    session.add(oi)
                    total_items += 1

                    # 3.5% chance of return
                    if random.random() < 0.035:
                        ret_dt = order_dt + timedelta(days=random.randint(2, 14))
                        ret = Return(
                            order_id=order.id,
                            product_id=prod.id,
                            return_date=ret_dt,
                            refund_amount=item_rev,
                            reason=random.choice(return_reasons)
                        )
                        session.add(ret)
                        total_returns += 1

        # 4. Generate marketing spend data (monthly per channel)
        marketing_channels = ["Digital Ads", "Social Media", "Influencer", "SEO", "Email Marketing"]
        channel_monthly_budgets = {
            "Digital Ads": (4000, 7500),
            "Social Media": (2500, 5000),
            "Influencer": (1500, 4000),
            "SEO": (1200, 2500),
            "Email Marketing": (800, 1800)
        }

        total_marketing_records = 0
        for y in [2024, 2025]:
            for m in range(1, 13):
                for ch in marketing_channels:
                    low, high = channel_monthly_budgets[ch]
                    # Holiday boost in Q4
                    if m in [11, 12]:
                        low = int(low * 1.5)
                        high = int(high * 1.5)
                    spend = round(random.uniform(low, high), 2)
                    ms = MarketingSpend(
                        spend_date=datetime(y, m, 1),
                        channel=ch,
                        spend_amount=spend
                    )
                    session.add(ms)
                    total_marketing_records += 1

        session.commit()
        print(f"Database successfully seeded:")
        print(f" - {len(db_customers)} Customers")
        print(f" - {len(db_products)} Products across 5 Categories")
        print(f" - {total_orders} Orders")
        print(f" - {total_items} Order Line Items")
        print(f" - {total_returns} Returns")
        print(f" - {total_marketing_records} Marketing Spend Records")

    except Exception as e:
        session.rollback()
        raise e
    finally:
        session.close()

if __name__ == "__main__":
    seed_database()
