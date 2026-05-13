import os
import asyncio
from app.agents.v2_emailer import V2EmailerAgent

from dotenv import load_dotenv
load_dotenv()

# Ensure RESEND_API_KEY is present
if not os.environ.get("RESEND_API_KEY"):
    print("Warning: RESEND_API_KEY not found in environment.")

async def test_agent():
    agent = V2EmailerAgent()
    user_input = "send a test email to dsharma.workmain@gmail.com, subject: 'Omni Agent Verification', body: 'This is a test to verify the Resend migration and agent orchestration layer is working perfectly.'"
    
    print(f"--- Testing Agent Flow ---")
    print(f"Input: {user_input}\n")
    
    # We call handle_query_stream to see the logs
    for chunk_type, content in agent.handle_query_stream(user_input, action="EMAIL"):
        if chunk_type == "LOG":
            print(f"LOG: {content}")
        elif chunk_type == "TEXT":
            print(f"\nAI RESPONSE: {content}")

if __name__ == "__main__":
    asyncio.run(test_agent())
