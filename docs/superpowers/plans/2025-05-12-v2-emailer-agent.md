V2 Emailer Agent Implementation Plan
For AI AGENTS: REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

Goal: Build a robust, persistent Emailer Agent (COMMUNICATOR) for Omni-Agent V2 that handles reminders, direct emails, web-info relay, and recurring routines using Resend and Supabase.

Architecture: A standalone V2EmailerAgent that acts as a "Communicator" expert. It integrates a centralized APScheduler for persistence, a ResendTool for delivery, and internal agent access (Analyst, Generalist) to fetch content before emailing.

Tech Stack: Python, Resend SDK, APScheduler, Supabase (PostgreSQL), Omni-Agent V2 Framework.

Task 1: Environment & Roles
Files:

Modify: .env (Add RESEND_API_KEY)
Modify: app/core/llm_v2.py:18-48
Step 1: Update AgentRole Enum and Model Registry Add COMMUNICATOR role to AgentRole and assign llama-3.3-70b-instruct:free as its primary model in MODEL_REGISTRY.

Step 2: Commit git commit -m "feat: add COMMUNICATOR role to model registry"

Task 2: Email Delivery Tool (Resend)
Files:

Create: app/tools/resend_tool.py
Step 1: Implement ResendTool Create a class that wraps the Resend API to send formatted emails.

python
import os
import requests
class ResendTool:
    def __init__(self):
        self.api_key = "re_MwECAreo_44PyxU5DNN5TMGbbq3VnCWbM"
        self.base_url = "https://api.resend.com/emails"
        self.headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
    def send_email(self, to: str, subject: str, html_content: str, from_name: str = "Omni"):
        payload = {
            "from": f"{from_name} <onboarding@resend.dev>", # Replace with verified domain if available
            "to": [to],
            "subject": subject,
            "html": html_content
        }
        return requests.post(self.base_url, headers=self.headers, json=payload)
Step 2: Commit git commit -m "feat: implement ResendTool for email delivery"

Task 3: Centralized V2 Scheduler
Files:

Create: app/core/scheduler_v2.py
Modify: app/tools/news_api.py (Remove local scheduler, import global one)
Step 1: Implement Global Async Scheduler Create a singleton scheduler that handles both the news cache and the new email routines.

python
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
# Database URL for persistence
DB_URL = os.environ.get("SUPABASE_DB_URL") 
scheduler = AsyncIOScheduler(
    jobstores={'default': SQLAlchemyJobStore(url=DB_URL)},
    timezone="Asia/Kolkata"
)
Step 2: Commit git commit -m "feat: implement centralized persistent scheduler"

Task 4: V2 Emailer Agent Core
Files:

Create: app/agents/v2_emailer.py
Modify: app/agents/v2_router.py (Update intent classification)
Step 1: Implement V2EmailerAgent This agent will:

Resolve contacts from the contacts table.
If name is found but no email, use it. If not found, ask user and save.
Format emails with the "Omni Side" persona.
Schedule jobs using scheduler_v2.
Step 2: Update Router Add COMMUNICATOR to the Intent literal and update the system prompt to route email/reminder requests here.

Step 3: Commit git commit -m "feat: implement V2EmailerAgent and route intents"

Task 5: Routine & Contact Management Tools
Files:

Modify: app/agents/v2_emailer.py (Add tool methods)
Step 1: Add Contact/Routine Tools Implement save_contact, get_contact, and create_routine methods that interact with Supabase.

Step 2: Commit git commit -m "feat: add contact and routine persistence tools"

Task 6: Final Integration & UI Update
Files:

Modify: main.py (Initialize scheduler)
Modify: frontend/src/types/chat.ts (Ensure UI handles Communicator role)
Step 1: Start Scheduler in Main Ensure scheduler.start() is called in the FastAPI startup event.

Step 2: Commit git commit -m "feat: finalize Emailer integration"