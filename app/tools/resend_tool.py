import os
import requests
from typing import Optional

class ResendTool:
    """
    Tool for sending emails via Resend.com API.
    """
    def __init__(self):
        # We prefer environment variable, fallback to hardcoded if necessary for internal use
        self.api_key = os.environ.get("RESEND_API_KEY", "re_MwECAreo_44PyxU5DNN5TMGbbq3VnCWbM")
        self.base_url = "https://api.resend.com/emails"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

    def send_email(self, to: str, subject: str, html_content: str, from_name: str = "Omni") -> requests.Response:
        """
        Send an email using Resend API.
        
        Args:
            to: Recipient email address.
            subject: Email subject line.
            html_content: Body of the email in HTML format.
            from_name: Name to display in the 'from' field.
        """
        payload = {
            "from": f"{from_name} <onboarding@resend.dev>",
            "to": [to],
            "subject": subject,
            "html": html_content
        }
        
        try:
            response = requests.post(
                self.base_url,
                headers=self.headers,
                json=payload,
                timeout=15
            )
            return response
        except Exception as e:
            print(f"[ResendTool] Error sending email: {e}")
            raise e
