from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models import InvoiceStatus


class InvoiceCreate(BaseModel):
    client_id: int
    description: str = Field(min_length=1)
    amount: int = Field(ge=1)

    model_config = ConfigDict(str_strip_whitespace=True)


class InvoiceUpdate(BaseModel):
    description: str | None = Field(default=None, min_length=1)
    amount: int | None = Field(default=None, ge=1)

    model_config = ConfigDict(str_strip_whitespace=True)


class InvoiceRead(BaseModel):
    id: int
    client_id: int
    description: str
    amount: int
    status: InvoiceStatus
    razorpay_order_id: str | None
    razorpay_payment_id: str | None
    created_at: datetime
    paid_at: datetime | None

    model_config = ConfigDict(from_attributes=True)
