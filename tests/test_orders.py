"""Tests for Order Viewing and Purchasing Requests - Requirement 2."""
from src.store.service import StoreService
from src.store.models import CartItem, IndianAddress, ProductCategory, OrderStatus

def test_order_creation_and_viewing(test_db, active_agent):
    """Test creating an order in INR with Indian address, then retrieving it."""
    items = [
        CartItem(
            item_id="AMZ-GROC-01",
            name="Tata Tea Gold 1kg",
            category=ProductCategory.GROCERY,
            unit_price_inr=520.0,
            quantity=2
        ),
        CartItem(
            item_id="AMZ-ELEC-02",
            name="boAt Rockerz 450",
            category=ProductCategory.ELECTRONICS,
            unit_price_inr=1499.0,
            quantity=1
        )
    ]
    address = IndianAddress(
        address_line="Flat 402, Green Palms, MG Road",
        city="Bengaluru",
        state="Karnataka",
        pincode="560001"
    )

    order = StoreService.create_order(
        customer_id=active_agent.customer_id,
        agent_id=active_agent.agent_id,
        items=items,
        shipping_address=address,
        db_path=test_db
    )

    assert order.order_id.startswith("ord-amz-")
    assert order.total_amount == (520.0 * 2) + 1499.0
    assert order.currency == "INR"
    assert order.status == OrderStatus.PLACED

    # View order by ID
    fetched = StoreService.get_order(order.order_id, db_path=test_db)
    assert fetched is not None
    assert fetched.order_id == order.order_id
    assert fetched.shipping_address.pincode == "560001"

    # List orders for customer
    orders = StoreService.list_orders(customer_id=active_agent.customer_id, db_path=test_db)
    assert len(orders) >= 1
    assert any(o.order_id == order.order_id for o in orders)
