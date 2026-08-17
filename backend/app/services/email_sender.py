import smtplib
from email.message import EmailMessage

from app.core.config import Settings
from app.services.errors import IntegrationNotConfigured


def send_otp_email(recipient: str, code: str, settings: Settings) -> None:
    if not settings.smtp_host or not settings.smtp_from_email:
        if settings.is_development:
            return
        raise IntegrationNotConfigured(
            "El servicio SMTP para códigos de acceso no está configurado."
        )

    message = EmailMessage()
    message["Subject"] = "Código de acceso a Imagen Report"
    message["From"] = str(settings.smtp_from_email)
    message["To"] = recipient
    message.set_content(
        "Tu código de acceso es: "
        f"{code}\n\nCaduca en {settings.otp_ttl_minutes} minutos y solo puede utilizarse una vez."
    )

    with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=20) as smtp:
        if settings.smtp_use_tls:
            smtp.starttls()
        if settings.smtp_username and settings.smtp_password:
            smtp.login(settings.smtp_username, settings.smtp_password)
        smtp.send_message(message)
