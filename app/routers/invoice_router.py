from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.models import Client, Invoice, InvoiceStatus
from app.schemas.invoice_schema import InvoiceCreate, InvoiceRead, InvoiceUpdate


router = APIRouter(prefix="/invoices", tags=["Invoices"])


@router.post("", response_model=InvoiceRead, status_code=status.HTTP_201_CREATED)
def create_invoice(payload: InvoiceCreate, db: Session = Depends(get_db)) -> Invoice:
    client = db.get(Client, payload.client_id)
    if client is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Client not found",
        )

    invoice = Invoice(**payload.model_dump())
    db.add(invoice)
    db.commit()
    db.refresh(invoice)
    return invoice


@router.get("", response_model=list[InvoiceRead])
def list_invoices(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
    status_filter: InvoiceStatus | None = Query(default=None, alias="status"),
    client_id: int | None = Query(default=None),
    db: Session = Depends(get_db),
) -> list[Invoice]:
    statement = select(Invoice).order_by(Invoice.id)
    if status_filter is not None:
        statement = statement.where(Invoice.status == status_filter)
    if client_id is not None:
        statement = statement.where(Invoice.client_id == client_id)

    statement = statement.offset(skip).limit(limit)
    return list(db.scalars(statement).all())


def _get_invoice_or_404(db: Session, invoice_id: int) -> Invoice:
    invoice = db.get(Invoice, invoice_id)
    if invoice is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invoice not found",
        )
    return invoice


@router.get("/{invoice_id}", response_model=InvoiceRead)
def get_invoice(invoice_id: int, db: Session = Depends(get_db)) -> Invoice:
    return _get_invoice_or_404(db, invoice_id)


@router.patch("/{invoice_id}", response_model=InvoiceRead)
def update_invoice(
    invoice_id: int,
    payload: InvoiceUpdate,
    db: Session = Depends(get_db),
) -> Invoice:
    invoice = _get_invoice_or_404(db, invoice_id)
    if invoice.status != InvoiceStatus.pending:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Only pending invoices can be updated",
        )

    changes = payload.model_dump(exclude_unset=True)
    for key, value in changes.items():
        setattr(invoice, key, value)

    db.commit()
    db.refresh(invoice)
    return invoice


@router.delete("/{invoice_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_invoice(invoice_id: int, db: Session = Depends(get_db)) -> None:
    invoice = _get_invoice_or_404(db, invoice_id)
    if invoice.status != InvoiceStatus.pending:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Only pending invoices can be deleted",
        )

    db.delete(invoice)
    db.commit()
