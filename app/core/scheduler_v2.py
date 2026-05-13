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
        if not db_url:
            # Fallback to local SQLite for persistence if Supabase URL is not provided
            # This ensures the scheduler can start and persist jobs locally.
            db_url = "sqlite:///jobs.sqlite"
            print(f"[SchedulerV2] SUPABASE_DB_URL not found. Using fallback: {db_url}")
        
        jobstores = {
            'default': SQLAlchemyJobStore(url=db_url)
        }
        
        self._scheduler = AsyncIOScheduler(
            jobstores=jobstores,
            timezone="Asia/Kolkata"
        )

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
