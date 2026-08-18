from openai import OpenAI

from app.core.config import Settings
from app.core.report_models import SUPPORTED_OPENAI_MODELS, OpenAIModel
from app.services.errors import IntegrationFailed, IntegrationNotConfigured
from app.services.report_prompt import MEDICAL_REPORT_INSTRUCTIONS


class OpenAIReportGenerator:
    def __init__(self, settings: Settings):
        self.settings = settings

    def generate(self, transcript: str, model: OpenAIModel) -> str:
        if not self.settings.openai_api_key:
            raise IntegrationNotConfigured("OpenAI no está configurado en el servidor.")

        if model not in SUPPORTED_OPENAI_MODELS:
            raise IntegrationNotConfigured("El modelo de OpenAI seleccionado no está habilitado.")

        client = OpenAI(api_key=self.settings.openai_api_key)
        try:
            response = client.responses.create(
                model=model,
                instructions=MEDICAL_REPORT_INSTRUCTIONS,
                input=transcript,
            )
        except Exception as exc:
            raise IntegrationFailed("OpenAI no pudo generar el borrador.") from exc

        text = (response.output_text or "").strip()
        if not text:
            raise IntegrationFailed("OpenAI devolvió una respuesta vacía.")
        return text
