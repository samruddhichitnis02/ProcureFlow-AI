import random
import uuid
from datetime import datetime, timedelta
from typing import List, Dict, Any

CITIES_STATES = [
    ("sao paulo", "SP"),
    ("rio de janeiro", "RJ"),
    ("belo horizonte", "MG"),
    ("curitiba", "PR"),
    ("porto alegre", "RS"),
    ("salvador", "BA"),
    ("brasilia", "DF"),
    ("fortaleza", "CE"),
    ("recife", "PE"),
    ("campinas", "SP"),
]

CATEGORIES = [
    "cama_mesa_banho",
    "beleza_saude",
    "esporte_lazer",
    "moveis_decoracao",
    "informatica_acessorios",
    "utilidades_domesticas",
    "relogios_presentes",
    "telefonia",
    "automotivo",
    "brinquedos",
]

PAYMENT_TYPES = ["credit_card", "boleto", "voucher", "debit_card"]

REVIEW_TEMPLATES_POSITIVE = [
    ("Produto excelente", "Chegou antes do prazo estabelecido. Muito satisfeito com a compra e qualidade."),
    ("Muito bom", "Entrega super rápida e o produto corresponde exatamente ao anúncio. Recomendo o vendedor!"),
    ("Otimo atendimento", "Tudo em perfeita ordem, muito bem embalado. Excelente fornecedor."),
    ("Recomendo", "Compra segura e rápida. Produto original de excelente acabamento."),
]

REVIEW_TEMPLATES_NEGATIVE_DELAY = [
    ("Atraso absurdo na entrega", "Meu pedido era para ter chegado há mais de duas semanas e até agora nenhuma atualização da transportadora."),
    ("Nao recebi o produto", "O prazo de entrega expirou faz dias. Vendedor não responde às mensagens sobre o rastreamento."),
    ("Pessima logistica", "A mercadoria ficou retida no centro de distribuição do transportador e o suporte não resolve."),
    ("Demora inaceitavel", "Comprei para um presente de aniversário e não chegou a tempo. Quero cancelamento e reembolso imediato."),
]

REVIEW_TEMPLATES_NEGATIVE_PRODUCT = [
    ("Produto danificado", "A caixa veio amassada e a peça quebrada. Falta de cuidado na embalagem pelo vendedor."),
    ("Veio modelo errado", "Recebi um item diferente do que pedi no catálogo. Exijo a troca ou estorno do pagamento."),
    ("Qualidade muito inferior", "Material frágil, não condiz com as fotos publicadas pelo fornecedor."),
]

REVIEW_TEMPLATES_PAYMENT_ISSUE = [
    ("Problema na cobranca", "Houve cobrança duplicada no meu cartão de crédito e o pedido ainda consta pendente."),
    ("Divergencia de valor", "O valor cobrado foi superior ao total do carrinho com o frete acordado."),
]


class OlistDataGenerator:
    """
    Generates realistic Olist-conforming relational dataset.
    Simulates delayed orders, supplier SLA variance, and payment discrepancies.
    """

    def __init__(self, seed: int = 42):
        self.random = random.Random(seed)

    def generate_dataset(
        self,
        num_customers: int = 500,
        num_sellers: int = 80,
        num_products: int = 200,
        num_orders: int = 1500,
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Generate connected entities across customers, sellers, products, orders, items, payments, and reviews.
        """
        # 1. Customers
        customers = []
        for i in range(num_customers):
            city, state = self.random.choice(CITIES_STATES)
            c_id = f"cust_{i+1:05d}"
            u_id = f"user_{self.random.randint(1, int(num_customers * 0.8)):05d}"
            customers.append({
                "customer_id": c_id,
                "customer_unique_id": u_id,
                "customer_zip_code_prefix": self.random.randint(10000, 99999),
                "customer_city": city,
                "customer_state": state,
            })

        # 2. Sellers
        sellers = []
        for j in range(num_sellers):
            city, state = self.random.choice(CITIES_STATES)
            s_id = f"seller_{j+1:04d}"
            # Some sellers have lower SLA inherently
            base_sla = self.random.choice([0.98, 0.95, 0.88, 0.72, 0.65])
            sellers.append({
                "seller_id": s_id,
                "seller_zip_code_prefix": self.random.randint(10000, 99999),
                "seller_city": city,
                "seller_state": state,
                "sla_score": base_sla,
                "total_orders": 0,
                "late_orders_count": 0,
            })

        # 3. Products
        products = []
        for k in range(num_products):
            p_id = f"prod_{k+1:04d}"
            cat = self.random.choice(CATEGORIES)
            products.append({
                "product_id": p_id,
                "product_category_name": cat,
                "product_name_lenght": self.random.randint(20, 60),
                "product_description_lenght": self.random.randint(100, 1500),
                "product_photos_qty": self.random.randint(1, 6),
                "product_weight_g": round(self.random.uniform(200.0, 5000.0), 2),
                "product_length_cm": round(self.random.uniform(15.0, 80.0), 1),
                "product_height_cm": round(self.random.uniform(5.0, 50.0), 1),
                "product_width_cm": round(self.random.uniform(10.0, 60.0), 1),
            })

        # 4. Orders, Items, Payments, Reviews
        orders = []
        order_items = []
        order_payments = []
        order_reviews = []

        start_date = datetime(2023, 1, 1)

        seller_stats = {s["seller_id"]: {"total": 0, "late": 0} for s in sellers}

        for idx in range(num_orders):
            order_id = f"ord_{idx+1:06d}"
            customer = self.random.choice(customers)
            purchase_dt = start_date + timedelta(
                days=self.random.randint(0, 300),
                hours=self.random.randint(8, 20),
                minutes=self.random.randint(0, 59),
            )
            approved_dt = purchase_dt + timedelta(hours=self.random.randint(1, 24))

            # Introduce realistic scenarios:
            # 15% delayed orders, 5% payment issues, 5% canceled/processing, 75% normal delivered
            scenario_roll = self.random.random()
            is_delayed = False
            delay_days = 0.0
            has_payment_issue = False

            if scenario_roll < 0.15:
                # Late Delivery Scenario
                is_delayed = True
                order_status = "delivered"
                delay_days = round(self.random.uniform(3.0, 18.0), 1)
                est_days = self.random.randint(8, 15)
                est_delivery_dt = purchase_dt + timedelta(days=est_days)
                carrier_dt = purchase_dt + timedelta(days=self.random.randint(4, 9))
                actual_delivery_dt = est_delivery_dt + timedelta(days=int(delay_days), hours=int((delay_days % 1) * 24))
            elif scenario_roll < 0.20:
                # Payment Discrepancy Scenario
                has_payment_issue = True
                order_status = self.random.choice(["processing", "delivered", "canceled"])
                est_days = self.random.randint(10, 18)
                est_delivery_dt = purchase_dt + timedelta(days=est_days)
                carrier_dt = purchase_dt + timedelta(days=3)
                actual_delivery_dt = est_delivery_dt - timedelta(days=2) if order_status == "delivered" else None
            elif scenario_roll < 0.25:
                # In Transit / Processing (Unfulfilled)
                order_status = "shipped"
                est_days = self.random.randint(10, 20)
                est_delivery_dt = purchase_dt + timedelta(days=est_days)
                carrier_dt = purchase_dt + timedelta(days=2)
                actual_delivery_dt = None
            else:
                # Normal on-time delivery
                order_status = "delivered"
                est_days = self.random.randint(10, 22)
                est_delivery_dt = purchase_dt + timedelta(days=est_days)
                carrier_dt = purchase_dt + timedelta(days=self.random.randint(1, 4))
                actual_delivery_dt = est_delivery_dt - timedelta(days=self.random.randint(1, 7))

            orders.append({
                "order_id": order_id,
                "customer_id": customer["customer_id"],
                "order_status": order_status,
                "order_purchase_timestamp": purchase_dt,
                "order_approved_at": approved_dt,
                "order_delivered_carrier_date": carrier_dt,
                "order_delivered_customer_date": actual_delivery_dt,
                "order_estimated_delivery_date": est_delivery_dt,
                "delay_days": delay_days,
                "is_delayed": is_delayed,
                "has_payment_issue": has_payment_issue,
            })

            # Items for this order
            num_items = self.random.choices([1, 2, 3, 4], weights=[0.75, 0.15, 0.07, 0.03])[0]
            total_items_price = 0.0
            total_freight = 0.0

            for itm_idx in range(num_items):
                prod = self.random.choice(products)
                seller = self.random.choice(sellers)
                price = round(self.random.uniform(19.90, 480.00), 2)
                freight = round(self.random.uniform(8.50, 45.00), 2)
                total_items_price += price
                total_freight += freight

                shipping_limit = purchase_dt + timedelta(days=self.random.randint(3, 7))
                order_items.append({
                    "order_id": order_id,
                    "order_item_id": itm_idx + 1,
                    "product_id": prod["product_id"],
                    "seller_id": seller["seller_id"],
                    "shipping_limit_date": shipping_limit,
                    "price": price,
                    "freight_value": freight,
                })

                seller_stats[seller["seller_id"]]["total"] += 1
                if is_delayed:
                    seller_stats[seller["seller_id"]]["late"] += 1

            # Payments for this order
            expected_total = round(total_items_price + total_freight, 2)
            if has_payment_issue:
                # Underpaid, duplicated or zeroed
                paid_amount = round(expected_total * self.random.choice([0.5, 0.8, 1.25, 0.0]), 2)
            else:
                paid_amount = expected_total

            order_payments.append({
                "order_id": order_id,
                "payment_sequential": 1,
                "payment_type": self.random.choice(PAYMENT_TYPES),
                "payment_installments": self.random.choice([1, 2, 3, 6, 10]),
                "payment_value": paid_amount,
            })

            # Reviews for this order
            review_date = (actual_delivery_dt or est_delivery_dt) + timedelta(days=self.random.randint(1, 4))
            if is_delayed:
                title, comment = self.random.choice(REVIEW_TEMPLATES_NEGATIVE_DELAY)
                score = self.random.choice([1, 2])
            elif has_payment_issue:
                title, comment = self.random.choice(REVIEW_TEMPLATES_PAYMENT_ISSUE)
                score = self.random.choice([1, 2, 3])
            elif self.random.random() < 0.05:
                title, comment = self.random.choice(REVIEW_TEMPLATES_NEGATIVE_PRODUCT)
                score = self.random.choice([1, 2])
            else:
                title, comment = self.random.choice(REVIEW_TEMPLATES_POSITIVE)
                score = self.random.choice([4, 5])

            order_reviews.append({
                "review_id": f"rev_{idx+1:06d}",
                "order_id": order_id,
                "review_score": score,
                "review_comment_title": title,
                "review_comment_message": f"{comment} [Ref: {order_id}]",
                "review_creation_date": review_date,
                "review_answer_timestamp": review_date + timedelta(hours=12),
            })

        # Update sellers SLA stats
        for s in sellers:
            st = seller_stats[s["seller_id"]]
            s["total_orders"] = st["total"]
            s["late_orders_count"] = st["late"]
            if st["total"] > 0:
                s["sla_score"] = round(1.0 - (st["late"] / st["total"]), 3)

        return {
            "customers": customers,
            "sellers": sellers,
            "products": products,
            "orders": orders,
            "order_items": order_items,
            "order_payments": order_payments,
            "order_reviews": order_reviews,
        }

