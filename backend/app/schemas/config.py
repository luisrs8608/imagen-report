from pydantic import BaseModel

from app.core.report_models import ReportModel, ReportProvider


class ReportModelOption(BaseModel):
    id: ReportModel
    provider: ReportProvider
    label: str
    description: str


class PublicConfigResponse(BaseModel):
    gmail_draft_enabled: bool
    report_default_model: ReportModel
    report_models: list[ReportModelOption]
