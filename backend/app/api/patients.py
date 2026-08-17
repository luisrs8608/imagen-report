from fastapi import APIRouter, Depends, HTTPException, Path, Query, status

from app.api.dependencies import get_current_user
from app.core.config import Settings, get_settings
from app.models import User
from app.schemas.patient import PatientSummary, SheetSelectionResponse
from app.services.errors import IntegrationFailed, IntegrationNotConfigured
from app.services.sheets import SheetsPatientReader

router = APIRouter(prefix="/patients", tags=["patients"])


@router.get("/sheets", response_model=SheetSelectionResponse)
def list_patient_sheets(
    _: User = Depends(get_current_user),
    settings: Settings = Depends(get_settings),
) -> SheetSelectionResponse:
    try:
        return SheetsPatientReader(settings).list_sheets()
    except IntegrationNotConfigured as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
    except IntegrationFailed as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc


@router.get("/row/{row_number}", response_model=PatientSummary)
def get_patient_by_row(
    row_number: int = Path(ge=1),
    sheet: str | None = Query(default=None, min_length=1, max_length=100),
    _: User = Depends(get_current_user),
    settings: Settings = Depends(get_settings),
) -> PatientSummary:
    try:
        patient = SheetsPatientReader(settings).get_by_row(
            row_number=row_number,
            sheet_name=sheet,
        )
        if patient is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"La fila {row_number} no contiene datos de un paciente.",
            )
        return patient
    except IntegrationNotConfigured as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
    except IntegrationFailed as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc


@router.get("", response_model=list[PatientSummary])
def search_patients(
    query: str = Query(min_length=2, max_length=120),
    sheet: str | None = Query(default=None, min_length=1, max_length=100),
    _: User = Depends(get_current_user),
    settings: Settings = Depends(get_settings),
) -> list[PatientSummary]:
    try:
        return SheetsPatientReader(settings).search(query=query, sheet_name=sheet)
    except IntegrationNotConfigured as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
    except IntegrationFailed as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc
