from google import genai
from google.genai import types

from app.core.config import Settings
from app.services.errors import IntegrationFailed, IntegrationNotConfigured

MEDICAL_REPORT_INSTRUCTIONS = (
    "Actúa como radiólogo dental experto. Traduce esta transcripción a terminología técnica "
    "profesional de odontología/radiología.\n"
    "    Reglas: Mantén fidelidad al original y usa términos precisos.\n"
    "    IMPORTANTE:\n"
    "    1. Al describir lesiones, zonas afectadas o cualquier hallazgo patológico, utiliza "
    'EXCLUSIVAMENTE los términos "radiodenso" o "no radiodenso". Evita el uso de "radiopaco" '
    'o "radiolúcido" para hallazgos patológicos.\n'
    '    2. Al mencionar un posible diagnóstico, utiliza los términos "aparenta" o "sugiere" '
    'en lugar del término "compatible".\n'
    "    3. Cuando se mencionen varios dientes o piezas dentales, sepáralos utilizando la barra "
    'diagonal "/" (por ejemplo: "diente 1.1 / 1.2" o "piezas 18 / 17 / 16").\n'
    "    4. Al registrar medidas o longitudes dentarias y radiculares (ej. conductos "
    'radiculares), separa cada medida con punto y coma ";" y utiliza punto "." para los valores '
    'decimales (por ejemplo: "MV 20.5 mm; ML 20.7 mm; D 19.9 mm").\n'
    "    Aplica puntuación correcta y devuelve SOLO el texto corregido.\n"
)


class GeminiReportGenerator:
    def __init__(self, settings: Settings):
        self.settings = settings

    def generate(self, transcript: str) -> str:
        if not self.settings.gemini_api_key:
            raise IntegrationNotConfigured("Gemini no está configurado en el servidor.")

        client = genai.Client(api_key=self.settings.gemini_api_key)
        try:
            response = client.models.generate_content(
                model=self.settings.gemini_model,
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
