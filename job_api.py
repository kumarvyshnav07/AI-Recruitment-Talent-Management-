"""
job_api.py
==========
FastAPI service for posting/listing jobs, backed by the same MySQL
database as the Streamlit app (via database.py's get_connection/DB_CONFIG).

Run locally with:
    uvicorn job_api:app --reload

Endpoints
---------
POST   /jobs                 -> create a job posting
GET    /jobs                 -> list all job postings
GET    /jobs/{job_id}        -> fetch one job posting
DELETE /jobs/{job_id}        -> remove a job posting
GET    /jobs/{job_id}/matches -> rank all candidates against this job
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from database import init_db, create_job, get_jobs, get_job, update_job, delete_job
from job_matching import match_candidates_to_job

app = FastAPI(title="TalentOps AI — Job Postings API")

init_db()


class Job(BaseModel):
    job_title: str = Field(..., min_length=2, max_length=200)
    company_name: str = Field(..., min_length=2, max_length=200)
    experience: str = Field(..., examples=["Fresher", "2 Years", "5+ Years"])
    location: str = Field(..., min_length=2, max_length=200)
    salary: float = Field(..., gt=0, description="Annual salary")
    required_skills: str = Field(
        default="", description="Comma-separated, e.g. 'Python, SQL, Docker'"
    )
    qualification: str = Field(default="Any Degree")


class JobOut(Job):
    job_id: int


@app.post("/jobs", response_model=dict, status_code=201)
def create_job_endpoint(job: Job):
    new_id = create_job(
        job_title=job.job_title,
        company_name=job.company_name,
        experience=job.experience,
        location=job.location,
        salary=job.salary,
        required_skills=job.required_skills,
        qualification=job.qualification,
    )
    if new_id is None:
        raise HTTPException(status_code=500, detail="Database connection failed")
    return {"message": "Job posted successfully", "job_id": new_id}


@app.get("/jobs", response_model=list[JobOut])
def list_jobs():
    return get_jobs()


@app.get("/jobs/{job_id}", response_model=JobOut)
def get_job_endpoint(job_id: int):
    job = get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@app.put("/jobs/{job_id}")
def update_job_endpoint(job_id: int, job: Job):
    existing = get_job(job_id)
    if existing is None:
        raise HTTPException(status_code=404, detail="Job not found")

    updated = update_job(
        job_id=job_id,
        job_title=job.job_title,
        company_name=job.company_name,
        experience=job.experience,
        location=job.location,
        salary=job.salary,
        required_skills=job.required_skills,
        qualification=job.qualification,
    )
    if not updated:
        raise HTTPException(status_code=500, detail="Database connection failed")
    return {"message": "Job updated successfully", "job_id": job_id}


@app.delete("/jobs/{job_id}")
def delete_job_endpoint(job_id: int):
    deleted = delete_job(job_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Job not found")
    return {"message": "Job deleted successfully"}


@app.get("/jobs/{job_id}/matches")
def get_job_matches(job_id: int):
    result = match_candidates_to_job(job_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return result


@app.get("/health")
def health():
    return {"status": "ok"}