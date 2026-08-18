from google import genai
from google.genai import types

from app.core.config import Settings
from app.core.report_models import SUPPORTED_GEMINI_MODELS, GeminiModel
from app.services.errors import IntegrationFailed, IntegrationNotConfigured
from app.services.report_prompt import MEDICAL_REPORT_INSTRUCTIONS


class GeminiReportGenerator:
    def __init__(self, settings: Settings):
        self.settings = settings

    def generate(self, transcript: str, model: GeminiModel) -> str:
        if not self.settings.gemini_api_key:
            raise IntegrationNotConfigured("Gemini no está configurado en el servidor.")

        if model not in SUPPORTED_GEMINI_MODELS:
            raise IntegrationNotConfigured("El modelo de Gemini seleccionado no está habilitado.")

        client = genai.Client(api_key=self.settings.gemini_api_key)
        try:
            response = client.models.generate_content(
                model=model,
                contents=transcript,
                config=types.GenerateContentConfig(
                    system_instruction=MEDICAL_REPORT_INSTRUCTIONS,
                ),
            )
        except Exception as exc:
            raise IntegrationFailed("Gemini no pudo generar el borrador.") from exc

        text = (response.text or "").strip()
        if not text:
            raise IntegrationFailed("Gemini devolvió una respuesta vacía.")
        return text
