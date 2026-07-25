from fastapi import APIRouter

from app.schemas.company import CompanyResponse
from app.services.company import get_all_companies

router = APIRouter(prefix="/companies",tags=["Companies"],)


@router.get("", response_model=list[CompanyResponse])
def list_companies():
    return get_all_companies()