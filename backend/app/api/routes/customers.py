from typing import Literal

from fastapi import APIRouter, Query

from app.schemas.customers import CustomerResponse
from app.services.customers import get_customers_by_company


router = APIRouter(
    prefix="/companies",
    tags=["Customers"],
)


@router.get(
    "/{company_id}/customers",
    response_model=list[CustomerResponse],
)
def list_company_customers(
    company_id: int,
    queue_status: Literal["review", "completed"] | None = Query(
        default=None,
        description="Filter customers by queue status",
    ),
):
    return get_customers_by_company(
        company_id=company_id,
        queue_status=queue_status,
    )