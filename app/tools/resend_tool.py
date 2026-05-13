import os
import resend

class ResendTool:
    """
    Tool for sending emails via Resend API using a verified domain.
    """
    def __init__(self):
        self.api_key = os.environ.get("RESEND_API_KEY")
        if self.api_key:
            resend.api_key = self.api_key
        # Default sender domain from user
        self.sender_email = os.environ.get("RESEND_SENDER", "agent@danis.live")

    def send_email(self, to: str, subject: str, html_content: str, from_name: str = "Omni Agent") -> bool:
        """
        Send an email using Resend API.
        
        Args:
            to: Recipient email address.
            subject: Email subject line.
            html_content: Body of the email in HTML format.
            from_name: Name to display in the 'from' field.
            
        Returns:
            True if successful, raises exception otherwise.
        """
        if not self.api_key:
            raise ValueError("RESEND_API_KEY not found in environment variables.")

        try:
            params = {
                "from": f"{from_name} <{self.sender_email}>",
                "to": [to],
                "subject": subject,
                "html": html_content,
            }
            
            email = resend.Emails.send(params)
            print(f"[ResendTool] Email successfully sent to {to}. ID: {email.get('id')}")
            return True
        except Exception as e:
            print(f"[ResendTool] Error sending email: {type(e).__name__}: {e}")
            raise e
