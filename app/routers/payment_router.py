from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.config import settings
from app.database.session import get_db
from app.models import Invoice, InvoiceStatus
from app.schemas.invoice_schema import InvoiceRead
from app.schemas.payment_schema import (
    OrderCreateRequest,
    OrderCreateResponse,
    PaymentVerifyRequest,
)
from app.services.razorpay_service import create_order, verify_signature


router = APIRouter(prefix="/payments", tags=["Payments"])


def _get_invoice_or_404(db: Session, invoice_id: int) -> Invoice:
    invoice = db.get(Invoice, invoice_id)
    if invoice is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invoice not found",
        )
    return invoice


@router.post("/orders", response_model=OrderCreateResponse)
def create_payment_order(
    payload: OrderCreateRequest,
    db: Session = Depends(get_db),
) -> OrderCreateResponse:
    invoice = _get_invoice_or_404(db, payload.invoice_id)
    if invoice.status != InvoiceStatus.pending:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Only pending invoices can have payment orders",
        )

    if invoice.razorpay_order_id:
        order_id = invoice.razorpay_order_id
    else:
        try:
            order_id = create_order(invoice.amount, f"invoice-{invoice.id}")
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Unable to create Razorpay order",
            ) from exc

        invoice.razorpay_order_id = order_id
        db.commit()

    return OrderCreateResponse(
        order_id=order_id,
        amount=invoice.amount,
        currency="INR",
        key_id=settings.RAZORPAY_KEY_ID,
    )


@router.post("/verify", response_model=InvoiceRead)
def verify_payment(
    payload: PaymentVerifyRequest,
    db: Session = Depends(get_db),
) -> Invoice:
    invoice = _get_invoice_or_404(db, payload.invoice_id)
    if invoice.razorpay_order_id != payload.razorpay_order_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Order ID does not match this invoice",
        )

    if invoice.status == InvoiceStatus.paid:
        return invoice

    if not verify_signature(
        payload.razorpay_order_id,
        payload.razorpay_payment_id,
        payload.razorpay_signature,
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid payment signature",
        )

    invoice.status = InvoiceStatus.paid
    invoice.razorpay_payment_id = payload.razorpay_payment_id
    invoice.paid_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(invoice)
    return invoice
