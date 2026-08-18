from fastapi import APIRouter, Depends, HTTPException, status

from app.api.dependencies import get_current_user
from app.core.config import Settings, get_settings
from app.models import User
from app.schemas.report import (
    GenerateReportRequest,
    GenerateReportResponse,
    PublishReportRequest,
    PublishReportResponse,
)
from app.services.errors import IntegrationFailed, IntegrationNotConfigured
from app.services.google_publisher import GoogleReportPublisher
from app.services.report_generator import ReportGenerator

router = APIRouter(prefix="/reports", tags=["reports"])


@router.post("/generate", response_model=GenerateReportResponse)
def generate_report(
    payload: GenerateReportRequest,
    _: User = Depends(get_current_user),
    settings: Settings = Depends(get_settings),
) -> GenerateReportResponse:
    try:
        report = ReportGenerator(settings).generate(
            payload.transcript,
            model=payload.model,
        )
    except IntegrationNotConfigured as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
    except IntegrationFailed as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc
    return GenerateReportResponse(report=report)


@router.post("/publish", response_model=PublishReportResponse)
def publish_report(
    payload: PublishReportRequest,
    _: User = Depends(get_current_user),
    settings: Settings = Depends(get_settings),
) -> PublishReportResponse:
    if payload.createGmailDraft and not settings.gmail_draft_enabled:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="La creación de borradores de Gmail está desactivada en la configuración.",
        )
    try:
        return GoogleReportPublisher(settings).publish(payload)
    except IntegrationNotConfigured as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
    except IntegrationFailed as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc
