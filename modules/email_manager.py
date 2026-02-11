"""
J.A.R.V.I.S. — Email Manager Module
Envío de correos electrónicos vía SMTP.
"""

import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from pathlib import Path
from typing import Optional

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import (
    EMAIL_SMTP_SERVER,
    EMAIL_SMTP_PORT,
    EMAIL_USE_TLS,
)

logger = logging.getLogger("jarvis.email_manager")


class EmailManager:
    """Gestiona el envío de correos electrónicos."""

    def __init__(self):
        self._credentials = None
        logger.info("EmailManager inicializado.")

    # ─── Configuración de credenciales ────────────────────────

    def setup_credentials(self, email: str, password: str) -> str:
        """
        Configura las credenciales de correo de forma segura.
        Usa keyring para almacenamiento seguro en el sistema.
        """
        try:
            import keyring
            keyring.set_password("jarvis_email", "email", email)
            keyring.set_password("jarvis_email", "password", password)
            self._credentials = {"email": email, "password": password}
            logger.info(f"Credenciales configuradas para: {email}")
            return "Credenciales de correo configuradas correctamente."
        except ImportError:
            # Fallback: guardar en memoria (no persistente)
            self._credentials = {"email": email, "password": password}
            logger.warning(
                "keyring no disponible. Credenciales solo en memoria."
            )
            return (
                "Credenciales guardadas en memoria. "
                "Instale 'keyring' para almacenamiento seguro."
            )
        except Exception as e:
            logger.error(f"Error configurando credenciales: {e}")
            return f"Error al configurar credenciales: {e}"

    def _get_credentials(self) -> Optional[dict]:
        """Obtiene las credenciales almacenadas."""
        if self._credentials:
            return self._credentials

        try:
            import keyring
            email = keyring.get_password("jarvis_email", "email")
            password = keyring.get_password("jarvis_email", "password")
            if email and password:
                self._credentials = {"email": email, "password": password}
                return self._credentials
        except ImportError:
            pass
        except Exception as e:
            logger.error(f"Error obteniendo credenciales: {e}")

        return None

    # ─── Envío de correos ─────────────────────────────────────

    def send_email(
        self,
        recipient: str,
        subject: str = "",
        body: str = "",
        html: bool = False,
        attachments: list = None,
        smtp_server: str = None,
        smtp_port: int = None,
    ) -> str:
        """
        Envía un correo electrónico.

        Args:
            recipient: Dirección de correo del destinatario.
            subject: Asunto del correo.
            body: Cuerpo del correo.
            html: Si True, el cuerpo es HTML.
            attachments: Lista de rutas de archivos adjuntos.
            smtp_server: Servidor SMTP (override).
            smtp_port: Puerto SMTP (override).

        Returns:
            Mensaje de confirmación o error.
        """
        creds = self._get_credentials()
        if not creds:
            return (
                "No hay credenciales de correo configuradas, señor. "
                "Use el comando de configuración de correo primero."
            )

        server = smtp_server or EMAIL_SMTP_SERVER
        port = smtp_port or EMAIL_SMTP_PORT

        try:
            # Construir mensaje
            msg = MIMEMultipart()
            msg["From"] = creds["email"]
            msg["To"] = recipient
            msg["Subject"] = subject or "(Sin asunto)"

            # Cuerpo
            content_type = "html" if html else "plain"
            msg.attach(MIMEText(body, content_type, "utf-8"))

            # Adjuntos
            if attachments:
                for file_path in attachments:
                    path = Path(file_path)
                    if path.exists():
                        with open(path, "rb") as f:
                            part = MIMEBase("application", "octet-stream")
                            part.set_payload(f.read())
                        encoders.encode_base64(part)
                        part.add_header(
                            "Content-Disposition",
                            f'attachment; filename="{path.name}"',
                        )
                        msg.attach(part)
                    else:
                        logger.warning(f"Adjunto no encontrado: {file_path}")

            # Enviar
            with smtplib.SMTP(server, port) as smtp:
                if EMAIL_USE_TLS:
                    smtp.starttls()
                smtp.login(creds["email"], creds["password"])
                smtp.send_message(msg)

            logger.info(f"Correo enviado a: {recipient}")
            return f"Correo enviado exitosamente a {recipient}."

        except smtplib.SMTPAuthenticationError:
            return (
                "Error de autenticación. Verifique sus credenciales, señor. "
                "Si usa Gmail, habilite 'contraseñas de aplicaciones'."
            )
        except smtplib.SMTPException as e:
            logger.error(f"Error SMTP: {e}")
            return f"Error al enviar correo: {e}"
        except Exception as e:
            logger.error(f"Error inesperado enviando correo: {e}")
            return f"Error inesperado: {e}"

    def compose_email(self, recipient: str, subject: str, body: str) -> dict:
        """
        Prepara un correo para revisión antes de enviar.

        Returns:
            Diccionario con los datos del correo para confirmar.
        """
        return {
            "to": recipient,
            "subject": subject,
            "body": body,
            "status": "draft",
        }

    def is_configured(self) -> bool:
        """Verifica si las credenciales están configuradas."""
        return self._get_credentials() is not None
