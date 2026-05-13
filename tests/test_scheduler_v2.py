import pytest
from app.core.scheduler_v2 import SchedulerV2
import asyncio

@pytest.mark.asyncio
async def test_scheduler_singleton():
    s1 = SchedulerV2()
    s2 = SchedulerV2()
    assert s1 is s2

@pytest.mark.asyncio
async def test_scheduler_start_stop():
    scheduler_instance = SchedulerV2()
    # Should not raise error
    scheduler_instance.start()
    assert scheduler_instance.scheduler.running
    scheduler_instance.shutdown()
    assert not scheduler_instance.scheduler.running
