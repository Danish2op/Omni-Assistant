
import json
import re

def mock_handle_email(query, recipient_name):
    name = recipient_name
    email_addr = None
    
    print(f"Testing with name: '{name}'")
    # 85: Check if extracted name is actually an email
    if "@" in name and "." in name:
        email_addr = name
        print(f"LOG: 📧 Using direct email address: {email_addr}")
    else:
        print(f"LOG: 👤 Resolving contact for '{name}'...")
        # 2. Resolve Contact from Database (Mocked as None)
        contact = None 
        if contact:
            email_addr = contact.get("email")
        else:
            # Final fallback: Look for ANY email address in the raw query
            emails = re.findall(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', query)
            if emails:
                email_addr = emails[0]
                print(f"LOG: 🔍 Detected email in message: {email_addr}")
            else:
                print(f"TEXT: I don't have an email for '{name}' in my contacts. What is their email address? I'll save it for next time.")
                return

    print(f"Final resolved email: {email_addr}")

print("--- Test 1: Direct Email in Name ---")
mock_handle_email("send email to test@example.com", "test@example.com")

print("\n--- Test 2: Name extracted, Email in Query ---")
mock_handle_email("send email to paryag.sahni@thefuture.university", "paryag.sahni")

print("\n--- Test 3: The user's specific case ---")
mock_handle_email("the email is paryag.sahni@thefuture.university, on behalf of me just remind him to work hard", "paryag.sahni@thefuture.university")
