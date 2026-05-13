import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

class GmailTool:
    """
    Tool for sending emails via Gmail SMTP using an App Password.
    """
    def __init__(self):
        self.email_address = os.environ.get("GMAIL_ADDRESS", "omniagentbydanishsharma@gmail.com")
        self.app_password = os.environ.get("GMAIL_APP_PASSWORD", "yplo xytp svgc wdvt")
        self.smtp_server = "smtp.gmail.com"
        self.smtp_port = 587

    def send_email(self, to: str, subject: str, html_content: str, from_name: str = "Omni") -> bool:
        """
        Send an email using Gmail SMTP.
        
        Args:
            to: Recipient email address.
            subject: Email subject line.
            html_content: Body of the email in HTML format.
            from_name: Name to display in the 'from' field.
            
        Returns:
            True if successful, raises exception otherwise.
        """
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = f"{from_name} <{self.email_address}>"
        msg["To"] = to

        # Attach HTML content
        part = MIMEText(html_content, "html")
        msg.attach(part)

        try:
            # Connect to SMTP server
            server = smtplib.SMTP(self.smtp_server, self.smtp_port)
            server.starttls()  # Secure the connection
            server.login(self.email_address, self.app_password)
            
            # Send email
            server.sendmail(self.email_address, to, msg.as_string())
            server.quit()
            return True
        except Exception as e:
            print(f"[GmailTool] Error sending email: {e}")
            raise e
