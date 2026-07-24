"""
skills_database.py
===================
Single source of truth for "what is a skill" and "what counts as the
same skill".

Why this file exists
---------------------
Before this change, skill_extractor.py was empty (extraction was
basically random / hardcoded), and skill_matcher.py only did an exact
string comparison after lower-casing. That meant:
    - A resume that said "JS" was never matched against a job asking
      for "JavaScript".
    - Skills mentioned in project/summary text (not under a literal
      "Skills" heading) were never picked up.
    - Only a handful of skills could ever be detected.

This file fixes the root problem: one canonical skill list + alias map
that BOTH skill_extractor.py (resume -> skills) and skill_matcher.py
(compare two skill lists) import and use. Add a skill once here and it
is automatically extractable AND matchable everywhere.

How to extend
--------------
Add an entry to SKILL_ALIASES:
    "Canonical Display Name": ["alias one", "alias two", ...]
Aliases are matched case-insensitively. You don't need to add the
canonical name itself as an alias - that's automatic.
"""

# canonical_name -> list of alternate spellings / abbreviations
SKILL_ALIASES = {
    # ---------------- Programming Languages ----------------
    "Python": ["python3", "py"],
    "Java": [],
    "JavaScript": ["js", "javascript es6", "es6", "ecmascript"],
    "TypeScript": ["ts"],
    "C": ["c programming"],
    "C++": ["cpp", "c plus plus"],
    "C#": ["csharp", "c sharp"],
    "Go": ["golang"],
    "Rust": [],
    "Kotlin": [],
    "Swift": [],
    "PHP": [],
    "Ruby": [],
    "R": ["r programming", "r language"],
    "Scala": [],
    "MATLAB": [],
    "Perl": [],
    "Dart": [],
    "Shell Scripting": ["bash", "shell script", "bash scripting", "shell"],

    # ---------------- Web Frontend ----------------
    "HTML": ["html5"],
    "CSS": ["css3"],
    "React": ["react.js", "reactjs"],
    "Angular": ["angular.js", "angularjs"],
    "Vue.js": ["vue", "vuejs"],
    "Next.js": ["nextjs"],
    "Redux": [],
    "Tailwind CSS": ["tailwind", "tailwindcss"],
    "Bootstrap": [],
    "jQuery": [],
    "Sass": ["scss"],
    "Webpack": [],

    # ---------------- Backend / Frameworks ----------------
    "Node.js": ["nodejs", "node"],
    "Express.js": ["express", "expressjs"],
    "Django": [],
    "Flask": [],
    "FastAPI": ["fast api"],
    "Spring Boot": ["spring", "springboot"],
    ".NET": ["dotnet", "asp.net", "asp .net"],
    "Laravel": [],
    "Ruby on Rails": ["rails"],
    "GraphQL": [],
    "REST API": ["rest apis", "restful api", "rest", "api development"],

    # ---------------- Databases ----------------
    "SQL": ["structured query language"],
    "MySQL": [],
    "PostgreSQL": ["postgres"],
    "MongoDB": ["mongo"],
    "SQLite": [],
    "Oracle Database": ["oracle db", "oracle sql"],
    "Redis": [],
    "Cassandra": [],
    "Firebase": [],
    "DynamoDB": [],
    "Microsoft SQL Server": ["mssql", "sql server"],

    # ---------------- Cloud & DevOps ----------------
    "AWS": ["amazon web services"],
    "Microsoft Azure": ["azure"],
    "Google Cloud Platform": ["gcp", "google cloud"],
    "Docker": [],
    "Kubernetes": ["k8s"],
    "Jenkins": [],
    "CI/CD": ["ci cd", "continuous integration", "continuous deployment"],
    "Terraform": [],
    "Ansible": [],
    "Linux": ["unix"],
    "Nginx": [],
    "Git": [],
    "GitHub": [],
    "GitLab": [],

    # ---------------- Data Science / ML / AI ----------------
    "Machine Learning": ["ml"],
    "Deep Learning": ["dl"],
    "Artificial Intelligence": ["ai"],
    "Natural Language Processing": ["nlp"],
    "Computer Vision": ["opencv"],
    "Data Analysis": ["data analytics", "data analytic"],
    "Data Visualization": [],
    "Data Science": [],
    "Big Data": [],
    "Statistics": ["statistical analysis"],
    "Pandas": [],
    "NumPy": [],
    "Scikit-learn": ["sklearn", "scikit learn"],
    "TensorFlow": [],
    "PyTorch": [],
    "Keras": [],
    "OpenCV": ["open cv"],
    "Power BI": ["powerbi"],
    "Tableau": [],
    "Excel": ["ms excel", "microsoft excel"],
    "ETL": ["extract transform load"],
    "Apache Spark": ["pyspark", "spark"],
    "Hadoop": [],
    "Generative AI": ["genai", "gen ai"],
    "Large Language Models": ["llm", "llms"],

    # ---------------- Mobile ----------------
    "Android Development": ["android"],
    "iOS Development": ["ios"],
    "React Native": [],
    "Flutter": [],

    # ---------------- Testing ----------------
    "Unit Testing": [],
    "Selenium": [],
    "Postman": [],
    "JUnit": [],
    "Pytest": [],

    # ---------------- Tools / Methodologies ----------------
    "Agile Methodology": ["agile", "scrum"],
    "Jira": [],
    "Figma": [],
    "Object-Oriented Programming": ["oop", "object oriented programming"],
    "Data Structures and Algorithms": ["dsa", "data structures", "algorithms"],
    "Microservices": ["microservice architecture"],
    "System Design": [],

    # ---------------- Soft Skills (kept small & unambiguous) ----------------
    "Communication": ["communication skills"],
    "Leadership": [],
    "Teamwork": ["team collaboration", "collaboration"],
    "Problem Solving": ["problem-solving"],
    "Time Management": [],
    "Project Management": [],
}


def _build_lookup():
    """Flatten SKILL_ALIASES into {lowercase alias/name: canonical name},
    sorted longest-first so multi-word skills are matched before their
    shorter substrings (e.g. 'Machine Learning' before 'Learning')."""
    lookup = {}
    for canonical, aliases in SKILL_ALIASES.items():
        lookup[canonical.lower()] = canonical
        for alias in aliases:
            lookup[alias.lower().strip()] = canonical
    return lookup


ALIAS_LOOKUP = _build_lookup()

# Longest term first, so phrase-matching (see skill_extractor.py) prefers
# "Machine Learning" over accidentally matching just "Learning" first.
ALL_TERMS_BY_LENGTH = sorted(ALIAS_LOOKUP.keys(), key=len, reverse=True)


def normalize_skill(term):
    """Map any raw skill string (alias, abbreviation, different casing)
    to its canonical display name. Unknown terms are returned title-cased
    and unchanged, so custom/niche skills typed by a user still work -
    they just won't get alias-matching benefits."""
    term = (term or "").strip().lower()
    if not term:
        return ""
    return ALIAS_LOOKUP.get(term, term.title())