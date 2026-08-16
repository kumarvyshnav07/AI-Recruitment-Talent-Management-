"""
interview_service.py
=====================
Thin orchestration layer around ai_interview.engine for running a
structured interview session (create -> generate questions -> evaluate
each answer -> finish with an aggregate report).

Not currently wired into the Streamlit UI (interview_page.py talks to
`engine` directly for its live chat simulation), but kept correct and
usable for anyone who wants persistent, multi-step interview sessions
instead of ad-hoc chat state.
"""
from copy import deepcopy
from datetime import datetime
from typing import Dict
import logging
import uuid

from ai_interview import engine

logger = logging.getLogger(__name__)


class InterviewService:

    # =====================================================
    # CREATE INTERVIEW SESSION
    # =====================================================
    def create_interview_session(
        self, candidate: dict, job: dict, difficulty: str, interviewer: str
    ) -> dict:
        if not candidate:
            raise ValueError("Candidate cannot be empty")
        if not job:
            raise ValueError("Job cannot be empty")

        return {
            "session_id": str(uuid.uuid4()),
            "candidate": deepcopy(candidate),
            "job": deepcopy(job),
            "difficulty": difficulty,
            "interviewer": interviewer,
            "started_at": datetime.now(),
            "completed_at": None,
            "questions": [],
            "answers": [],
            "evaluations": [],
            "report": None,
            "status": "Running",
        }

    # =====================================================
    # GENERATE QUESTIONS
    # =====================================================
    def generate_questions(self, session: dict) -> Dict:
        logger.info("Generating AI questions for session %s", session.get("session_id"))

        questions = engine.generate_questions(
            candidate=session["candidate"],
            job=session["job"],
            difficulty=session["difficulty"],
        )
        session["questions"] = questions
        return questions

    # =====================================================
    # EVALUATE ANSWER
    # =====================================================
    def evaluate_answer(self, session: dict, question: str, answer: str) -> Dict:
        logger.info("Evaluating answer for session %s", session.get("session_id"))

        job_role = session["job"].get("job_title", "Software Engineer")
        result = engine.evaluate_answer(question, answer, job_role=job_role)

        session["answers"].append({"question": question, "answer": answer})
        session["evaluations"].append(result)
        return result

    # =====================================================
    # FINISH INTERVIEW
    # =====================================================
    def finish_interview(self, session: dict) -> Dict:
        logger.info("Generating final report for session %s", session.get("session_id"))

        report = engine.interview_summary(
            session["candidate"].get("name", "Candidate"),
            session["evaluations"],
        )

        session["completed_at"] = datetime.now()
        session["status"] = "Completed"
        session["report"] = report
        return report

    # =====================================================
    # RESET SESSION
    # =====================================================
    def reset_session(self) -> Dict:
        return {"questions": [], "answers": [], "evaluations": []}


# Singleton
interview_service = InterviewService()
