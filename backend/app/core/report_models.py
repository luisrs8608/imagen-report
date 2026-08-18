from typing import Literal

GeminiModel = Literal["gemini-3.5-flash-lite", "gemini-3.6-flash"]
OpenAIModel = Literal["gpt-5.6-luna"]
ReportProvider = Literal["google", "openai"]
ReportModel = Literal[
    "gemini-3.5-flash-lite",
    "gemini-3.6-flash",
    "gpt-5.6-luna",
]

REPORT_MODEL_OPTIONS: tuple[dict[str, str], ...] = (
    {
        "id": "gemini-3.5-flash-lite",
        "provider": "google",
        "label": "Google · Gemini 3.5 Flash-Lite",
        "description": "Más rápido y económico para generar el borrador técnico.",
    },
    {
        "id": "gemini-3.6-flash",
        "provider": "google",
        "label": "Google · Gemini 3.6 Flash",
        "description": "Mayor capacidad de razonamiento y seguimiento de instrucciones.",
    },
    {
        "id": "gpt-5.6-luna",
        "provider": "openai",
        "label": "OpenAI · GPT-5.6 Luna",
        "description": "Modelo eficiente de OpenAI para tareas de gran volumen.",
    },
)

SUPPORTED_GEMINI_MODELS = frozenset(
    option["id"] for option in REPORT_MODEL_OPTIONS if option["provider"] == "google"
)
SUPPORTED_OPENAI_MODELS = frozenset(
    option["id"] for option in REPORT_MODEL_OPTIONS if option["provider"] == "openai"
)
