"""
Job queue service for managing background tasks with status tracking.
"""

import os
import time
import json
import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any, Callable
from pathlib import Path
import uuid

logger = logging.getLogger(__name__)

# In-memory job queue
JOBS = {}

class JobStatus:
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"

class Job:
    def __init__(self, 
                job_id: str, 
                job_type: str, 
                parameters: Dict[str, Any],
                created_at: Optional[datetime] = None):
        self.job_id = job_id
        self.job_type = job_type
        self.parameters = parameters
        self.status = JobStatus.PENDING
        self.progress = 0.0
        self.message = "Job created"
        self.error = None
        self.result = None
        self.created_at = created_at or datetime.now()
        self.started_at = None
        self.completed_at = None
        
    def to_dict(self) -> Dict[str, Any]:
        """Convert job to dictionary for serialization"""
        return {
            "job_id": self.job_id,
            "job_type": self.job_type,
            "parameters": self.parameters,
            "status": self.status,
            "progress": self.progress,
            "message": self.message,
            "error": self.error,
            "result": self.result,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Job':
        """Create job from dictionary"""
        job = cls(
            job_id=data["job_id"],
            job_type=data["job_type"],
            parameters=data["parameters"],
            created_at=datetime.fromisoformat(data["created_at"]) if data.get("created_at") else None
        )
        job.status = data["status"]
        job.progress = data["progress"]
        job.message = data["message"]
        job.error = data["error"]
        job.result = data["result"]
        job.started_at = datetime.fromisoformat(data["started_at"]) if data.get("started_at") else None
        job.completed_at = datetime.fromisoformat(data["completed_at"]) if data.get("completed_at") else None
        return job

async def create_job(job_type: str, parameters: Dict[str, Any]) -> str:
    """Create a new job and add it to the queue"""
    job_id = f"{job_type}_{int(time.time())}"
    job = Job(job_id=job_id, job_type=job_type, parameters=parameters)
    JOBS[job_id] = job
    
    # Persist job to disk
    await save_job_to_disk(job)
    
    logger.info(f"Created job {job_id} of type {job_type}")
    return job_id

async def update_job_status(job_id: str, 
                           status: str, 
                           progress: float = None, 
                           message: str = None,
                           error: str = None,
                           result: Dict[str, Any] = None) -> bool:
    """Update the status of a job"""
    if job_id not in JOBS:
        # Try to load from disk
        job = await load_job_from_disk(job_id)
        if not job:
            logger.error(f"Job {job_id} not found")
            return False
        JOBS[job_id] = job
    
    job = JOBS[job_id]
    
    if status:
        job.status = status
        if status == JobStatus.RUNNING and not job.started_at:
            job.started_at = datetime.now()
        elif status in [JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.TIMEOUT]:
            job.completed_at = datetime.now()
    
    if progress is not None:
        job.progress = progress
    
    if message:
        job.message = message
    
    if error:
        job.error = error
    
    if result:
        job.result = result
    
    # Persist updated job to disk
    await save_job_to_disk(job)
    
    logger.info(f"Updated job {job_id} status to {job.status}, progress: {job.progress}")
    return True

async def get_job_status(job_id: str) -> Optional[Dict[str, Any]]:
    """Get the status of a job"""
    if job_id not in JOBS:
        # Try to load from disk
        job = await load_job_from_disk(job_id)
        if not job:
            logger.warning(f"Job {job_id} not found")
            return None
        JOBS[job_id] = job
    
    return JOBS[job_id].to_dict()

async def execute_job(job_id: str, task_func: Callable) -> None:
    """Execute a job asynchronously"""
    if job_id not in JOBS:
        # Try to load from disk
        job = await load_job_from_disk(job_id)
        if not job:
            logger.error(f"Job {job_id} not found, cannot execute")
            return
        JOBS[job_id] = job
    
    job = JOBS[job_id]
    
    # Update status to running
    await update_job_status(job_id, JobStatus.RUNNING, message="Job started")
    
    try:
        # Execute the task
        result = await task_func(**job.parameters)
        
        if isinstance(result, dict) and "success" in result and not result["success"]:
            # Task failed with error
            await update_job_status(
                job_id, 
                JobStatus.FAILED, 
                progress=1.0, 
                message="Job failed",
                error=result.get("error", "Unknown error"),
                result=result
            )
        else:
            # Task completed successfully
            await update_job_status(
                job_id, 
                JobStatus.COMPLETED, 
                progress=1.0, 
                message="Job completed",
                result=result
            )
    except Exception as e:
        logger.exception(f"Error executing job {job_id}: {str(e)}")
        await update_job_status(
            job_id, 
            JobStatus.FAILED, 
            progress=1.0, 
            message="Job failed with exception",
            error=str(e)
        )

async def save_job_to_disk(job: Job) -> bool:
    """Save job state to disk for persistence"""
    try:
        # Create jobs directory if it doesn't exist
        jobs_dir = Path("data/jobs")
        jobs_dir.mkdir(exist_ok=True, parents=True)
        
        # Save job to file
        job_file = jobs_dir / f"{job.job_id}.json"
        with open(job_file, "w") as f:
            json.dump(job.to_dict(), f)
            
        return True
    except Exception as e:
        logger.error(f"Error saving job {job.job_id} to disk: {str(e)}")
        return False

async def load_job_from_disk(job_id: str) -> Optional[Job]:
    """Load job state from disk"""
    try:
        job_file = Path(f"data/jobs/{job_id}.json")
        if not job_file.exists():
            return None
        
        with open(job_file, "r") as f:
            job_data = json.load(f)
            
        return Job.from_dict(job_data)
    except Exception as e:
        logger.error(f"Error loading job {job_id} from disk: {str(e)}")
        return None

async def list_jobs(job_type: Optional[str] = None, 
                   status: Optional[str] = None, 
                   limit: int = 100,
                   include_completed: bool = True) -> List[Dict[str, Any]]:
    """List jobs with optional filtering"""
    try:
        # Load jobs from disk to ensure we have all jobs
        jobs_dir = Path("data/jobs")
        if jobs_dir.exists():
            for job_file in jobs_dir.glob("*.json"):
                job_id = job_file.stem
                if job_id not in JOBS:
                    job = await load_job_from_disk(job_id)
                    if job:
                        JOBS[job_id] = job
        
        # Filter jobs
        filtered_jobs = []
        for job in JOBS.values():
            if job_type and job.job_type != job_type:
                continue
            if status and job.status != status:
                continue
            if not include_completed and job.status in [JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.TIMEOUT]:
                continue
            filtered_jobs.append(job.to_dict())
        
        # Sort by creation time (newest first)
        filtered_jobs.sort(key=lambda j: j.get("created_at", ""), reverse=True)
        
        # Apply limit
        return filtered_jobs[:limit]
    except Exception as e:
        logger.error(f"Error listing jobs: {str(e)}")
        return []

async def cleanup_old_jobs(days: int = 7) -> int:
    """Clean up old completed jobs that are older than X days"""
    try:
        cutoff_date = datetime.now() - timedelta(days=days)
        jobs_dir = Path("data/jobs")
        
        if not jobs_dir.exists():
            return 0
        
        count = 0
        for job_file in jobs_dir.glob("*.json"):
            try:
                # Check file modification time first (faster)
                if job_file.stat().st_mtime > cutoff_date.timestamp():
                    continue
                
                # Load job to check its status
                job_id = job_file.stem
                job = await load_job_from_disk(job_id)
                
                if not job:
                    continue
                
                # Delete if job is completed/failed and older than cutoff
                if (job.status in [JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.TIMEOUT] and
                    job.created_at < cutoff_date):
                    # Remove from memory
                    if job_id in JOBS:
                        del JOBS[job_id]
                    
                    # Remove from disk
                    job_file.unlink()
                    count += 1
            except Exception as e:
                logger.error(f"Error cleaning up job {job_file.stem}: {str(e)}")
        
        return count
    except Exception as e:
        logger.error(f"Error cleaning up old jobs: {str(e)}")
        return 0

# Schedule periodic job cleanup
async def start_cleanup_scheduler():
    """Start periodic job cleanup scheduler"""
    try:
        while True:
            # Run once per day
            await asyncio.sleep(24 * 60 * 60)
            count = await cleanup_old_jobs(days=7)
            logger.info(f"Cleaned up {count} old jobs")
    except asyncio.CancelledError:
        pass 