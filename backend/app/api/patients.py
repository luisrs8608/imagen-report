from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.dependencies import get_current_user
from app.core.config import Settings, get_settings
from app.models import User
from app.schemas.patient import PatientSummary
from app.services.errors import IntegrationFailed, IntegrationNotConfigured
from app.services.sheets import SheetsPatientReader

router = APIRouter(prefix="/patients", tags=["patients"])


@router.get("", response_model=list[PatientSummary])
def search_patients(
    query: str = Query(min_length=2, max_length=120),
    _: User = Depends(get_current_user),
    settings: Settings = Depends(get_settings),
) -> list[PatientSummary]:
    try:
        return SheetsPatientReader(settings).search(query=query)
    except IntegrationNotConfigured as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
    except IntegrationFailed as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc
