import json
import os
from typing import List, Optional, Dict, Any
from app.core.llm_v2 import MultiModelClient, AgentRole
from app.core.database_v2 import SupabaseV2Client
from app.tools.resend_tool import ResendTool
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
        self.resend = ResendTool()
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
        # We combine both to ensure we have the refined context AND the raw technical details
        combined_context = f"Refined Task: {query}\nRaw Input: {raw_user_input or ''}"
        extraction_prompt = f"""Extract email details from this context:
        ---
        {combined_context}
        ---
        Output ONLY valid JSON: {{"recipient_name": "string", "subject": "string", "body_intent": "string"}}
        If any field is missing, use null."""
        
        try:
            raw_extract = self.llm.generate(prompt=extraction_prompt, role=self.role, temperature=0.1)
            details_str = self._extract_json(raw_extract)
            if not details_str:
                yield "TEXT", f"⚠️ The brain is a bit foggy right now (LLM failed to produce structured data). Please try again in a moment.\n\nRaw response: {raw_extract[:100]}..."
                return
            
            details = json.loads(details_str)
            
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
            success = self.resend.send_email(
                to=email_addr,
                subject=details.get("subject") or "Message from Omni",
                html_content=html_body
            )
            
            if success:
                yield "TEXT", f"✅ Email sent successfully to {name} ({email_addr})."
            else:
                yield "TEXT", f"❌ Failed to send email via API."

        except Exception as e:
            yield "TEXT", f"⚠️ Error processing email request: {str(e)}"

    def _handle_reminder(self, query: str) -> str:
        """Schedule a one-off reminder email."""
        # --- Layer 1: Heuristic Extraction (Bypass LLM) ---
        heuristics = self._heuristic_extract_reminder(query)
        details = None
        if heuristics:
            print(f"[Communicator] Heuristic reminder match: {heuristics['message']}")
            details = heuristics
        else:
            # --- Layer 2: LLM Extraction ---
            extraction_prompt = f"""Extract reminder details from: "{query}"
            Output ONLY valid JSON: {{"message": "string", "wait_minutes": int, "absolute_time": "ISO format string or null"}}
            If it's relative (e.g. 'in 5 minutes'), use wait_minutes. If absolute, use absolute_time.
            Current time (IST): {datetime.now().isoformat()}"""
            
            try:
                raw_extract = self.llm.generate(prompt=extraction_prompt, role=self.role, temperature=0.1)
                details_str = self._extract_json(raw_extract)
                if details_str:
                    details = json.loads(details_str)
            except Exception as e:
                print(f"[Communicator] LLM Reminder Extraction failed: {e}")

        if not details:
            return "I'm having trouble understanding the time and message for the reminder. Could you try saying it differently (e.g., 'remind me in 5 minutes')?"
        
        try:
            message = details.get("message") or query
            wait_min = details.get("wait_minutes")
            abs_time_str = details.get("absolute_time")
            
            # Resolve user email
            user_email = os.environ.get("USER_EMAIL") or os.environ.get("GMAIL_ADDRESS")
            if not user_email:
                self_contact = self.get_contact("self")
                if self_contact:
                    user_email = self_contact.get("email")
            
            if not user_email:
                return "⚠️ I don't know your email address! Please set USER_EMAIL in your .env or add a 'self' contact with your email."

            # Calculate run time
            run_at = None
            log_msg = ""
            
            if wait_min:
                run_at = datetime.now() + timedelta(minutes=int(wait_min))
                log_msg = f"in {wait_min} minutes"
            elif abs_time_str:
                try:
                    # ISO format parsing
                    run_at = datetime.fromisoformat(abs_time_str.replace("Z", "+00:00"))
                    log_msg = f"at {abs_time_str}"
                except:
                    # Fallback for simple HH:MM if LLM returned it
                    return f"I couldn't understand the timestamp '{abs_time_str}'. Try 'in 10 minutes'."

            if run_at:
                # Check persistence status
                db_url = os.environ.get("SUPABASE_DB_URL")
                storage_type = "persistent" if db_url else "local (non-persistent)"
                
                from app.core.jobs_v2 import async_send_routine_email
                try:
                    scheduler_instance.scheduler.add_job(
                        async_send_routine_email,
                        'date',
                        run_date=run_at,
                        args=[user_email, "Omni Reminder", f"<h3>Reminder</h3><p>{message}</p>"],
                        id=f"remind_{int(run_at.timestamp())}",
                        replace_existing=True
                    )
                    return f"✅ Set a {storage_type} reminder for {log_msg} to {message}."
                except Exception as sched_err:
                    print(f"[Communicator] Scheduler Error: {sched_err}")
                    return f"⚠️ I couldn't schedule the reminder: {sched_err}"
            
            return "I couldn't quite figure out when to remind you. Could you be more specific (e.g. 'in 10 minutes')?"

        except Exception as e:
            return f"⚠️ Error scheduling reminder: {str(e)}"

    def _heuristic_extract_reminder(self, query: str) -> Optional[dict]:
        """Regex-based extraction for simple 'remind me in X minutes' patterns."""
        import re
        text = query.lower()
        
        # Pattern: remind me in 5 minutes to turn off light
        # Pattern: remind me in 5 mins to turn off light
        match = re.search(r'remind me in (\d+)\s*(min|minute|mins|minutes|hr|hour|hrs|hours)', text)
        if match:
            amount = int(match.group(1))
            unit = match.group(2)
            
            wait_minutes = amount
            if 'hr' in unit or 'hour' in unit:
                wait_minutes = amount * 60
            
            # Extract message: everything after 'to ' or 'about '
            msg_match = re.search(r'(?:to|about|that)\s+(.*)', text)
            message = msg_match.group(1).strip() if msg_match else query
            
            return {
                "message": message,
                "wait_minutes": wait_minutes,
                "absolute_time": None
            }
        
        # Pattern: remind me at 11:05 pm to X
        abs_match = re.search(r'remind me at (\d{1,2}(?::\d{2})?\s*(?:am|pm)?)', text)
        if not abs_match:
            # Check for just 'at 11:05 pm'
            abs_match = re.search(r'at (\d{1,2}(?::\d{2})?\s*(?:am|pm)?)', text)

        if abs_match:
            time_str = abs_match.group(1).upper()
            msg_match = re.search(r'(?:to|about|that)\s+(.*)', text)
            message = msg_match.group(1).strip() if msg_match else query
            
            try:
                clean_time = time_str.strip()
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
                
                now = datetime.now()
                target = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
                if target < now: # If time has passed today, assume tomorrow
                    target += timedelta(days=1)
                
                return {
                    "message": message,
                    "wait_minutes": None,
                    "absolute_time": target.isoformat()
                }
            except:
                pass
                
        return None

    def _schedule_reminder_job(self, to: str, subject: str, html_content: str, wait_minutes: int):
        """Helper to schedule the reminder job via APScheduler."""
        from app.core.jobs_v2 import async_send_routine_email
        from app.core.scheduler_v2 import scheduler_instance
        
        run_at = datetime.now() + timedelta(minutes=wait_minutes)
        scheduler_instance.scheduler.add_job(
            async_send_routine_email,
            'date',
            run_date=run_at,
            args=[to, subject, html_content]
        )
        print(f"[Communicator] Scheduled reminder for {to} at {run_at}")


    def _handle_schedule(self, query: str) -> str:
        """Schedule a recurring routine (e.g., daily news, weekly check-in)."""
        # --- Layer 1: Heuristic Extraction (Bypass LLM for common patterns) ---
        heuristics = self._heuristic_extract_schedule(query)
        
        details = None
        if heuristics:
            print(f"[Communicator] Heuristic extraction success for routine: {heuristics['routine_type']}")
            details = heuristics
        else:
            # --- Layer 2: LLM Extraction (Dynamic reasoning) ---
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
                details_str = self._extract_json(raw_extract)
                if details_str:
                    details = json.loads(details_str)
            except Exception as e:
                print(f"[Communicator] LLM Extraction failed: {e}")

        if not details:
            return "I couldn't structure your routine correctly. Please specify the time and frequency (e.g., 'every day at 9 AM')."
        
        try:
            routine_type = details.get("routine_type")
            frequency = details.get("frequency")
            time_str = details.get("time")
            day_of_week = details.get("day_of_week")
            name = details.get("recipient_name")

            if not all([routine_type, frequency, time_str]):
                return "I need to know what to schedule, how often (daily/weekly), and at what time (e.g. 9:00 AM)."

            # Resolve contact
            recipient_email = os.environ.get("USER_EMAIL")
            if not recipient_email:
                recipient_email = os.environ.get("GMAIL_ADDRESS")

            if not recipient_email:
                # Check for "self" contact
                self_contact = self.get_contact("self")
                if self_contact:
                    recipient_email = self_contact.get("email")
            
            if name and name.lower() not in ["me", "self"]:
                contact = self.get_contact(name)
                if contact:
                    recipient_email = contact.get("email")
                else:
                    return f"I couldn't find '{name}' in your contacts. I'll need their email to schedule this routine."
            
            if not recipient_email:
                return "⚠️ I don't know your email address! Please set USER_EMAIL in your environment (e.g., Render settings) or add a 'self' contact with your email."

            # Parse time
            try:
                # Handle HH:MM AM/PM or just HH:MM
                clean_time = time_str.upper().strip()
                is_pm = "PM" in clean_time
                is_am = "AM" in clean_time
                time_nums = clean_time.replace("AM", "").replace("PM", "").strip()
                
                if ":" in time_nums:
                    hour, minute = map(int, time_nums.split(":"))
                else:
                    hour = int(time_nums)
                    minute = 0
                
                if is_pm and hour < 12:
                    hour += 12
                elif is_am and hour == 12:
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

    def _heuristic_extract_schedule(self, query: str) -> Optional[dict]:
        """Regex-based extraction for common routine patterns."""
        import re
        text = query.lower()
        
        # 1. Frequency and Day of Week
        frequency = "daily"
        day_of_week = None
        days_map = {
            "monday": "mon", "tuesday": "tue", "wednesday": "wed", 
            "thursday": "thu", "friday": "fri", "saturday": "sat", "sunday": "sun",
            "mon": "mon", "tue": "tue", "wed": "wed", "thu": "thu", "fri": "fri", "sat": "sat", "sun": "sun"
        }
        
        for day, code in days_map.items():
            if f"every {day}" in text or f"on {day}" in text:
                frequency = "weekly"
                day_of_week = code
                break
        
        if frequency == "daily":
            if "weekly" in text or "every week" in text:
                frequency = "weekly"
                day_of_week = "mon" # Default
            elif "monthly" in text or "every month" in text:
                frequency = "monthly"
            elif "every day" in text or "everyday" in text or "daily" in text:
                frequency = "daily"
            
        # 2. Time (e.g., 9 am, 9:30 PM, at 10:00)
        time_match = re.search(r'(\d{1,2}(?::\d{2})?\s*(?:am|pm)?)', text, re.IGNORECASE)
        if not time_match:
            # Fallback for "morning", "night", etc.
            if "morning" in text:
                time_str = "9:00 AM"
            elif "night" in text:
                time_str = "10:00 PM"
            elif "evening" in text:
                time_str = "6:00 PM"
            elif "afternoon" in text:
                time_str = "2:00 PM"
            else:
                return None
        else:
            time_str = time_match.group(1).upper()
        
        # 3. Routine Type
        routine_type = query
        words_to_strip = [
            "every day", "everyday", "daily", "weekly", "monthly", "schedule", 
            "routine", "at", "set a", "on", "every"
        ]
        words_to_strip.extend(days_map.keys())
        
        for w in words_to_strip:
            routine_type = re.sub(rf'\b{w}\b', '', routine_type, flags=re.IGNORECASE)
        
        if time_match:
            routine_type = routine_type.replace(time_match.group(1), "")
            
        routine_type = " ".join(routine_type.split()).strip()
        
        if not routine_type:
            routine_type = "Generic Routine"
            
        return {
            "routine_type": routine_type,
            "frequency": frequency,
            "time": time_str,
            "day_of_week": day_of_week,
            "recipient_name": "me" if "me" in text or "my" in text else None
        }

    def _chat(self, query: str) -> str:
        """General communication response."""
        system_msg = "You are Omni's Communicator. You help the user with emails, reminders, and scheduling. Be professional and helpful."
        return self.llm.generate(prompt=query, system_instruction=system_msg, role=self.role)

    def _extract_json(self, raw: str) -> Optional[str]:
        """Robust JSON extraction from LLM output."""
        cleaned = raw.strip()
        # Find outermost JSON braces
        start = cleaned.find('{')
        end = cleaned.rfind('}')
        if start != -1 and end != -1:
            return cleaned[start:end + 1]
        return None

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
        """Save a recurring routine to Supabase.
        
        Table schema: id, type, parameters (jsonb), frequency, recipient_email,
                       start_date, end_date, next_run_at, status, created_at (auto).
        """
        data = {
            "recipient_email": contact_email,
            "type": routine_type,
            "frequency": frequency,
            "parameters": {**(content_params or {}), "schedule_time": schedule_time},
            "status": "active",
        }
        result = self.db.save_data("routines", data)
        return result is not None

