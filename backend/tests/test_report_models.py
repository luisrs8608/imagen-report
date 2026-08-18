from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from app.core.config import Settings
from app.schemas.report import GenerateReportRequest
from app.services.gemini import GeminiReportGenerator
from app.services.openai_report import OpenAIReportGenerator
from app.services.report_generator import ReportGenerator


class FakeGeminiModels:
    def __init__(self) -> None:
        self.requested_model: str | None = None

    def generate_content(self, *, model: str, contents: str, config: object) -> object:
        self.requested_model = model
        return SimpleNamespace(text="Informe técnico Gemini.")


class FakeGeminiClient:
    def __init__(self, models: FakeGeminiModels) -> None:
        self.models = models


class FakeOpenAIResponses:
    def __init__(self) -> None:
        self.requested_model: str | None = None
        self.instructions: str | None = None

    def create(self, *, model: str, instructions: str, input: str) -> object:
        self.requested_model = model
        self.instructions = instructions
        return SimpleNamespace(output_text="Informe técnico OpenAI.")


class FakeOpenAIClient:
    def __init__(self, responses: FakeOpenAIResponses) -> None:
        self.responses = responses


@pytest.mark.parametrize(
    "model",
    ["gemini-3.5-flash-lite", "gemini-3.6-flash", "gpt-5.6-luna"],
)
def test_generate_report_request_accepts_enabled_models(model: str) -> None:
    request = GenerateReportRequest(transcript="Texto dictado.", model=model)

    assert request.model == model


def test_generate_report_request_rejects_arbitrary_model() -> None:
    with pytest.raises(ValidationError):
        GenerateReportRequest(transcript="Texto dictado.", model="modelo-no-permitido")


def test_gemini_generator_uses_selected_model(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_models = FakeGeminiModels()
    monkeypatch.setattr(
        "app.services.gemini.genai.Client",
        lambda **_: FakeGeminiClient(fake_models),
    )

    report = GeminiReportGenerator(Settings(gemini_api_key="test-key")).generate(
        "Texto dictado.",
        model="gemini-3.6-flash",
    )

    assert report == "Informe técnico Gemini."
    assert fake_models.requested_model == "gemini-3.6-flash"


def test_openai_generator_uses_responses_api(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_responses = FakeOpenAIResponses()
    monkeypatch.setattr(
        "app.services.openai_report.OpenAI",
        lambda **_: FakeOpenAIClient(fake_responses),
    )

    report = OpenAIReportGenerator(Settings(openai_api_key="test-key")).generate(
        "Texto dictado.",
        model="gpt-5.6-luna",
    )

    assert report == "Informe técnico OpenAI."
    assert fake_responses.requested_model == "gpt-5.6-luna"
    assert fake_responses.instructions


def test_report_generator_uses_configured_default_model(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "app.services.report_generator.GeminiReportGenerator.generate",
        lambda *_: "Informe predeterminado.",
    )
    generator = ReportGenerator(
        Settings(
            gemini_api_key="test-key",
            report_model="gemini-3.5-flash-lite",
        )
    )

    assert generator.generate("Texto dictado.") == "Informe predeterminado."


def test_report_generator_routes_openai_model(monkeypatch: pytest.MonkeyPatch) -> None:
    requested_models: list[str] = []

    def fake_generate(_: object, transcript: str, model: str) -> str:
        requested_models.append(model)
        return f"Informe para: {transcript}"

    monkeypatch.setattr(
        "app.services.report_generator.OpenAIReportGenerator.generate",
        fake_generate,
    )

    report = ReportGenerator(Settings(openai_api_key="test-key")).generate(
        "Texto dictado.",
        model="gpt-5.6-luna",
    )

    assert report == "Informe para: Texto dictado."
    assert requested_models == ["gpt-5.6-luna"]
