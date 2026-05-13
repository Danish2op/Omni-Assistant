import os
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from typing import Optional

class SchedulerV2:
    _instance: Optional['SchedulerV2'] = None
    _scheduler: Optional[AsyncIOScheduler] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(SchedulerV2, cls).__new__(cls)
            cls._instance._init_scheduler()
        return cls._instance

    def _init_scheduler(self):
        # Database URL for persistence
        # Priority: SUPABASE_DB_URL -> Local SQLite
        db_url = os.environ.get("SUPABASE_DB_URL")
        
        # Check if we are running in a hosted environment (Render/Vercel)
        is_hosted = os.environ.get("RENDER") or os.environ.get("VERCEL")
        
        if not db_url:
            if is_hosted:
                # CRITICAL: Do NOT fall back to SQLite on Render/Vercel as it is transient.
                # This will alert the user in the logs that their configuration is broken.
                print("!!! [SchedulerV2] WARNING: SUPABASE_DB_URL is missing in a HOSTED environment.")
                print("!!! Reminders will NOT persist across restarts. Please set SUPABASE_DB_URL in Render/Vercel settings.")
                db_url = "sqlite:///jobs.sqlite" # Temporary fallback to allow startup, but with loud warning
            else:
                db_url = "sqlite:///jobs.sqlite"
                print(f"[SchedulerV2] Local environment detected. Using SQLite: {db_url}")
        else:
            # Mask sensitive info for logging
            masked_url = db_url.split("@")[-1] if "@" in db_url else "Supabase DB"
            print(f"[SchedulerV2] Persistence enabled via: {masked_url}")
        
        try:
            jobstores = {
                'default': SQLAlchemyJobStore(url=db_url)
            }
            
            self._scheduler = AsyncIOScheduler(
                jobstores=jobstores,
                timezone="Asia/Kolkata"
            )
        except Exception as e:
            print(f"!!! [SchedulerV2] FAILED TO INITIALIZE JOBSTORE: {e}")
            # Fallback to memory-only if DB fails entirely
            self._scheduler = AsyncIOScheduler(timezone="Asia/Kolkata")
            print("[SchedulerV2] Falling back to memory-only scheduler (NON-PERSISTENT).")


    @property
    def scheduler(self) -> AsyncIOScheduler:
        return self._scheduler

    def start(self):
        if not self._scheduler.running:
            self._scheduler.start()
            print("[SchedulerV2] Persistent scheduler started.")

    def shutdown(self):
        if self._scheduler.running:
            self._scheduler.shutdown()
            print("[SchedulerV2] Persistent scheduler shut down.")

# Global instance
scheduler_instance = SchedulerV2()
