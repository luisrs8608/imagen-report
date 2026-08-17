import base64
import io
import re
from email.message import EmailMessage

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload

from app.core.config import Settings
from app.schemas.report import PublishReportRequest, PublishReportResponse
from app.services.errors import IntegrationFailed, IntegrationNotConfigured

GOOGLE_DOCUMENT_SCOPES = [
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/documents",
]
GMAIL_DRAFT_SCOPE = "https://www.googleapis.com/auth/gmail.compose"


def safe_file_part(value: str) -> str:
    value = re.sub(r"[\\/:*?\"<>|]+", "-", value).strip()
    return re.sub(r"\s+", " ", value)[:120] or "informe"


class GoogleReportPublisher:
    def __init__(self, settings: Settings):
        self.settings = settings

    def publish(self, report: PublishReportRequest) -> PublishReportResponse:
        if report.createGmailDraft and not self.settings.gmail_draft_enabled:
            raise IntegrationNotConfigured(
                "La creación de borradores de Gmail está desactivada en la configuración."
            )
        credentials = self._credentials()
        drive = build("drive", "v3", credentials=credentials, cache_discovery=False)
        docs = build("docs", "v1", credentials=credentials, cache_discovery=False)

        file_stem = safe_file_part(
            f"{report.fecha.isoformat()} - {report.nombrePaciente} - {report.ciPaciente}"
        )

        try:
            copied_document = (
                drive.files()
                .copy(
                    fileId=self.settings.google_docs_template_id,
                    supportsAllDrives=True,
                    body={
                        "name": file_stem,
                        "parents": [self.settings.google_drive_output_folder_id],
                    },
                    fields="id,name,webViewLink",
                )
                .execute()
            )
            document_id = copied_document["id"]

            docs.documents().batchUpdate(
                documentId=document_id,
                body={"requests": self._replacement_requests(report)},
            ).execute()

            pdf_bytes = (
                drive.files().export(fileId=document_id, mimeType="application/pdf").execute()
            )
            pdf_metadata = (
                drive.files()
                .create(
                    supportsAllDrives=True,
                    body={
                        "name": f"{file_stem}.pdf",
                        "parents": [self.settings.google_drive_output_folder_id],
                    },
                    media_body=MediaIoBaseUpload(
                        io.BytesIO(pdf_bytes),
                        mimetype="application/pdf",
                        resumable=False,
                    ),
                    fields="id,name,webViewLink",
                )
                .execute()
            )

            draft_id = None
            if report.createGmailDraft:
                draft_id = self._create_gmail_draft(
                    credentials=credentials,
                    report=report,
                    pdf_bytes=pdf_bytes,
                    pdf_filename=f"{file_stem}.pdf",
                )
        except Exception as exc:
            raise IntegrationFailed(
                "No fue posible crear el documento final en Google Workspace."
            ) from exc

        return PublishReportResponse(
            document_id=document_id,
            document_url=copied_document.get(
                "webViewLink", f"https://docs.google.com/document/d/{document_id}/edit"
            ),
            pdf_id=pdf_metadata["id"],
            pdf_url=pdf_metadata.get(
                "webViewLink", f"https://drive.google.com/file/d/{pdf_metadata['id']}/view"
            ),
            gmail_draft_id=draft_id,
        )

    def _credentials(self) -> Credentials:
        required = [
            self.settings.google_oauth_client_id,
            self.settings.google_oauth_client_secret,
            self.settings.google_oauth_refresh_token,
        ]
        if not all(required):
            raise IntegrationNotConfigured(
                "La cuenta institucional para Google Docs, Drive y Gmail no está configurada."
            )
        return Credentials(
            token=None,
            refresh_token=self.settings.google_oauth_refresh_token,
            token_uri=self.settings.google_oauth_token_uri,
            client_id=self.settings.google_oauth_client_id,
            client_secret=self.settings.google_oauth_client_secret,
            scopes=[
                *GOOGLE_DOCUMENT_SCOPES,
                *([GMAIL_DRAFT_SCOPE] if self.settings.gmail_draft_enabled else []),
            ],
        )

    def _replacement_requests(self, report: PublishReportRequest) -> list[dict]:
        replacements = {
            "{{ paciente }}": report.nombrePaciente,
            "{{ doctor }}": report.doctor,
            "{{ fecha }}": report.fecha.strftime("%d/%m/%Y"),
            "{{ analisis }}": report.texto,
            "{{ CI }}": report.ciPaciente,
            "{{ driver link }}": report.driveUrl,
            "{{ measures }}": report.measures,
            "{{ doctor_gender }}": report.doctor_gender,
        }
        return [
            {
                "replaceAllText": {
                    "containsText": {"text": placeholder, "matchCase": True},
                    "replaceText": replacement,
                }
            }
            for placeholder, replacement in replacements.items()
        ]

    def _create_gmail_draft(
        self,
        *,
        credentials: Credentials,
        report: PublishReportRequest,
        pdf_bytes: bytes,
        pdf_filename: str,
    ) -> str:
        if not report.recipientEmail:
            raise ValueError("Falta el correo destinatario.")

        message = EmailMessage()
        message["To"] = str(report.recipientEmail)
        message["Subject"] = f"Informe radiológico - {report.nombrePaciente}"
        message.set_content(
            f"{report.doctor_gender} {report.doctor}:\n\n"
            f"Adjuntamos el informe correspondiente a {report.nombrePaciente}.\n\n"
            "Saludos."
        )
        message.add_attachment(
            pdf_bytes,
            maintype="application",
            subtype="pdf",
            filename=pdf_filename,
        )

        gmail = build("gmail", "v1", credentials=credentials, cache_discovery=False)
        encoded = base64.urlsafe_b64encode(message.as_bytes()).decode()
        draft = (
            gmail.users()
            .drafts()
            .create(
                userId=self.settings.gmail_user_id,
                body={"message": {"raw": encoded}},
            )
            .execute()
        )
        return draft["id"]
