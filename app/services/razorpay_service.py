import hashlib
import hmac
from uuid import uuid4

import razorpay

from app.config import settings


client = razorpay.Client(
    auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET)
)


def create_order(amount: int, receipt: str) -> str:
    if settings.RAZORPAY_MOCK:
        return f"order_mock_{uuid4().hex[:12]}"

    order = client.order.create(
        {
            "amount": amount,
            "currency": "INR",
            "receipt": receipt,
        }
    )
    return order["id"]


def verify_signature(order_id: str, payment_id: str, signature: str) -> bool:
    if settings.RAZORPAY_MOCK:
        message = f"{order_id}|{payment_id}"
        expected_signature = hmac.new(
            settings.RAZORPAY_KEY_SECRET.encode(),
            message.encode(),
            hashlib.sha256,
        ).hexdigest()
        return hmac.compare_digest(
            signature.encode("utf-8", errors="replace"),
            expected_signature.encode("utf-8"),
        )

    try:
        client.utility.verify_payment_signature(
            {
                "razorpay_order_id": order_id,
                "razorpay_payment_id": payment_id,
                "razorpay_signature": signature,
            }
        )
    except razorpay.errors.SignatureVerificationError:
        return False
    return True
