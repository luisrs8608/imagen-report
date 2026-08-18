from typing import cast

from app.core.config import Settings
from app.core.report_models import (
    SUPPORTED_GEMINI_MODELS,
    SUPPORTED_OPENAI_MODELS,
    GeminiModel,
    OpenAIModel,
    ReportModel,
)
from app.services.errors import IntegrationNotConfigured
from app.services.gemini import GeminiReportGenerator
from app.services.openai_report import OpenAIReportGenerator


class ReportGenerator:
    def __init__(self, settings: Settings):
        self.settings = settings

    def generate(self, transcript: str, model: ReportModel | None = None) -> str:
        selected_model = model or self.settings.report_model
        if selected_model in SUPPORTED_GEMINI_MODELS:
            return GeminiReportGenerator(self.settings).generate(
                transcript,
                cast(GeminiModel, selected_model),
            )
        if selected_model in SUPPORTED_OPENAI_MODELS:
            return OpenAIReportGenerator(self.settings).generate(
                transcript,
                cast(OpenAIModel, selected_model),
            )
        raise IntegrationNotConfigured("El modelo de IA seleccionado no está habilitado.")
