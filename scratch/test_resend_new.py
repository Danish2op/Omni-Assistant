import os
from app.tools.resend_tool import ResendTool
from dotenv import load_dotenv

load_dotenv()

def test_resend():
    # If key is not in .env, this will fail
    try:
        tool = ResendTool()
        print(f"--- Testing Resend Tool ---")
        print(f"Sender: {tool.sender_email}")
        
        # Replace with your actual email for testing
        test_recipient = "dsharma2_be22@thapar.edu" 
        
        success = tool.send_email(
            to=test_recipient,
            subject="Test from Resend",
            html_content="<h1>It works!</h1><p>Omni Agent is now using Resend on danis.live.</p>"
        )
        if success:
            print("✅ Resend test successful!")
    except Exception as e:
        print(f"❌ Resend test failed: {e}")

if __name__ == "__main__":
    test_resend()
