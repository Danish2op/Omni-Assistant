import asyncio
from app.tools.gmail_tool import GmailTool

def send_routine_email(to: str, subject: str, html_content: str):
    """
    Synchronous wrapper for scheduled email jobs.
    """
    gmail = GmailTool()
    print(f"[Jobs V2] Executing scheduled email to {to}...")
    try:
        success = gmail.send_email(to, subject, html_content)
        if success:
            print(f"[Jobs V2] Success: Routine email sent to {to}")
    except Exception as e:
        print(f"[Jobs V2] Failed: {e}")

def execute_intelligent_routine(to: str, routine_type: str, params: dict):
    """
    Fetches real-time data (e.g. news) and sends a personalized routine email.
    """
    from app.agents.v2_analyst import V2AnalystAgent
    from app.core.llm_v2 import MultiModelClient, AgentRole
    
    print(f"[Jobs V2] Executing intelligent routine: {routine_type} for {to}")
    
    subject = f"Omni Routine: {routine_type.title()}"
    content = ""
    
    try:
        if "news" in routine_type.lower() or "market" in routine_type.lower():
            analyst = V2AnalystAgent()
            query = params.get("query", f"Latest news on {routine_type}")
            research = analyst.handle_query(query)
            
            # Format research into a nice HTML email
            llm = MultiModelClient()
            format_prompt = f"""Format the following research data into a beautiful, mobile-friendly HTML email body.
            Routine Type: {routine_type}
            Research Data: {research}
            
            Use professional typography, clear sections, and include source links.
            Do not include <html> or <body> tags, just the inner content."""
            
            content = llm.generate(prompt=format_prompt, role=AgentRole.COMMUNICATOR)
        else:
            content = f"<p>This is your scheduled {routine_type} update.</p><p>Summary: {params.get('query', 'No details provided.')}</p>"
            
    except Exception as e:
        print(f"[Jobs V2] Content generation error: {e}")
        content = f"<p>Sorry, I had trouble generating your {routine_type} update today.</p><p>Error: {str(e)}</p>"

    gmail = GmailTool()
    try:
        success = gmail.send_email(to, subject, content)
        if success:
            print(f"[Jobs V2] Success: Intelligent routine email sent to {to}")
    except Exception as e:
        print(f"[Jobs V2] Failed: {e}")

async def async_send_routine_email(to: str, subject: str, html_content: str):
    """Async version for AsyncIOScheduler."""
    gmail = GmailTool()
    print(f"[Jobs V2] Executing scheduled email to {to}...")
    try:
        success = gmail.send_email(to, subject, html_content)
        if success:
            print(f"[Jobs V2] Success: Routine email sent to {to}")
    except Exception as e:
        print(f"[Jobs V2] Failed: {e}")
