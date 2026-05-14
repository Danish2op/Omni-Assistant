import asyncio
from app.tools.resend_tool import ResendTool

def send_routine_email(to: str, subject: str, html_content: str):
    """
    Synchronous wrapper for scheduled email jobs.
    """
    resend = ResendTool()
    print(f"[Jobs V2] Executing scheduled email to {to}...")
    try:
        success = resend.send_email(to, subject, html_content)
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
        # For intelligent routines, we usually want to research the topic first
        # unless specifically instructed otherwise.
        analyst = V2AnalystAgent()
        
        # Determine the best query: explicit query param > routine_type context
        query = params.get("query")
        if not query:
            query = f"Latest updates and information about {routine_type}"
            
        print(f"[Jobs V2] Fetching research for: {query}")
        research = analyst.handle_query(query)
        
        # Format research into a nice HTML email
        llm = MultiModelClient()
        format_prompt = f"""Format the following research data into a beautiful, mobile-friendly HTML email body.
        Routine Type: {routine_type}
        Research Data: {research}
        
        Use professional typography, clear sections, vibrant modern design, and include source links.
        Do not include <html> or <body> tags, just the inner content."""
        
        content = llm.generate(prompt=format_prompt, role=AgentRole.COMMUNICATOR)
    except Exception as e:
        print(f"[Jobs V2] Content generation error: {e}")
        content = f"<p>Sorry, I had trouble generating your {routine_type} update today.</p><p>Error: {str(e)}</p>"

    resend = ResendTool()
    try:
        success = resend.send_email(to, subject, content)
        if success:
            print(f"[Jobs V2] Success: Intelligent routine email sent to {to}")
    except Exception as e:
        print(f"[Jobs V2] Failed: {e}")

async def async_send_routine_email(to: str, subject: str, html_content: str):
    """Async version for AsyncIOScheduler."""
    resend = ResendTool()
    print(f"[Jobs V2] Executing scheduled email to {to}...")
    try:
        success = resend.send_email(to, subject, html_content)
        if success:
            print(f"[Jobs V2] Success: Routine email sent to {to}")
    except Exception as e:
        print(f"[Jobs V2] Failed: {e}")

def sync_routines_on_startup():
    """Sync routines from Supabase to the APScheduler."""
    try:
        from app.core.database_v2 import SupabaseV2Client
        from app.core.scheduler_v2 import scheduler_instance
        import re
        
        print("[Jobs V2] Starting routine reconciliation...")
        db = SupabaseV2Client()
        routines = db.get_data("routines", {})
        count = 0
        
        for routine in (routines or []):
            try:
                if routine.get("status") == "active":
                    recipient_email = routine.get("recipient_email")
                    if not recipient_email: continue
                    
                    time_str = routine.get("parameters", {}).get("schedule_time", "9 AM")
                    time_match = re.search(r'(\d{1,2}(?::\d{2})?\s*(?:am|pm)?)', time_str, re.IGNORECASE)
                    
                    if time_match:
                        clean_time = time_match.group(1).upper()
                        is_pm = "PM" in clean_time
                        is_am = "AM" in clean_time
                        time_nums = clean_time.replace("AM", "").replace("PM", "").strip()
                        
                        if ":" in time_nums:
                            hour, minute = map(int, time_nums.split(":"))
                        else:
                            hour = int(time_nums)
                            minute = 0
                            
                        if is_pm and hour < 12: hour += 12
                        elif is_am and hour == 12: hour = 0
                        
                        trigger_args = {'hour': hour, 'minute': minute}
                        if routine.get("frequency") == 'weekly':
                            trigger_args['day_of_week'] = routine.get("parameters", {}).get("day_of_week", "mon")
                        
                        routine_type = routine.get("type", "Generic Routine")
                        query = routine.get("parameters", {}).get("query", routine_type)
                        
                        job_id = f"routine_{routine_type}_{recipient_email}".replace(" ", "_")
                        
                        scheduler_instance.scheduler.add_job(
                            execute_intelligent_routine,
                            'cron',
                            **trigger_args,
                            args=[recipient_email, routine_type, {"query": query}],
                            id=job_id,
                            replace_existing=True
                        )
                        count += 1
                        print(f"[Jobs V2] Rescheduled routine: {job_id} at {hour:02d}:{minute:02d}")
            except Exception as item_err:
                print(f"[Jobs V2] Skipping routine ID {routine.get('id')}: {item_err}")
                    
        print(f"[Jobs V2] Synced {count} active routines from database.")
    except Exception as e:
        print(f"[Jobs V2] ⚠️ Failed to sync routines: {e}")
