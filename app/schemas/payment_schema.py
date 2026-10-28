from pydantic import BaseModel


class OrderCreateRequest(BaseModel):
    invoice_id: int


class OrderCreateResponse(BaseModel):
    order_id: str
    amount: int
    currency: str
    key_id: str


class PaymentVerifyRequest(BaseModel):
    invoice_id: int
    razorpay_order_id: str
    razorpay_payment_id: str
    razorpay_signature: str
