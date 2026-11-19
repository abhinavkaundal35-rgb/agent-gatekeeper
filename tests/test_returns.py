"""Tests for Return and Refund Requests - Requirement 3."""
from src.store.service import StoreService
from src.store.models import (
    CartItem,
    IndianAddress,
    ProductCategory,
    RefundMethod,
    OrderStatus
)

def test_return_processing(test_db, active_agent):
    """Test initiating and processing an eligible return on an Amazon India order."""
    item = CartItem(
        item_id="AMZ-ELEC-02",
        name="boAt Rockerz 450",
        category=ProductCategory.ELECTRONICS,
        unit_price_inr=1499.0,
        quantity=1
    )
    address = IndianAddress(
        address_line="Flat 402, Green Palms, MG Road",
        city="Bengaluru",
        state="Karnataka",
        pincode="560001"
    )
    order = StoreService.create_order(
        customer_id=active_agent.customer_id,
        agent_id=active_agent.agent_id,
        items=[item],
        shipping_address=address,
        db_path=test_db
    )

    # Process return
    ret = StoreService.process_return(
        customer_id=active_agent.customer_id,
        agent_id=active_agent.agent_id,
        order_id=order.order_id,
        item_id=item.item_id,
        reason="Sound distorted on one side",
        refund_method=RefundMethod.AMAZON_PAY_BALANCE,
        refund_amount=1499.0,
        db_path=test_db
    )

    assert ret.return_id.startswith("ret-amz-")
    assert ret.refund_amount == 1499.0
    assert ret.refund_method == RefundMethod.AMAZON_PAY_BALANCE
    assert ret.status == "APPROVED"

    # Verify order state is updated to RETURNED
    updated_order = StoreService.get_order(order.order_id, db_path=test_db)
    assert updated_order.status == OrderStatus.RETURNED

    # Verify listed returns
    returns = StoreService.list_returns(customer_id=active_agent.customer_id, db_path=test_db)
    assert len(returns) == 1
    assert returns[0].return_id == ret.return_id
