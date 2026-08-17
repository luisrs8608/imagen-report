from google import genai
from google.genai import types

from app.core.config import Settings
from app.services.errors import IntegrationFailed, IntegrationNotConfigured

MEDICAL_REPORT_INSTRUCTIONS = """Actúa como asistente de redacción para un radiólogo dental.
Convierte la transcripción en un borrador técnico profesional de odontología/radiología.

Reglas obligatorias:
- Mantén estricta fidelidad al original. No agregues hallazgos, diagnósticos, piezas,
  medidas ni lateralidad.
- Si una parte es ambigua, consérvala sin inventar y señálala entre corchetes como [REVISAR: ...].
- Para lesiones o hallazgos patológicos utiliza exclusivamente «radiodenso» o «no radiodenso»;
  no utilices «radiopaco» ni «radiolúcido».
- Para un posible diagnóstico utiliza «aparenta» o «sugiere», nunca «compatible».
- Separa varias piezas dentales con « / ».
- Separa medidas con punto y coma y utiliza punto para decimales.
- Devuelve únicamente el borrador, sin explicaciones ni encabezados añadidos.

La salida es un borrador y debe ser revisada por un profesional antes de publicarse.
"""


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
