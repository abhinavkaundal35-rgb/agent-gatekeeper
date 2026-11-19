"""Amazon India Mock Store Service handling Orders, Catalog, and Returns."""
import json
import uuid
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from src.core.database import get_db_connection
from src.store.models import (
    CartItem,
    IndianAddress,
    OrderResponse,
    OrderStatus,
    ReturnResponse,
    RefundMethod,
    ProductCategory
)

# Reference sample catalog for Amazon India
SAMPLE_CATALOG = [
    CartItem(item_id="AMZ-ELEC-01", name="Echo Dot (5th Gen) Smart Speaker", category=ProductCategory.ELECTRONICS, unit_price_inr=4499.0, quantity=1),
    CartItem(item_id="AMZ-ELEC-02", name="boAt Rockerz 450 Bluetooth Headphones", category=ProductCategory.ELECTRONICS, unit_price_inr=1499.0, quantity=1),
    CartItem(item_id="AMZ-GROC-01", name="Tata Tea Gold 1kg", category=ProductCategory.GROCERY, unit_price_inr=520.0, quantity=1),
    CartItem(item_id="AMZ-GROC-02", name="Aashirvaad Superior MP Atta 10kg", category=ProductCategory.GROCERY, unit_price_inr=495.0, quantity=1),
    CartItem(item_id="AMZ-JEWL-01", name="Candere by Kalyan Jewellers Gold Pendant", category=ProductCategory.JEWELRY, unit_price_inr=18500.0, quantity=1),
    CartItem(item_id="AMZ-FASH-01", name="Cotton Casual Shirt for Men", category=ProductCategory.FASHION, unit_price_inr=899.0, quantity=1),
    CartItem(item_id="AMZ-HOME-01", name="Prestige Iris 750 Watt Mixer Grinder", category=ProductCategory.HOME, unit_price_inr=3199.0, quantity=1),
]

class StoreService:
    @staticmethod
    def get_customer_verified_pincodes(customer_id: str, db_path: Optional[str] = None) -> List[str]:
        """Fetch verified PIN codes for the customer."""
        conn = get_db_connection(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT verified_pincodes FROM customers WHERE customer_id = ?", (customer_id,))
        row = cursor.fetchone()
        conn.close()
        if row and row["verified_pincodes"]:
            return json.loads(row["verified_pincodes"])
        return ["560001"] # Default fallback

    @staticmethod
    def create_order(
        customer_id: str,
        agent_id: str,
        items: List[CartItem],
        shipping_address: IndianAddress,
        db_path: Optional[str] = None
    ) -> OrderResponse:
        """Create and place an Amazon India order."""
        conn = get_db_connection(db_path)
        cursor = conn.cursor()

        order_id = f"ord-amz-{uuid.uuid4().hex[:8]}"
        total_amount = sum(item.total_price for item in items)
        now_iso = datetime.now(timezone.utc).isoformat()

        shipping_json = json.dumps(shipping_address.model_dump())
        items_json = json.dumps([item.model_dump() for item in items])

        cursor.execute("""
        INSERT INTO orders (
            order_id, customer_id, agent_id, total_amount, currency,
            status, shipping_address, items, placed_at, delivered_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            order_id,
            customer_id,
            agent_id,
            total_amount,
            "INR",
            OrderStatus.PLACED.value,
            shipping_json,
            items_json,
            now_iso,
            None
        ))
        conn.commit()
        conn.close()

        return OrderResponse(
            order_id=order_id,
            customer_id=customer_id,
            agent_id=agent_id,
            total_amount=total_amount,
            currency="INR",
            status=OrderStatus.PLACED,
            shipping_address=shipping_address,
            items=items,
            placed_at=now_iso,
            delivered_at=None
        )

    @staticmethod
    def get_order(order_id: str, db_path: Optional[str] = None) -> Optional[OrderResponse]:
        """Retrieve order details by order ID."""
        conn = get_db_connection(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM orders WHERE order_id = ?", (order_id,))
        row = cursor.fetchone()
        conn.close()

        if not row:
            return None

        shipping_data = json.loads(row["shipping_address"])
        items_data = json.loads(row["items"])

        return OrderResponse(
            order_id=row["order_id"],
            customer_id=row["customer_id"],
            agent_id=row["agent_id"],
            total_amount=row["total_amount"],
            currency=row["currency"],
            status=OrderStatus(row["status"]),
            shipping_address=IndianAddress(**shipping_data),
            items=[CartItem(**item) for item in items_data],
            placed_at=row["placed_at"],
            delivered_at=row["delivered_at"]
        )

    @staticmethod
    def list_orders(
        customer_id: Optional[str] = None,
        agent_id: Optional[str] = None,
        db_path: Optional[str] = None
    ) -> List[OrderResponse]:
        """List orders matching criteria."""
        conn = get_db_connection(db_path)
        cursor = conn.cursor()

        query = "SELECT * FROM orders WHERE 1=1"
        params: List[Any] = []

        if customer_id:
            query += " AND customer_id = ?"
            params.append(customer_id)
        if agent_id:
            query += " AND agent_id = ?"
            params.append(agent_id)

        query += " ORDER BY placed_at DESC"
        cursor.execute(query, tuple(params))
        rows = cursor.fetchall()
        conn.close()

        results = []
        for row in rows:
            results.append(OrderResponse(
                order_id=row["order_id"],
                customer_id=row["customer_id"],
                agent_id=row["agent_id"],
                total_amount=row["total_amount"],
                currency=row["currency"],
                status=OrderStatus(row["status"]),
                shipping_address=IndianAddress(**json.loads(row["shipping_address"])),
                items=[CartItem(**i) for i in json.loads(row["items"])],
                placed_at=row["placed_at"],
                delivered_at=row["delivered_at"]
            ))
        return results

    @staticmethod
    def process_return(
        customer_id: str,
        agent_id: str,
        order_id: str,
        item_id: str,
        reason: str,
        refund_method: RefundMethod = RefundMethod.AMAZON_PAY_BALANCE,
        refund_amount: Optional[float] = None,
        db_path: Optional[str] = None
    ) -> ReturnResponse:
        """Register and execute a return for an order item."""
        conn = get_db_connection(db_path)
        cursor = conn.cursor()

        return_id = f"ret-amz-{uuid.uuid4().hex[:8]}"
        now_iso = datetime.now(timezone.utc).isoformat()

        # If refund amount not explicitly passed, compute from order item
        final_refund = refund_amount
        if final_refund is None:
            order = StoreService.get_order(order_id, db_path=db_path)
            if order:
                for item in order.items:
                    if item.item_id == item_id:
                        final_refund = item.total_price
                        break
        if final_refund is None:
            final_refund = 0.0

        cursor.execute("""
        INSERT INTO returns (
            return_id, order_id, customer_id, agent_id, item_id,
            reason, refund_amount, refund_method, status, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            return_id,
            order_id,
            customer_id,
            agent_id,
            item_id,
            reason,
            final_refund,
            refund_method.value,
            "APPROVED",
            now_iso
        ))

        # Mark order item as returned
        cursor.execute("""
        UPDATE orders SET status = ? WHERE order_id = ?
        """, (OrderStatus.RETURNED.value, order_id))

        conn.commit()
        conn.close()

        return ReturnResponse(
            return_id=return_id,
            order_id=order_id,
            customer_id=customer_id,
            agent_id=agent_id,
            item_id=item_id,
            reason=reason,
            refund_amount=final_refund,
            refund_method=refund_method,
            status="APPROVED",
            created_at=now_iso,
            message=f"Return processed successfully. Refund of ₹{final_refund:,.2f} initiated via {refund_method.value}."
        )

    @staticmethod
    def list_returns(customer_id: Optional[str] = None, db_path: Optional[str] = None) -> List[ReturnResponse]:
        """List recorded returns."""
        conn = get_db_connection(db_path)
        cursor = conn.cursor()
        if customer_id:
            cursor.execute("SELECT * FROM returns WHERE customer_id = ? ORDER BY created_at DESC", (customer_id,))
        else:
            cursor.execute("SELECT * FROM returns ORDER BY created_at DESC")
        rows = cursor.fetchall()
        conn.close()

        return [
            ReturnResponse(
                return_id=row["return_id"],
                order_id=row["order_id"],
                customer_id=row["customer_id"],
                agent_id=row["agent_id"],
                item_id=row["item_id"],
                reason=row["reason"],
                refund_amount=row["refund_amount"],
                refund_method=RefundMethod(row["refund_method"]),
                status=row["status"],
                created_at=row["created_at"],
                message="Return on record."
            )
            for row in rows
        ]
