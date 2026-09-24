import pytest

pytestmark = pytest.mark.django_db


def test_order_over_http(api, world):
    product = (
        api(world.admin, world.syndicat, world.prop)
        .post(
            "/api/v1/store/products/",
            {"name": "Coffee", "price": "3.00", "stock_quantity": 5},
            format="json",
        )
        .json()
    )
    order = api(world.tenant, world.syndicat, world.prop).post(
        "/api/v1/store/orders/",
        {"items": [{"product_id": product["id"], "quantity": 2}], "total_amount": "0.01"},
        format="json",
    )
    assert (
        order.status_code == 201 and order.json()["total_amount"] == "6.00"
    )  # client totals are ignored
