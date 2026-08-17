from datetime import date

import pytest
from pydantic import ValidationError

from app.core.config import Settings
from app.schemas.report import PublishReportRequest
from app.services.errors import IntegrationNotConfigured
from app.services.google_publisher import GoogleReportPublisher


def valid_payload(**overrides):
    payload = {
        "ciPaciente": "45691787",
        "nombrePaciente": "Sofía Araujo",
        "doctor_gender": "Dra.",
        "doctor": "Viviana Lambrechts",
        "fecha": date(2026, 8, 16),
        "measures": "0.5",
        "texto": "Informe revisado.",
        "driveUrl": "https://drive.google.com/example",
        "recipientEmail": None,
        "createGmailDraft": False,
        "approved": True,
    }
    payload.update(overrides)
    return payload


def test_publish_requires_medical_approval():
    with pytest.raises(ValidationError):
        PublishReportRequest(**valid_payload(approved=False))


def test_gmail_requires_recipient():
    with pytest.raises(ValidationError):
        PublishReportRequest(**valid_payload(createGmailDraft=True))


def test_google_doc_placeholders_match_legacy_workflow():
    report = PublishReportRequest(**valid_payload())
    publisher = GoogleReportPublisher(Settings())
    requests = publisher._replacement_requests(report)
    placeholders = {request["replaceAllText"]["containsText"]["text"] for request in requests}

    assert placeholders == {
        "{{ paciente }}",
        "{{ doctor }}",
        "{{ fecha }}",
        "{{ analisis }}",
        "{{ CI }}",
        "{{ driver link }}",
        "{{ measures }}",
        "{{ doctor_gender }}",
    }


def test_gmail_draft_is_rejected_when_feature_is_disabled():
    report = PublishReportRequest(
        **valid_payload(createGmailDraft=True, recipientEmail="doctor@gmail.com")
    )
    publisher = GoogleReportPublisher(Settings(gmail_draft_enabled=False))

    with pytest.raises(IntegrationNotConfigured):
        publisher.publish(report)
