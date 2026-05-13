import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

class GmailTool:
    """
    Tool for sending emails via Gmail SMTP using an App Password.
    """
    def __init__(self):
        self.email_address = os.environ.get("GMAIL_ADDRESS")
        self.app_password = os.environ.get("GMAIL_APP_PASSWORD")
        self.smtp_server = "smtp.gmail.com"
        self.smtp_port = 465  # Switched to SSL port for better cloud compatibility

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
            import socket
            # Force IPv4 by resolving the hostname manually
            addr_info = socket.getaddrinfo(self.smtp_server, self.smtp_port, socket.AF_INET, socket.SOCK_STREAM)
            ipv4_addr = addr_info[0][4][0]
            print(f"[GmailTool] Resolved {self.smtp_server} to IPv4: {ipv4_addr}")
            
            # Connect to SMTP server using SSL on IPv4
            server = smtplib.SMTP_SSL(ipv4_addr, self.smtp_port, timeout=15)
            server.login(self.email_address, self.app_password)
            
            # Send email
            server.sendmail(self.email_address, to, msg.as_string())
            server.quit()
            print(f"[GmailTool] Email successfully sent to {to}")
            return True
        except Exception as e:
            print(f"[GmailTool] Detailed error sending email: {type(e).__name__}: {e}")
            raise e
#1b557d30-3bcb-47f2-9a5f-b4d127410cf6