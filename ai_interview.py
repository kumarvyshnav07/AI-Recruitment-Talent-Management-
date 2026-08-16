"""
==========================================================
AI Recruitment Copilot
Milestone 3: AI Interview Engine (Groq-backed)
==========================================================

Covers, per the Milestone 3 brief:
  Module 1 - role-specific question generation, categorized by
             difficulty (Beginner / Intermediate / Advanced) and by
             type (technical / behavioural / situational / follow-up).
  Module 3 - AI interview simulation: evaluate text OR voice answers,
             score them, and roll everything up into a final
             performance report (see interview_summary()).

Runs on GroqCloud instead of Gemini - no-credit-card free tier, and
Groq's OpenAI-compatible chat.completions endpoint supports native JSON
mode, so every prompt below that returns JSON is enforced server-side.
"""

import os
import json
import logging
from typing import Dict, List

from dotenv import load_dotenv
from groq import Groq

# ==========================================================
# LOAD ENVIRONMENT & CONFIG
# ==========================================================

load_dotenv()

API_KEY = os.getenv("GROQ_API_KEY")

if not API_KEY:
    raise ValueError("GROQ_API_KEY not found inside .env — get one free (no card) at console.groq.com")

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger(__name__)

client = Groq(api_key=API_KEY)

# openai/gpt-oss-120b: strongest reasoning, primary pick.
# openai/gpt-oss-20b: smaller/faster, used as an automatic fallback if the
# first model is rate-limited or briefly unavailable.
# (llama-3.3-70b-versatile / llama-3.1-8b-instant are deprecated on Groq
# as of mid-2026 and are being shut down - don't use those model IDs.)
MODELS = ["openai/gpt-oss-120b", "openai/gpt-oss-20b"]
TRANSCRIPTION_MODEL = "whisper-large-v3"

DIFFICULTY_LEVELS = ["Beginner", "Intermediate", "Advanced"]

# ==========================================================
# PROMPTS
# ==========================================================

SYSTEM_PROMPT = """
You are a Senior Technical Recruiter and Technical Interviewer.
Generate accurate interview questions and evaluate candidate responses strictly.
Always return ONLY valid JSON without any markdown formatting or surrounding text.
"""

# Each question is now an object carrying its own difficulty tag, so the
# recruiter dashboard can categorize / filter by Beginner, Intermediate,
# or Advanced instead of only picking one difficulty for the whole set.
QUESTION_PROMPT = """
Candidate Information
Name: {name}
Experience: {experience}
ATS Score: {ats}
Skills: {skills}
Projects: {projects}
Certifications: {certifications}

Target Job Role: {job}
Required Job Skills: {required}
Requested Difficulty Center-Point: {difficulty}

Generate:
- 5 Technical Questions
- 3 Behavioural Questions
- 2 Situational Questions
- 2 Follow-up Questions

Every question must be tagged with a difficulty level of exactly one of:
"Beginner", "Intermediate", or "Advanced". Spread the technical questions
across at least two difficulty levels, biased around the requested
center-point ({difficulty}), so the set is genuinely categorized rather
than uniformly one level.

Return ONLY valid JSON matching this exact structure:
{{
  "technical": [
    {{"question": "q1", "difficulty": "Beginner"}},
    {{"question": "q2", "difficulty": "Intermediate"}},
    {{"question": "q3", "difficulty": "Intermediate"}},
    {{"question": "q4", "difficulty": "Advanced"}},
    {{"question": "q5", "difficulty": "Advanced"}}
  ],
  "behavioural": [
    {{"question": "q1", "difficulty": "Intermediate"}},
    {{"question": "q2", "difficulty": "Intermediate"}},
    {{"question": "q3", "difficulty": "Advanced"}}
  ],
  "situational": [
    {{"question": "q1", "difficulty": "Intermediate"}},
    {{"question": "q2", "difficulty": "Advanced"}}
  ],
  "follow_up": ["q1", "q2"]
}}
"""

EVALUATION_PROMPT = """
Candidate Role: {job_role}
Question Asked: {question}
Candidate Answer: {answer}

Evaluate the response and return ONLY valid JSON matching this structure:
{{
  "technical_score": <1-10>,
  "communication_score": <1-10>,
  "confidence_score": <1-10>,
  "problem_solving_score": <1-10>,
  "strengths": ["<strength 1>", "<strength 2>"],
  "weaknesses": ["<weakness 1>"],
  "improvement": ["<suggestion 1>"],
  "final_comment": "<summary comment>"
}}
"""

# Note: no TRANSCRIPTION_PROMPT here - Groq's Whisper endpoint transcribes
# directly from audio, it doesn't take a text instruction prompt the way
# Gemini's multimodal call used to.

# ==========================================================
# PARSER & CLIENT
# ==========================================================

class JSONParser:
    @staticmethod
    def clean(text: str) -> str:
        text = text.strip()
        text = text.replace("```json", "").replace("```", "")
        return text.strip()

    @staticmethod
    def parse(text: str):
        try:
            return json.loads(JSONParser.clean(text))
        except Exception as e:
            logger.error(f"JSON Parsing Error: {e}")
            return None


class GroqLLMClient:
    def __init__(self):
        self.client = client
        self.models = MODELS

    def ask(self, prompt: str, max_retries: int = 2, json_mode: bool = True) -> str:
        """Text prompt -> text response, with model/retry fallback.
        json_mode=True (the default) turns on Groq's native JSON mode,
        which server-side enforces that the reply is valid JSON - every
        prompt in this file that expects JSON already says so in its own
        text, which is required for JSON mode to kick in."""
        return self._generate(prompt, max_retries, json_mode)

    def _generate(self, prompt: str, max_retries: int, json_mode: bool) -> str:
        last_exception = None
        for model_name in self.models:
            for attempt in range(1, max_retries + 1):
                try:
                    kwargs = {"response_format": {"type": "json_object"}} if json_mode else {}
                    response = self.client.chat.completions.create(
                        model=model_name,
                        messages=[
                            {"role": "system", "content": SYSTEM_PROMPT},
                            {"role": "user", "content": prompt},
                        ],
                        temperature=0.7,
                        **kwargs,
                    )
                    return response.choices[0].message.content
                except Exception as e:
                    last_exception = e
                    err_str = str(e)
                    if "429" in err_str or "rate_limit" in err_str.lower():
                        break  # try the next model
                    elif "503" in err_str or "unavailable" in err_str.lower():
                        import time
                        time.sleep(attempt)
                    else:
                        break
        raise Exception(f"Groq API Error: {last_exception}")

    def transcribe(self, audio_bytes: bytes, filename: str = "answer.wav") -> str:
        """Speech-to-text via Groq's hosted Whisper endpoint - a direct
        transcription call, not a chat prompt, so it doesn't go through
        _generate()/JSON mode."""
        try:
            transcription = self.client.audio.transcriptions.create(
                file=(filename, audio_bytes),
                model=TRANSCRIPTION_MODEL,
                response_format="text",
            )
            return str(transcription).strip()
        except Exception as e:
            raise Exception(f"Groq Transcription Error: {e}")


groq_llm = GroqLLMClient()

# ==========================================================
# AI INTERVIEW ENGINE
# ==========================================================

class AIInterviewEngine:
    def __init__(self):
        self.client = groq_llm

    # -----------------------------------------------------
    # MODULE 1: ROLE-SPECIFIC QUESTION GENERATION
    # -----------------------------------------------------

    def generate_questions(self, candidate: Dict, job: Dict, difficulty: str = "Intermediate") -> Dict:
        prompt = QUESTION_PROMPT.format(
            name=candidate.get("name", "Candidate"),
            experience=candidate.get("experience", "Not specified"),
            ats=candidate.get("ats_score", 0),
            skills=candidate.get("skills", ""),
            projects=candidate.get("projects", []),
            certifications=candidate.get("certifications", []),
            job=job.get("job_title", "General Role"),
            required=job.get("required_skills", ""),
            difficulty=difficulty
        )

        try:
            response = self.client.ask(prompt)
            parsed = JSONParser.parse(response)
            if parsed:
                return self._normalize_questions(parsed, difficulty)
        except Exception as e:
            logger.error(f"Question Generation Error: {e}")

        return self._fallback_questions(job, difficulty)

    @staticmethod
    def _normalize_questions(parsed: Dict, default_difficulty: str) -> Dict:
        """
        Defensive normalization: the model is asked to return
        {"question": ..., "difficulty": ...} objects for technical /
        behavioural / situational, but LLM JSON output is never fully
        guaranteed. This makes sure every entry downstream is always a
        dict with both keys - even if the model slipped back to a plain
        string, or used an unrecognized difficulty label - so the UI
        never has to guess at the shape.
        """
        default_difficulty = default_difficulty if default_difficulty in DIFFICULTY_LEVELS else "Intermediate"

        def normalize_list(items):
            normalized = []
            for item in items or []:
                if isinstance(item, dict):
                    q = item.get("question", "").strip()
                    d = item.get("difficulty", default_difficulty)
                    d = d if d in DIFFICULTY_LEVELS else default_difficulty
                else:
                    q = str(item).strip()
                    d = default_difficulty
                if q:
                    normalized.append({"question": q, "difficulty": d})
            return normalized

        follow_up = [
            (item.get("question") if isinstance(item, dict) else str(item)).strip()
            for item in parsed.get("follow_up", []) or []
        ]
        follow_up = [q for q in follow_up if q]

        return {
            "technical": normalize_list(parsed.get("technical")),
            "behavioural": normalize_list(parsed.get("behavioural")),
            "situational": normalize_list(parsed.get("situational")),
            "follow_up": follow_up,
        }

    @staticmethod
    def _fallback_questions(job: Dict, difficulty: str) -> Dict:
        """Used if the API fails or hits quota - still returns the same
        difficulty-tagged shape the rest of the app expects."""
        job_title = job.get("job_title", "Data Engineer")
        d = difficulty if difficulty in DIFFICULTY_LEVELS else "Intermediate"
        return {
            "technical": [
                {"question": f"Describe your end-to-end architecture design for a {job_title} pipeline.", "difficulty": d},
                {"question": "How do you handle query optimization and indexing for large datasets?", "difficulty": "Beginner"},
                {"question": "What strategies do you use for partitioning and managing schema evolution?", "difficulty": d},
                {"question": "How do you implement data validation checks to prevent corrupted data ingestion?", "difficulty": d},
                {"question": "Explain your approach to continuous integration and monitoring for automated pipelines.", "difficulty": "Advanced"},
            ],
            "behavioural": [
                {"question": "Describe a critical production bug you encountered and how you diagnosed it under pressure.", "difficulty": d},
                {"question": "How do you balance technical quality with aggressive product delivery deadlines?", "difficulty": "Beginner"},
                {"question": "How do you communicate technical requirements to non-technical stakeholders?", "difficulty": d},
            ],
            "situational": [
                {"question": "What steps would you take if a database node experiences high CPU utilization in production?", "difficulty": d},
                {"question": "How do you handle breaking upstream API schema changes that occur without notice?", "difficulty": "Advanced"},
            ],
            "follow_up": [
                "Can you elaborate on the performance bottleneck you encountered and how you measured the fix?",
                "What architectural trade-offs did you evaluate when making your technology choices?",
            ],
        }

    # -----------------------------------------------------
    # MODULE 3: RESPONSE EVALUATION (TEXT)
    # -----------------------------------------------------

    def evaluate_answer(self, question: str, answer: str, job_role: str = "Software Engineer") -> Dict:
        prompt = EVALUATION_PROMPT.format(
            question=question,
            answer=answer,
            job_role=job_role
        )
        try:
            response = self.client.ask(prompt)
            parsed = JSONParser.parse(response)
            if parsed:
                parsed["ai_evaluated"] = True
                return parsed
        except Exception as e:
            logger.error(f"Answer Evaluation Error - Groq call failed, using fallback: {e}")

        # NOTE: this is a static placeholder, not a real evaluation - the
        # Groq call above failed (see the logged error). `ai_evaluated`
        # lets the UI flag this turn instead of silently presenting fake
        # scores as if the AI had actually judged the answer.
        return {
            "technical_score": 7,
            "communication_score": 8,
            "confidence_score": 7,
            "problem_solving_score": 7,
            "strengths": ["Answer logged and processed"],
            "weaknesses": ["Requires further technical detail"],
            "improvement": ["Elaborate with specific implementation metrics"],
            "final_comment": "AI evaluation unavailable for this turn - placeholder score shown. Check GROQ_API_KEY / logs.",
            "ai_evaluated": False,
        }

    # -----------------------------------------------------
    # MODULE 3: VOICE RESPONSES
    # -----------------------------------------------------

    def transcribe_audio(self, audio_bytes: bytes, mime_type: str = "audio/wav") -> str:
        """
        Turn a recorded candidate answer (e.g. from st.audio_input) into
        plain text so it can flow through the exact same evaluate_answer
        path as a typed response. Raises on failure - the caller decides
        how to surface that to the recruiter (no silent fallback here,
        since a wrong fallback transcript would corrupt the evaluation).

        Uses Groq's hosted Whisper endpoint directly (speech-to-text is a
        dedicated Groq API, not a chat prompt), so mime_type isn't needed
        beyond picking a sane filename extension for the upload.
        """
        if not audio_bytes:
            raise ValueError("No audio data provided for transcription")

        ext = "wav"
        if mime_type and "/" in mime_type:
            ext = mime_type.split("/")[-1].split(";")[0] or "wav"

        return self.client.transcribe(audio_bytes, filename=f"answer.{ext}")

    # -----------------------------------------------------
    # MODULE 3: FINAL INTERVIEW PERFORMANCE REPORT
    # -----------------------------------------------------

    def interview_summary(self, candidate_name: str, evaluations: List[Dict]) -> Dict:
        """Aggregate every per-answer evaluation into one final interview
        performance report - overall score, merged strengths/weaknesses,
        and a verdict-style closing comment - for the recruiter dashboard."""
        if not evaluations:
            return {
                "candidate_name": candidate_name,
                "questions_answered": 0,
                "average_technical_score": 0,
                "average_communication_score": 0,
                "average_confidence_score": 0,
                "average_problem_solving_score": 0,
                "overall_score": 0,
                "strengths": [],
                "weaknesses": [],
                "improvement_areas": [],
                "final_comment": "No answers were submitted during this interview.",
            }

        def _avg(key):
            values = [e.get(key, 0) for e in evaluations]
            return round(sum(values) / len(values), 1)

        avg_technical = _avg("technical_score")
        avg_communication = _avg("communication_score")
        avg_confidence = _avg("confidence_score")
        avg_problem_solving = _avg("problem_solving_score")

        overall = round(
            (avg_technical + avg_communication + avg_confidence + avg_problem_solving) / 4, 1
        )

        strengths, weaknesses, improvements = [], [], []
        for e in evaluations:
            strengths.extend(e.get("strengths", []))
            weaknesses.extend(e.get("weaknesses", []))
            improvements.extend(e.get("improvement", []))

        # De-duplicate while preserving order
        strengths = list(dict.fromkeys(strengths))
        weaknesses = list(dict.fromkeys(weaknesses))
        improvements = list(dict.fromkeys(improvements))

        if overall >= 8:
            final_comment = f"{candidate_name} performed strongly across the interview and is a strong hire candidate."
        elif overall >= 6:
            final_comment = f"{candidate_name} showed solid competence with some areas to probe further."
        else:
            final_comment = f"{candidate_name}'s responses indicate significant gaps versus the role's requirements."

        return {
            "candidate_name": candidate_name,
            "questions_answered": len(evaluations),
            "average_technical_score": avg_technical,
            "average_communication_score": avg_communication,
            "average_confidence_score": avg_confidence,
            "average_problem_solving_score": avg_problem_solving,
            "overall_score": overall,
            "strengths": strengths[:5],
            "weaknesses": weaknesses[:5],
            "improvement_areas": improvements[:5],
            "final_comment": final_comment,
        }

    # -----------------------------------------------------
    # MODULE 3: ADAPTIVE, ANTI-REPEAT FOLLOW-UP ENGINE
    # -----------------------------------------------------

    def generate_followup_question(
        self,
        previous_question: str,
        previous_answer: str,
        job_role: str,
        asked_questions: List[str] = None,
        target_difficulty: str = None,
    ) -> Dict:
        """
        Generates the NEXT interview question with full session memory, so
        it can never loop back onto something already asked (the old bug:
        this only ever looked at the single most-recent Q&A pair).

        `asked_questions` - every question already asked THIS session
        (not just the last one). Sent to the model as an explicit
        do-not-repeat list.

        `target_difficulty` - the difficulty this next question should be
        pitched at. Pair this with adapt_difficulty() so a strong answer
        earns a harder question and a weak one gets an easier one, instead
        of the session sitting flat at one level the whole time.

        Returns {"question": str, "difficulty": str, "topic": str} instead
        of a bare string, so the UI can badge/track it.
        """
        asked_questions = [q for q in (asked_questions or []) if q]
        target_difficulty = target_difficulty if target_difficulty in DIFFICULTY_LEVELS else "Intermediate"

        history_block = "\n".join(f"- {q}" for q in asked_questions) or "- (none yet - this is the first follow-up)"

        prompt = f"""
Job Role: {job_role}
Target Difficulty For This Question: {target_difficulty}

Most Recent Question: {previous_question}
Candidate's Answer: {previous_answer}

Every question already asked earlier in THIS interview session (do NOT
repeat any of these, and do NOT ask a near-duplicate that just rewords the
same idea or probes the exact same sub-topic):
{history_block}

Ask ONE new follow-up question that:
1. Either digs one level deeper into the candidate's last answer, OR pivots
   to a genuinely unexplored angle of the role (a different skill, tool,
   or scenario not covered by anything in the list above).
2. Is pitched at "{target_difficulty}" difficulty.
3. Is not a rephrasing of anything already asked.

Return ONLY valid JSON matching this structure:
{{"question": "<the new question>", "difficulty": "{target_difficulty}", "topic": "<2-4 word topic tag, e.g. 'Database Indexing'>"}}
"""
        try:
            response = self.client.ask(prompt)
            parsed = JSONParser.parse(response)
            if parsed and parsed.get("question", "").strip():
                q = parsed["question"].strip()
                # Safety net: if the model repeated itself anyway, drop
                # through to the anti-repeat fallback bank instead.
                if q.lower() not in [a.lower() for a in asked_questions]:
                    d = parsed.get("difficulty")
                    return {
                        "question": q,
                        "difficulty": d if d in DIFFICULTY_LEVELS else target_difficulty,
                        "topic": (parsed.get("topic") or "General").strip(),
                    }
        except Exception as e:
            logger.error(f"Follow-up Generation Error: {e}")

        return self._fallback_followup(job_role, asked_questions, target_difficulty)

    @staticmethod
    def _fallback_followup(job_role: str, asked_questions: List[str], target_difficulty: str) -> Dict:
        """Deterministic ROTATING bank (never random.choice - random can
        easily re-pick a question it already picked). Wide enough to carry
        a long session, and filtered against everything already asked so
        it self-heals even if the API is down for several turns in a row."""
        bank = [
            f"How do you ensure reliability and monitoring for your {job_role} implementations?",
            "What specific error handling measures do you put in place for unexpected data types?",
            "How would you optimize memory usage or database calls in that scenario?",
            f"Walk me through how you'd design a code review checklist specific to {job_role} work.",
            "Describe a time you had to learn a new tool or framework quickly for a project.",
            "How do you approach testing and validating your work before it reaches production?",
            "What trade-offs do you consider when choosing between build-vs-buy for a component?",
            "How do you keep your technical skills current in this field?",
            "Tell me about a disagreement with a teammate over a technical approach and how it was resolved.",
            f"What metrics would you track to prove the success of a {job_role} project?",
            "How would you approach onboarding a new engineer onto a codebase you own?",
            "Describe how you'd debug a production issue you can't reproduce locally.",
        ]
        asked_lower = [a.lower() for a in asked_questions]
        unused = [q for q in bank if q.lower() not in asked_lower]
        pool = unused or bank  # bank exhausted -> recycle rather than crash
        index = len(asked_questions) % len(pool)
        return {"question": pool[index], "difficulty": target_difficulty, "topic": "General"}

    @staticmethod
    def adapt_difficulty(current_difficulty: str, evaluation: Dict) -> str:
        """Bumps difficulty up/down one notch off technical + problem-solving
        scores, so the interview actually adapts turn-by-turn instead of
        staying flat: score well on an Intermediate question and the next
        one steps up to Advanced; struggle and it steps back down."""
        current_difficulty = current_difficulty if current_difficulty in DIFFICULTY_LEVELS else "Intermediate"
        idx = DIFFICULTY_LEVELS.index(current_difficulty)
        avg = (evaluation.get("technical_score", 5) + evaluation.get("problem_solving_score", 5)) / 2
        if avg >= 8 and idx < len(DIFFICULTY_LEVELS) - 1:
            idx += 1
        elif avg <= 4 and idx > 0:
            idx -= 1
        return DIFFICULTY_LEVELS[idx]


# Export singleton instance
engine = AIInterviewEngine()