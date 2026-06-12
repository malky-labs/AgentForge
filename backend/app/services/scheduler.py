import asyncio
import logging
from datetime import datetime, timedelta
from typing import Optional
from sqlmodel import Session, select
from app.core.database import engine
from app.models.schemas import ScheduledJob, JobRun, Workflow, WorkflowExecution, Agent
from app.services.workflow_runner import workflow_runner
from app.services.runtime_engine import runtime_engine

logger = logging.getLogger("AgentForge.Scheduler")

def match_cron_field(val: int, pattern: str) -> bool:
    if pattern == '*':
        return True
    if ',' in pattern:
        return any(match_cron_field(val, p) for p in pattern.split(','))
    if pattern.startswith('*/'):
        try:
            step = int(pattern.split('/')[1])
            return val % step == 0
        except (ValueError, IndexError):
            return False
    if '-' in pattern:
        try:
            start, end = map(int, pattern.split('-'))
            return start <= val <= end
        except ValueError:
            return False
    try:
        return val == int(pattern)
    except ValueError:
        return False

def matches_cron(dt: datetime, cron_str: str) -> bool:
    fields = cron_str.strip().split()
    if len(fields) != 5:
        return False
    
    minute, hour, day, month, day_of_week = fields
    # dt.weekday() returns 0 (Monday) to 6 (Sunday)
    # Cron standard: 0 (Sunday) to 6 (Saturday). Convert python weekday:
    cron_dow = dt.weekday() + 1
    if cron_dow == 7:
        cron_dow = 0

    return (
        match_cron_field(dt.minute, minute) and
        match_cron_field(dt.hour, hour) and
        match_cron_field(dt.day, day) and
        match_cron_field(dt.month, month) and
        match_cron_field(cron_dow, day_of_week)
    )

def calculate_next_run(cron_str: Optional[str]) -> Optional[datetime]:
    if not cron_str:
        return None
    # Quick approximation for scheduler polling: check each minute up to 24 hours
    now = datetime.utcnow().replace(second=0, microsecond=0)
    for i in range(1, 1441):
        future = now + timedelta(minutes=i)
        if matches_cron(future, cron_str):
            return future
    return None

class TaskScheduler:
    def __init__(self):
        self._running = False
        self._task: Optional[asyncio.Task] = None

    def start(self):
        if not self._running:
            self._running = True
            self._task = asyncio.create_task(self._loop())
            logger.info("Background Task Scheduler started.")

    async def stop(self):
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            logger.info("Background Task Scheduler stopped.")

    async def _loop(self):
        while self._running:
            try:
                # Poll database every 30 seconds for active jobs
                await self.poll_and_execute_jobs()
            except Exception as e:
                logger.error(f"Error in scheduler polling loop: {e}")
            await asyncio.sleep(30)

    async def poll_and_execute_jobs(self):
        now = datetime.utcnow()
        with Session(engine) as session:
            # Select jobs that are active and scheduled to run in the past or now
            statement = select(ScheduledJob).where(
                ScheduledJob.is_active == True,
                ScheduledJob.next_run_at <= now
            )
            jobs = session.exec(statement).all()

            for job in jobs:
                logger.info(f"Triggering scheduled job '{job.name}' ({job.id})")
                
                # Create job execution log
                run = JobRun(
                    job_id=job.id,
                    state="running",
                    started_at=datetime.utcnow()
                )
                session.add(run)
                session.commit()
                session.refresh(run)

                try:
                    if job.task_type == "workflow_run":
                        # Add a pending workflow execution
                        wf_exec = WorkflowExecution(
                            workflow_id=job.target_id,
                            state="pending",
                            input_data=job.payload,
                            started_at=datetime.utcnow()
                        )
                        session.add(wf_exec)
                        session.commit()
                        session.refresh(wf_exec)
                        
                        # Trigger runner in background task
                        asyncio.create_task(
                            workflow_runner.execute_workflow(wf_exec.id, session)
                        )
                    elif job.task_type == "agent_run":
                        # Launch background agent run session
                        import uuid
                        session_id = f"sched-{uuid.uuid4()}"
                        
                        def db_session_factory():
                            return Session(engine)
                        
                        # Payload standard structures: {"prompt": "...", "history": [...]}
                        import json
                        try:
                            payload_dict = json.loads(job.payload)
                        except json.JSONDecodeError:
                            payload_dict = {}
                        
                        prompt = payload_dict.get("prompt", "Scheduled execution check.")
                        messages = [{"role": "user", "content": prompt}]
                        
                        asyncio.create_task(
                            runtime_engine.run_agent_job(
                                session_id=session_id,
                                agent_id=str(job.target_id),
                                messages=messages,
                                session_db_factory=db_session_factory
                            )
                        )
                    else:
                        raise ValueError(f"Unknown task type: {job.task_type}")

                    # Complete run logs
                    run.state = "completed"
                    run.finished_at = datetime.utcnow()
                except Exception as err:
                    logger.error(f"Failed to execute job '{job.name}': {err}")
                    run.state = "failed"
                    run.finished_at = datetime.utcnow()
                    run.error_message = str(err)
                
                # Calculate next occurrence
                job.next_run_at = calculate_next_run(job.cron_expression)
                session.add(job)
                session.add(run)
                session.commit()

scheduler = TaskScheduler()
