from pydantic import BaseModel


class ScanWorkerEvent(BaseModel):
    scan_job_id: str
