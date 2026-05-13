import json
import os
from typing import List, Optional, Dict, Any
from app.core.llm_v2 import MultiModelClient, AgentRole
from app.core.database_v2 import SupabaseV2Client
from app.tools.gmail_tool import GmailTool
from app.core.scheduler_v2 import scheduler_instance
from datetime import datetime, timedelta

class V2EmailerAgent:
    """
    COMMUNICATOR Agent: Handles emails, reminders, and recurring routines.
    Integrates with Resend for delivery and Supabase for contact/routine storage.
    """

    def __init__(self):
        self.llm = MultiModelClient()
        self.db = SupabaseV2Client()
        self.gmail = GmailTool()
        self.role = AgentRole.COMMUNICATOR

    def handle_query(
        self,
        user_input: str,
        action: str = None,
        keywords: list = None,
        processed_query: str = None,
    ) -> str:
        """
        Main entry point for communicator tasks (Sync version).
        Returns the final string result.
        """
        result = []
        for chunk_type, content in self.handle_query_stream(user_input, action, keywords, processed_query):
            if chunk_type == "TEXT":
                result.append(content)
        return "".join(result)

    def handle_query_stream(
        self,
        user_input: str,
        action: str = None,
        keywords: list = None,
        processed_query: str = None,
    ):
        """
        Generator version of handle_query.
        Yields (type, content) pairs. types: 'LOG', 'TEXT'
        """
        effective_query = processed_query if processed_query else user_input
        
        if action == "EMAIL":
            yield from self._handle_email(effective_query, user_input)
        elif action == "REMIND":
            yield "TEXT", self._handle_reminder(effective_query)
        elif action == "SCHEDULE":
            yield "TEXT", self._handle_schedule(effective_query)
        else:
            yield "TEXT", self._chat(effective_query)

    def _handle_email(self, query: str, raw_user_input: str = None):
        """Resolve contact, compose email via LLM, and send with progress logs."""
        yield "LOG", "🔍 Analyzing email request..."
        
        # 1. Extract recipient and intent from query
        # Use raw_user_input if available for better extraction of technical details
        search_query = raw_user_input if raw_user_input else query
        extraction_prompt = f"""Extract email details from this query: "{search_query}"
        Output ONLY valid JSON: {{"recipient_name": "string", "subject": "string", "body_intent": "string"}}
        If any field is missing, use null."""
        
        try:
            raw_extract = self.llm.generate(prompt=extraction_prompt, role=self.role, temperature=0.1)
            # Find JSON in potentially messy output
            start = raw_extract.find('{')
            end = raw_extract.rfind('}')
            details = json.loads(raw_extract[start:end+1])
            
            name = details.get("recipient_name")
            if not name:
                yield "TEXT", "I couldn't identify who you want to email. Could you specify the name?"
                return

            email_addr = None
            
            # Check if extracted name is actually an email
            if name and "@" in name and "." in name:
                email_addr = name.strip()
                yield "LOG", f"📧 Using direct email address: {email_addr}"
            else:
                yield "LOG", f"👤 Resolving contact for '{name}'..."
                # 2. Resolve Contact from Database
                contact = self.get_contact(name)
                if contact:
                    email_addr = contact.get("email")
                else:
                    # Final fallback: Look for ANY email address in the raw query OR refined query
                    import re
                    all_text = f"{query} {raw_user_input or ''}"
                    emails = re.findall(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', all_text)
                    if emails:
                        email_addr = emails[0]
                        yield "LOG", f"🔍 Detected email in message: {email_addr}"
                    else:
                        yield "TEXT", f"I don't have an email for '{name}' in my contacts. What is their email address? I'll save it for next time."
                        return

            yield "LOG", f"📝 Drafting professional email for {email_addr}..."
            # 3. Compose Email Body via LLM
            composition_prompt = f"""Compose a professional email. 
            Recipient: {name}
            Subject: {details.get("subject") or "Message from Omni"}
            Intent: {details.get("body_intent") or query}
            
            Format as HTML. Use 'Omni' as the signature.
            Output ONLY the HTML body."""
            
            html_body = self.llm.generate(prompt=composition_prompt, role=self.role)
            
            yield "LOG", f"📧 Sending email to {email_addr}..."
            # 4. Send
            success = self.gmail.send_email(
                to=email_addr,
                subject=details.get("subject") or "Message from Omni",
                html_content=html_body
            )
            
            if success:
                yield "TEXT", f"✅ Email sent successfully to {name} ({email_addr})."
            else:
                yield "TEXT", f"❌ Failed to send email via SMTP."

        except Exception as e:
            yield "TEXT", f"⚠️ Error processing email request: {str(e)}"

    def _handle_reminder(self, query: str) -> str:
        """Schedule a one-off reminder email."""
        extraction_prompt = f"""Extract reminder details from: "{query}"
        Output ONLY valid JSON: {{"message": "string", "wait_minutes": int, "absolute_time": "ISO format string or null"}}
        If it's relative (e.g. 'in 5 minutes'), use wait_minutes. If absolute, use absolute_time.
        Current time (IST): {datetime.now().isoformat()}"""
        
        try:
            raw_extract = self.llm.generate(prompt=extraction_prompt, role=self.role, temperature=0.1)
            start = raw_extract.find('{')
            end = raw_extract.rfind('}')
            details = json.loads(raw_extract[start:end+1])
            
            message = details.get("message") or query
            wait_min = details.get("wait_minutes")
            
            from app.core.jobs_v2 import async_send_routine_email
            
            # Default to user's email if no recipient specified for reminder
            user_email = os.environ.get("USER_EMAIL", "danishsharma@example.com")
            self_contact = self.get_contact("self")
            if self_contact:
                user_email = self_contact.get("email")
            
            if wait_min:
                scheduler_instance.scheduler.add_job(
                    async_send_routine_email,
                    'date',
                    run_date=datetime.now() + timedelta(minutes=wait_min),
                    args=[user_email, "Omni Reminder", f"<p>Reminder: {message}</p>"]
                )
                return f"✅ Set a reminder for {wait_min} minutes from now."
            
            return "I couldn't quite figure out when to remind you. Could you be more specific (e.g. 'in 10 minutes')?"

        except Exception as e:
            return f"⚠️ Error scheduling reminder: {str(e)}"

    def _handle_schedule(self, query: str) -> str:
        """Schedule a recurring routine (e.g., daily news, weekly check-in)."""
        extraction_prompt = f"""Extract recurring routine details from: "{query}"
        Output ONLY valid JSON: {{
            "routine_type": "string", 
            "frequency": "daily|weekly|monthly", 
            "time": "HH:MM", 
            "day_of_week": "mon|tue|wed|thu|fri|sat|sun|null",
            "recipient_name": "string or null"
        }}
        Current time (IST): {datetime.now().isoformat()}"""
        
        try:
            raw_extract = self.llm.generate(prompt=extraction_prompt, role=self.role, temperature=0.1)
            start = raw_extract.find('{')
            end = raw_extract.rfind('}')
            details = json.loads(raw_extract[start:end+1])
            
            routine_type = details.get("routine_type")
            frequency = details.get("frequency")
            time_str = details.get("time")
            day_of_week = details.get("day_of_week")
            name = details.get("recipient_name")

            if not all([routine_type, frequency, time_str]):
                return "I need to know what to schedule, how often (daily/weekly), and at what time (e.g. 9:00 AM)."

            # Resolve contact
            recipient_email = os.environ.get("USER_EMAIL", "danishsharma@example.com")
            if name and name.lower() not in ["me", "self"]:
                contact = self.get_contact(name)
                if contact:
                    recipient_email = contact.get("email")
                else:
                    return f"I couldn't find '{name}' in your contacts. I'll need their email to schedule this routine."
            else:
                # Check for "self" contact
                self_contact = self.get_contact("self")
                if self_contact:
                    recipient_email = self_contact.get("email")

            # Parse time
            try:
                hour, minute = map(int, time_str.replace("AM", "").replace("PM", "").strip().split(":"))
                if "PM" in time_str.upper() and hour < 12:
                    hour += 12
                elif "AM" in time_str.upper() and hour == 12:
                    hour = 0
            except:
                return f"I couldn't understand the time '{time_str}'. Please use HH:MM format."

            # Store in Supabase
            success = self.create_routine(
                contact_email=recipient_email,
                routine_type=routine_type,
                frequency=frequency,
                schedule_time=time_str,
                content_params={"query": query}
            )

            if not success:
                return "⚠️ Failed to save the routine to the database. Is Supabase paused?"

            # Schedule the job
            from app.core.jobs_v2 import execute_intelligent_routine
            
            # Simplified trigger logic
            trigger_args = {'hour': hour, 'minute': minute}
            if frequency == 'weekly':
                trigger_args['day_of_week'] = day_of_week or 'mon'
            
            job = scheduler_instance.scheduler.add_job(
                execute_intelligent_routine,
                'cron',
                **trigger_args,
                args=[recipient_email, routine_type, {"query": query}],
                id=f"routine_{routine_type}_{recipient_email}".replace(" ", "_"),
                replace_existing=True
            )

            return f"✅ Scheduled a {frequency} {routine_type} for {time_str} ({day_of_week or 'every day'}) to {recipient_email}."

        except Exception as e:
            return f"⚠️ Error setting up routine: {str(e)}"

    def _chat(self, query: str) -> str:
        """General communication response."""
        system_msg = "You are Omni's Communicator. You help the user with emails, reminders, and scheduling. Be professional and helpful."
        return self.llm.generate(prompt=query, system_instruction=system_msg, role=self.role)

    # ---- Contact Management ----

    def get_contact(self, name: str) -> Optional[dict]:
        """Fetch contact by name from Supabase. Handles 'me' or 'self'."""
        if name.lower() in ["me", "self"]:
            # Try to find a contact with tag 'self' or specifically named 'Self'
            results = self.db.search_data("contacts", "name", ["Self"], limit=1)
            if not results:
                # Fallback search by metadata tag
                results = self.db.get_data("contacts", {"limit": 1}) # Simple fallback for now
            return results[0] if results else None

        results = self.db.search_data("contacts", "name", [name], limit=1)
        return results[0] if results else None

    def save_contact(self, name: str, email: str, metadata: dict = None) -> bool:
        """Save new contact to Supabase."""
        data = {"name": name, "email": email, "metadata": metadata or {}}
        result = self.db.save_data("contacts", data)
        return result is not None

    # ---- Routine Management ----

    def create_routine(self, contact_email: str, routine_type: str, frequency: str, schedule_time: str, content_params: dict = None) -> bool:
        """Save a recurring routine to Supabase."""
        data = {
            "contact_email": contact_email,
            "type": routine_type,
            "frequency": frequency,
            "time": schedule_time,
            "content_params": content_params or {},
            "status": "active",
            "created_at": datetime.utcnow().isoformat()
        }
        result = self.db.save_data("routines", data)
        return result is not None
