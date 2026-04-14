"""
AI Resume Analyzer - v7
Fixes: duplicate code removed, present-year experience, better project detection,
       safe caching, download report, phone false-positive fix, Marketing context added,
       experience scoring improved, all edge cases handled
"""

import re
import logging
import streamlit as st

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────
# PAGE CONFIG — must be first Streamlit call
# ─────────────────────────────────────────────
st.set_page_config(
    page_title="AI Resume Analyzer",
    layout="wide",
    page_icon="📄",
    initial_sidebar_state="collapsed",
)

st.markdown("""
<style>
div.stButton > button {
    background-color: #1a73e8;
    color: white;
    border: none;
    border-radius: 8px;
    padding: 10px 28px;
    font-size: 15px;
    font-weight: 600;
    cursor: pointer;
    transition: background-color 0.2s ease,
                transform 0.15s ease,
                box-shadow 0.2s ease;
}
div.stButton > button:hover {
    background-color: #1558b0;
    transform: translateY(-2px);
    box-shadow: 0 4px 12px rgba(26,115,232,0.35);
}
div.stButton > button:active {
    transform: translateY(0px);
    background-color: #0f47a1;
}

/* ── skill tags ── */
.skill-tag {
    display: inline-block;
    background: rgba(26,115,232,0.15);
    color: #64b5f6;
    padding: 5px 14px;
    margin: 4px;
    border-radius: 20px;
    font-size: 13px;
    font-weight: 500;
    border: 1px solid rgba(100,181,246,0.3);
}

/* ── missing box ── */
.missing-box {
    background: rgba(229,57,53,0.1);
    padding: 14px 18px;
    border-left: 4px solid #ef5350;
    margin-top: 8px;
    border-radius: 4px;
}
.missing-item {
    display: flex;
    align-items: flex-start;
    gap: 8px;
    padding: 6px 0;
    font-size: 13.5px;
    color: #ef9a9a;
    border-bottom: 1px solid rgba(239,83,80,0.15);
    line-height: 1.4;
}
.missing-item:last-child { border-bottom: none; }

/* ── suggestion cards ── */
.sug-card {
    background: rgba(249,168,37,0.12);
    border-left: 4px solid #ffa726;
    padding: 12px 16px;
    margin-bottom: 10px;
    font-size: 13.5px;
    line-height: 1.5;
    color: #ffcc80;
    border-radius: 4px;
}
.sug-card.critical {
    background: rgba(230,81,0,0.12);
    border-left-color: #ff7043;
    color: #ffab91;
}
.sug-card.good {
    background: rgba(85,139,47,0.15);
    border-left-color: #81c784;
    color: #a5d6a7;
}
.sug-title {
    font-weight: 600;
    font-size: 13px;
    margin-bottom: 4px;
    color: inherit;
}

/* ── info rows ── */
.info-row {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 7px 0;
    border-bottom: 1px solid rgba(255,255,255,0.08);
    font-size: 14px;
    color: rgba(255,255,255,0.85);
}

/* ── progress steps ── */
.step-bar {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 6px 0;
    font-size: 13px;
    color: rgba(255,255,255,0.6);
}
.step-done { color: #81c784; }

/* ── score badge ── */
.score-badge {
    font-size: 56px;
    font-weight: 700;
    line-height: 1;
    margin: 0;
}
</style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────
# CONSTANTS
# ─────────────────────────────────────────────
import datetime
CURRENT_YEAR = datetime.datetime.now().year

SKILLS_DB: list[str] = [
    # Languages
    "python", "java", "c++", "c#", "go", "rust", "r", "scala", "swift",
    # Data / DB
    "sql", "nosql", "excel", "vba",
    "mongodb", "mysql", "postgresql", "redis", "sqlite",
    # ML / AI
    "machine learning", "deep learning", "nlp", "computer vision",
    "data cleaning", "data visualization", "data wrangling",
    "feature engineering", "statistics",
    "tensorflow", "pytorch", "keras", "scikit-learn", "xgboost", "lightgbm",
    "pandas", "numpy", "matplotlib", "seaborn", "opencv",
    # Web
    "html", "css", "javascript", "typescript",
    "react", "vue", "angular", "next.js",
    "node.js", "express.js", "django", "flask", "fastapi",
    # DevOps / Cloud
    "docker", "kubernetes", "ci/cd", "jenkins", "github actions",
    "aws", "gcp", "azure", "cloud",
    "linux", "bash", "networking",
    # BI / Analytics
    "power bi", "tableau", "looker", "google analytics",
    # Design
    "figma", "sketch", "adobe xd", "design thinking",
    "user testing", "color theory", "typography", "responsive design",
    # Mobile
    "flutter", "kotlin", "react native", "android", "ios",
    # Tools
    "git", "github", "gitlab", "debugging", "jira", "agile", "scrum",
    # CS fundamentals
    "data structures", "algorithms", "oops", "system design",
    # APIs
    "api integration", "rest api", "graphql",
    # Marketing
    "seo", "content marketing",
]

ROLE_SKILLS: dict[str, list[str]] = {
    "AI Engineer":       ["machine learning", "deep learning", "tensorflow",
                          "pytorch", "python", "nlp", "computer vision"],
    "Web Developer":     ["html", "css", "javascript", "react", "node.js",
                          "express.js", "mongodb", "mysql", "git"],
    "Data Analyst":      ["excel", "sql", "power bi", "tableau", "python",
                          "statistics", "pandas", "numpy", "google analytics"],
    "Software Engineer": ["java", "c++", "python", "data structures",
                          "algorithms", "oops", "debugging", "linux", "git"],
    "Data Scientist":    ["python", "pandas", "numpy", "scikit-learn",
                          "machine learning", "deep learning", "tensorflow",
                          "pytorch", "statistics", "data wrangling",
                          "feature engineering", "nlp"],
    "App Developer":     ["java", "kotlin", "flutter", "react native",
                          "api integration", "android", "ios"],
    "DevOps Engineer":   ["linux", "networking", "docker", "kubernetes",
                          "ci/cd", "aws", "bash", "github actions"],
    "UI/UX Designer":    ["figma", "sketch", "design thinking", "color theory",
                          "typography", "user testing", "responsive design",
                          "adobe xd"],
    "Marketing":         ["seo", "content marketing", "google analytics"],
    "Backend Developer": ["python", "java", "django", "flask", "fastapi",
                          "postgresql", "mongodb", "rest api", "docker"],
}

ROLE_CONTEXT_KEYWORDS: dict[str, list[str]] = {
    "Data Scientist":    ["data scientist", "predictive model", "machine learning model",
                          "classification", "regression", "clustering", "model accuracy",
                          "scikit", "random forest", "logistic regression",
                          "feature engineering", "model evaluation"],
    "Data Analyst":      ["data analyst", "dashboard", "business insight", "reporting",
                          "kpi", "data-driven", "trend analysis", "pivot table"],
    "AI Engineer":       ["ai engineer", "deep learning", "neural network", "transformer",
                          "llm", "nlp pipeline", "model deployment", "inference"],
    "Web Developer":     ["web developer", "frontend", "backend", "full stack",
                          "rest api", "responsive", "web application"],
    "Software Engineer": ["software engineer", "software developer", "system design",
                          "microservices", "object oriented"],
    "DevOps Engineer":   ["devops", "ci/cd pipeline", "deployment", "infrastructure",
                          "container", "orchestration", "terraform"],
    "App Developer":     ["mobile app", "android", "ios", "flutter app",
                          "play store", "app store", "mobile development"],
    "UI/UX Designer":    ["ui designer", "ux designer", "wireframe", "prototype",
                          "user research", "usability", "design system"],
    "Backend Developer": ["backend developer", "api development", "server side",
                          "database design", "microservice"],
    "Marketing":         ["digital marketing", "campaign", "seo strategy",
                          "content strategy", "social media", "brand awareness",
                          "lead generation", "google ads"],
}

ADDRESS_WORDS: set[str] = {
    "sector", "road", "street", "india", "nagar", "colony",
    "phase", "block", "district", "village", "tehsil", "pin",
}

# Lines that look like project titles but are NOT
_FALSE_PROJECT_WORDS = {
    "project", "projects", "description", "overview",
    "title", "details", "summary",
}


# ─────────────────────────────────────────────
# LAZY IMPORT HELPERS
# ─────────────────────────────────────────────
def _load_pdf_libs():
    import pdfplumber
    return pdfplumber


def _load_ocr_libs():
    import pytesseract
    from PIL import Image
    return pytesseract, Image


def _load_plotly():
    import plotly.graph_objects as go
    return go


# ─────────────────────────────────────────────
# TEXT EXTRACTION  (safe — no st.* inside cache)
# ─────────────────────────────────────────────
@st.cache_data(show_spinner=False)
def extract_text(file_bytes: bytes, file_type: str) -> tuple[str, str]:
    """
    Returns (text, error_message).
    Keeping st.* calls outside so cache works safely.
    """
    from io import BytesIO
    text = ""
    error = ""
    try:
        if file_type == "application/pdf":
            pdfplumber = _load_pdf_libs()
            with pdfplumber.open(BytesIO(file_bytes)) as pdf:
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n"
        else:
            pytesseract, Image = _load_ocr_libs()
            image = Image.open(BytesIO(file_bytes))
            text = pytesseract.image_to_string(image)
    except Exception as e:
        logger.error("Text extraction failed: %s", e)
        error = str(e)
    return text.strip(), error


# ─────────────────────────────────────────────
# PARSERS
# ─────────────────────────────────────────────
def parse_name(lines: list[str]) -> str:
    for line in lines[:10]:
        words = line.split()
        if 2 <= len(words) <= 4:
            alpha_words = [w for w in words if w.isalpha()]
            if alpha_words and all(w[0].isupper() for w in alpha_words):
                if not any(addr in line.lower() for addr in ADDRESS_WORDS):
                    return line
    return "Not Found"


def parse_email(text: str) -> str:
    matches = re.findall(
        r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-z]{2,}", text
    )
    return matches[0] if matches else "Not Found"


def parse_phone(text: str) -> str:
    """
    FIX: Exclude pure year-ranges like 2020-2024.
    Require at least one digit group of 3+ consecutive digits.
    """
    raw_matches = re.findall(r"\+?\d[\d\s\-]{8,14}\d", text)
    for m in raw_matches:
        digits_only = re.sub(r"\D", "", m)
        # Skip if it looks like a year range (≤8 digits and all in 1900-2100 range)
        if len(digits_only) <= 8:
            continue
        return m.strip()
    return "Not Found"


def parse_links(text: str) -> tuple[str, str]:
    github   = re.findall(r"https?://github\.com/[\w\-]+(?:/[\w\-\.]+)*", text)
    linkedin = re.findall(
        r"https?://(?:www\.)?linkedin\.com/in/[\w\-]+/?", text
    )
    return (github[0] if github else ""), (linkedin[0] if linkedin else "")


def extract_skills_section(text: str) -> str:
    """Extract only the Skills section text."""
    lines = text.split("\n")
    skill_header = re.compile(
        r"^\s*(technical\s+skills?|skills?|core\s+competencies|"
        r"key\s+skills?|technologies|tech\s+stack|"
        r"tools?\s*(?:&|and)\s*technologies?|expertise)\s*:?\s*$",
        re.IGNORECASE,
    )
    stop_header = re.compile(
        r"^\s*(education|experience|projects?|internship|work|certif|"
        r"achievement|awards?|publications?|references?|languages?|"
        r"hobbies|interests?|summary|objective|profile|about)\s*:?\s*$",
        re.IGNORECASE,
    )
    in_skills = False
    collected: list[str] = []
    for line in lines:
        stripped = line.strip()
        if not in_skills:
            if skill_header.match(stripped):
                in_skills = True
        else:
            if stripped and stop_header.match(stripped):
                break
            collected.append(stripped.lower())
    return " ".join(collected)


def parse_skills(text: str) -> list[str]:
    skills_text = extract_skills_section(text)
    # FIX: only fall back to full text if skills section truly empty
    search_text = (
        skills_text if len(skills_text.strip()) > 20 else text.lower()
    )
    found: set[str] = set()
    for skill in SKILLS_DB:
        pattern = r"(?<![a-zA-Z])" + re.escape(skill) + r"(?![a-zA-Z])"
        if re.search(pattern, search_text, re.IGNORECASE):
            found.add(skill)
    return sorted(found)


def parse_experience(text_lower: str) -> float:
    """
    FIX: Handle 'Present', 'present', 'current', 'now' as CURRENT_YEAR.
    Also handles en-dash, em-dash, hyphen, 'to'.
    """
    # Replace present/current/now with current year
    normalized = re.sub(
        r"\b(present|current|now|till\s+date|to\s+date)\b",
        str(CURRENT_YEAR),
        text_lower,
    )

    date_ranges = re.findall(
        r"(\d{4})\s*(?:–|—|−|-|to)\s*(\d{4})", normalized
    )
    max_exp = 0.0
    for start, end in date_ranges:
        s, e = int(start), int(end)
        # Sanity check: valid year range
        if 1990 <= s <= CURRENT_YEAR and s < e <= CURRENT_YEAR + 1:
            max_exp = max(max_exp, e - s)

    if max_exp == 0 and "intern" in text_lower:
        return 0.5
    return max_exp


def parse_projects(lines: list[str]) -> list[str]:
    """
    FIX: Look for project TITLES — lines with meaningful content,
    not just lines that start with 'project'.
    Strategy: scan for project section, collect titled lines.
    """
    project_header = re.compile(
        r"^\s*(projects?|personal\s+projects?|academic\s+projects?|"
        r"key\s+projects?)\s*:?\s*$",
        re.IGNORECASE,
    )
    stop_header = re.compile(
        r"^\s*(education|experience|skills?|certif|achievement|"
        r"awards?|references?|languages?|hobbies|interests?|"
        r"summary|objective|profile|about|internship|work)\s*:?\s*$",
        re.IGNORECASE,
    )

    # Method 1: Extract from Projects section
    in_proj = False
    titles: list[str] = []
    for line in lines:
        stripped = line.strip()
        if not in_proj:
            if project_header.match(stripped):
                in_proj = True
        else:
            if stripped and stop_header.match(stripped):
                break
            clean = re.sub(r"^[\-\*\•\–\d\.]+\s*", "", stripped).strip()
            # A project title: reasonable length, not a sentence
            if (
                10 < len(clean) < 80
                and clean.lower() not in _FALSE_PROJECT_WORDS
                and not clean.lower().startswith(("the ", "a ", "an "))
                and sum(1 for c in clean if c.isupper()) >= 1  # has uppercase
            ):
                titles.append(clean)

    # Method 2: Fallback — bullet lines mentioning "project"
    if not titles:
        for line in lines:
            stripped = line.strip()
            if stripped.startswith(("•", "-", "*", "–")):
                if "project" in stripped.lower():
                    clean = re.sub(r"^[\-\*\•\–]\s*", "", stripped).strip()
                    if 10 < len(clean) < 100:
                        titles.append(clean)

    # Deduplicate preserving order
    seen: set[str] = set()
    unique: list[str] = []
    for t in titles:
        key = t.lower()[:40]
        if key not in seen:
            seen.add(key)
            unique.append(t)
    return unique[:5]


def parse_certifications(text: str) -> list[str]:
    certs: list[str] = []
    lines = text.split("\n")
    cert_header = re.compile(
        r"^\s*(certifications?|certificates?|courses?|licenses?|"
        r"online\s+courses?|professional\s+development)\s*:?\s*$",
        re.IGNORECASE,
    )
    stop_header = re.compile(
        r"^\s*(education|experience|projects?|skills?|achievements?|"
        r"awards?|languages?|hobbies|interests?|references?|"
        r"summary|objective|profile|about)\s*:?\s*$",
        re.IGNORECASE,
    )
    in_section = False
    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        if cert_header.match(stripped):
            in_section = True
            continue
        if in_section:
            if stop_header.match(stripped):
                break
            clean = re.sub(r"^[\-\*\•\–]\s*", "", stripped).strip()
            if len(clean) > 8:
                certs.append(clean)
    return certs[:6]


# ─────────────────────────────────────────────
# ROLE DETECTION  (weighted: skills 60% + context 40%)
# ─────────────────────────────────────────────
def detect_role(skills: list[str], text_lower: str) -> tuple[str, int]:
    skill_set = set(skills)
    weighted: dict[str, float] = {}

    for role, role_skills in ROLE_SKILLS.items():
        matched  = sum(1 for s in role_skills if s in skill_set)
        max_s    = len(role_skills) or 1
        skill_sc = matched / max_s * 60

        ctx_kws  = ROLE_CONTEXT_KEYWORDS.get(role, [])
        max_c    = len(ctx_kws) or 1
        ctx_hits = sum(1 for kw in ctx_kws if kw in text_lower)
        ctx_sc   = min(ctx_hits / max_c * 40, 40)

        weighted[role] = round(skill_sc + ctx_sc, 2)

    best       = max(weighted, key=lambda r: weighted[r])
    confidence = min(round(weighted[best]), 100)

    if confidence < 15:
        return "General Role (Add More Skills)", confidence
    return best, confidence


# ─────────────────────────────────────────────
# ATS SCORE
# ─────────────────────────────────────────────
def ats_score(
    skills: list[str],
    projects: list[str],
    experience: float,
    github: str,
    linkedin: str,
    name: str,
    email: str,
    certs: list[str],
) -> int:
    s = 0
    s += min(len(skills)   * 4, 25)   # max 25
    s += min(len(projects) * 8, 20)   # max 20
    # FIX: intern (0.5 yr) → 4 pts, 1yr → 8, 2yr → 16, cap 20
    s += min(int(experience * 8), 20) # max 20
    s += 8  if github   else 0
    s += 7  if linkedin else 0
    s += 10 if (name != "Not Found" and email != "Not Found") else (
          5 if (name != "Not Found" or email != "Not Found") else 0
    )
    s += min(len(certs) * 5, 10)      # max 10
    return min(s, 100)


# ─────────────────────────────────────────────
# SMART SUGGESTIONS
# ─────────────────────────────────────────────
def build_suggestions(
    skills: list[str],
    projects: list[str],
    experience: float,
    github: str,
    linkedin: str,
    score: int,
    role: str,
    certs: list[str],
) -> list[dict]:
    sugs: list[dict] = []
    skill_set = set(skills)

    # Missing role-specific skills
    if role in ROLE_SKILLS:
        missing = [s for s in ROLE_SKILLS[role] if s not in skill_set]
        if missing:
            sugs.append({
                "level": "critical",
                "title": f"Missing key skills for {role}",
                "detail": (
                    f"Add these to your Skills section: "
                    f"<b>{', '.join(missing[:5])}</b>. "
                    "ATS systems filter resumes by these keywords."
                ),
            })

    # Skills count
    if len(skills) < 6:
        sugs.append({
            "level": "critical",
            "title": "Too few skills listed",
            "detail": (
                f"Only <b>{len(skills)}</b> skill(s) detected. "
                "ATS expects 8–15. Add a dedicated 'Technical Skills' section."
            ),
        })
    elif len(skills) < 10:
        sugs.append({
            "level": "warn",
            "title": "Add more skills",
            "detail": (
                f"<b>{len(skills)}</b> skills found. "
                "Aim for 10+ relevant technologies for better ATS ranking."
            ),
        })

    # Projects
    if len(projects) == 0:
        sugs.append({
            "level": "critical",
            "title": "No projects detected",
            "detail": (
                "Add 2–3 projects with: tech stack used + measurable outcome "
                "(e.g., 'Built ML model achieving 92% accuracy')."
            ),
        })
    elif len(projects) < 2:
        sugs.append({
            "level": "warn",
            "title": "Add more projects",
            "detail": "Only 1 project found. Recruiters expect 2–3 with clear outcomes.",
        })

    # Experience
    if experience == 0:
        sugs.append({
            "level": "critical",
            "title": "No work experience found",
            "detail": (
                "Add internship, freelance, or part-time work. "
                "Even 3 months significantly improves ATS score."
            ),
        })
    elif experience < 1:
        sugs.append({
            "level": "warn",
            "title": "Experience is short",
            "detail": (
                f"Only <b>{experience}</b> year(s) found. "
                "Supplement with strong projects and certifications."
            ),
        })

    # Links
    if not github:
        sugs.append({
            "level": "warn",
            "title": "GitHub profile missing",
            "detail": (
                "Add your GitHub URL. Tech recruiters check it "
                "directly to evaluate your code quality."
            ),
        })
    if not linkedin:
        sugs.append({
            "level": "warn",
            "title": "LinkedIn profile missing",
            "detail": (
                "LinkedIn URL increases callback rate by 30%+. "
                "Ensure your profile matches your resume."
            ),
        })

    # Certifications
    if not certs:
        sugs.append({
            "level": "warn",
            "title": "No certifications mentioned",
            "detail": (
                "Add certifications like: Google Data Analytics, "
                "AWS Cloud Practitioner, Coursera ML, Meta Front-End Developer."
            ),
        })

    # Overall score feedback
    if score >= 85:
        sugs.append({
            "level": "good",
            "title": "Strong resume overall! 🎉",
            "detail": (
                f"ATS score <b>{score}/100</b>. "
                "Now tailor it to each specific job description for best results."
            ),
        })
    elif score >= 60:
        sugs.append({
            "level": "warn",
            "title": "Resume is decent — polish it further",
            "detail": (
                f"Score: <b>{score}/100</b>. Focus on adding missing skills, "
                "quantified project outcomes, and certifications."
            ),
        })
    else:
        sugs.append({
            "level": "critical",
            "title": "Resume needs major improvements",
            "detail": (
                f"Score: <b>{score}/100</b>. Priority actions: "
                "① Add Skills section ② Add 2+ projects with outcomes "
                "③ Include all contact details ④ Add certifications."
            ),
        })

    return sugs


# ─────────────────────────────────────────────
# MISSING DETAILS
# ─────────────────────────────────────────────
def build_missing(
    name: str,
    email: str,
    phone: str,
    github: str,
    linkedin: str,
    skills: list[str],
    projects: list[str],
    experience: float,
    certs: list[str],
) -> list[str]:
    m: list[str] = []
    if name  == "Not Found": m.append("Full name not detected — place it at the very top")
    if email == "Not Found": m.append("Email address is missing")
    if phone == "Not Found": m.append("Phone number is missing")
    if not github:           m.append("GitHub profile URL not found")
    if not linkedin:         m.append("LinkedIn profile URL not found")
    if len(skills) < 3:     m.append("Skills section missing or too sparse (< 3 skills)")
    if len(projects) == 0:  m.append("Projects section not found")
    if experience == 0:     m.append("Work / internship experience not found")
    if not certs:           m.append("No certifications mentioned")
    return m


# ─────────────────────────────────────────────
# DOWNLOAD REPORT
# ─────────────────────────────────────────────
def build_text_report(
    name: str, email: str, phone: str,
    github: str, linkedin: str,
    skills: list[str], projects: list[str],
    experience: float, certs: list[str],
    role: str, conf: int, score: int,
    suggestions: list[dict], missing: list[str],
) -> str:
    lines = [
        "=" * 55,
        "        AI RESUME ANALYZER — REPORT",
        "=" * 55,
        "",
        f"  ATS Score       : {score}/100",
        f"  Detected Role   : {role}  (Confidence: {conf}%)",
        "",
        "── CONTACT INFO ──────────────────────────────────",
        f"  Name    : {name}",
        f"  Email   : {email}",
        f"  Phone   : {phone}",
        f"  GitHub  : {github  or 'Not Found'}",
        f"  LinkedIn: {linkedin or 'Not Found'}",
        "",
        "── SKILLS FOUND ──────────────────────────────────",
        f"  {', '.join(skills) if skills else 'None detected'}",
        "",
        "── PROJECTS ──────────────────────────────────────",
    ]
    if projects:
        for p in projects:
            lines.append(f"  • {p}")
    else:
        lines.append("  None detected")

    lines += [
        "",
        "── CERTIFICATIONS ────────────────────────────────",
    ]
    if certs:
        for c in certs:
            lines.append(f"  • {c}")
    else:
        lines.append("  None detected")

    lines += [
        "",
        f"── EXPERIENCE ────── {experience} year(s) ─────────────────",
        "",
        "── MISSING DETAILS ───────────────────────────────",
    ]
    if missing:
        for idx, item in enumerate(missing, 1):
            lines.append(f"  {idx}. {item}")
    else:
        lines.append("  Nothing major missing ✓")

    lines += [
        "",
        "── SUGGESTIONS ───────────────────────────────────",
    ]
    for idx, sug in enumerate(suggestions, 1):
        lvl = sug["level"].upper()
        # Strip simple HTML tags for plain text
        detail = re.sub(r"<[^>]+>", "", sug["detail"])
        lines.append(f"  {idx}. [{lvl}] {sug['title']}")
        lines.append(f"     {detail}")
        lines.append("")

    lines += ["=" * 55, "  Generated by AI Resume Analyzer v7", "=" * 55]
    return "\n".join(lines)


# ─────────────────────────────────────────────
# CHART  (lazy plotly)
# ─────────────────────────────────────────────
def make_chart(
    skill_count: int,
    experience: float,
    project_count: int,
    cert_count: int,
):
    go = _load_plotly()
    labels = ["Skills", "Experience\n(yrs)", "Projects", "Certifications"]
    values = [skill_count, round(experience, 1), project_count, cert_count]
    colors = ["#4facfe", "#43e97b", "#f7971e", "#a18cd1"]

    fig = go.Figure(go.Bar(
        x=labels, y=values,
        marker_color=colors,
        text=values,
        textposition="outside",
        cliponaxis=False,
    ))
    fig.update_layout(
        margin=dict(t=30, b=20, l=10, r=10),
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        yaxis=dict(showgrid=False, zeroline=False, visible=False),
        xaxis=dict(tickfont=dict(size=12, color="rgba(255,255,255,0.8)")),
        height=290,
        bargap=0.35,
    )
    return fig


# ─────────────────────────────────────────────
# MAIN UI
# ─────────────────────────────────────────────
st.title("📄 AI Resume Analyzer")
st.caption(
    "Upload your resume (PDF or image) and get instant ATS score, "
    "skill analysis, role detection, and improvement tips."
)

uploaded_file = st.file_uploader(
    "Upload Resume (PDF, PNG, JPG)",
    type=["pdf", "png", "jpg", "jpeg"],
    label_visibility="visible",
)

if uploaded_file:
    if st.button("🔍 Analyze Resume", type="primary"):

        file_bytes = uploaded_file.read()

        # ── Progress indicator ──
        progress_placeholder = st.empty()

        def show_step(msg: str, done: bool = False):
            cls  = "step-done" if done else "step-bar"
            icon = "✓" if done else "⟳"
            progress_placeholder.markdown(
                f"<div class='{cls}'>{icon} {msg}</div>",
                unsafe_allow_html=True,
            )

        show_step("Reading file...")
        raw_text, err = extract_text(file_bytes, uploaded_file.type)

        if err or not raw_text:
            progress_placeholder.empty()
            st.error(
                f"Could not extract text from the file. "
                f"Please upload a clearer PDF or image.\n\n"
                f"{'Error: ' + err if err else ''}"
            )
        else:
            show_step("File read ✓  —  Analyzing...", done=True)

            text_lower = raw_text.lower()
            lines      = [l.strip() for l in raw_text.split("\n") if l.strip()]

            name             = parse_name(lines)
            email            = parse_email(raw_text)
            phone            = parse_phone(raw_text)
            github, linkedin = parse_links(raw_text)
            skills           = parse_skills(raw_text)
            experience       = parse_experience(text_lower)
            projects         = parse_projects(lines)
            certs            = parse_certifications(raw_text)
            role, conf       = detect_role(skills, text_lower)
            score            = ats_score(
                skills, projects, experience,
                github, linkedin, name, email, certs,
            )
            suggestions = build_suggestions(
                skills, projects, experience,
                github, linkedin, score, role, certs,
            )
            missing = build_missing(
                name, email, phone, github, linkedin,
                skills, projects, experience, certs,
            )

            progress_placeholder.empty()

            # ══════════════════════════════════════════════
            # TOP ROW
            # ══════════════════════════════════════════════
            col1, col2 = st.columns([1, 2], gap="large")

            with col1:
                # ATS Score
                st.subheader("ATS Score")
                color = (
                    "#e53935" if score < 50
                    else "#f57c00" if score < 75
                    else "#43a047"
                )
                st.markdown(
                    f"<p class='score-badge' style='color:{color}'>"
                    f"{score}"
                    f"<span style='font-size:22px;color:#888'>/100</span>"
                    f"</p>",
                    unsafe_allow_html=True,
                )
                st.progress(score / 100)
                st.caption(
                    "🔴 < 50  Poor"
                    "  |  🟡 50–74  Fair"
                    "  |  🟢 75+  Good"
                )

                # Role
                st.subheader("Detected Role")
                st.success(f"**{role}**")
                st.caption(f"Confidence: {conf}%")

                # Contact
                st.subheader("Contact Info")
                for label, value in [
                    ("👤 Name",  name),
                    ("✉ Email",  email),
                    ("📞 Phone", phone),
                ]:
                    st.markdown(
                        f"<div class='info-row'>"
                        f"<b>{label}:</b>&nbsp;{value}"
                        f"</div>",
                        unsafe_allow_html=True,
                    )

                # Links
                st.subheader("Links")
                if github:
                    st.markdown(f"🔗 [GitHub]({github})")
                else:
                    st.write("GitHub: Not Found")

                if linkedin:
                    st.markdown(f"🔗 [LinkedIn]({linkedin})")
                else:
                    st.write("LinkedIn: Not Found")

            with col2:
                # Skills
                st.subheader("Skills Detected")
                st.caption(
                    f"{len(skills)} skill(s) found "
                    f"{'from Skills section' if len(skills) > 0 else ''}"
                )
                if skills:
                    st.markdown(
                        "".join(
                            f"<span class='skill-tag'>{s}</span>"
                            for s in skills
                        ),
                        unsafe_allow_html=True,
                    )
                else:
                    st.warning(
                        "No skills detected. "
                        "Add a 'Technical Skills' section to your resume."
                    )

                # Projects
                st.subheader("Projects Detected")
                if projects:
                    for p in projects:
                        st.write(f"• {p}")
                else:
                    st.info(
                        "No projects found. "
                        "Add a 'Projects' section with clear titles."
                    )

                # Metrics chart
                st.subheader("Resume Metrics")
                st.plotly_chart(
                    make_chart(
                        len(skills), experience,
                        len(projects), len(certs),
                    ),
                    use_container_width=True,
                )

            st.divider()

            # ══════════════════════════════════════════════
            # BOTTOM ROW
            # ══════════════════════════════════════════════
            col3, col4 = st.columns(2, gap="large")

            with col3:
                st.subheader("💡 Smart Suggestions")
                if not suggestions:
                    st.success("No major issues — resume looks solid! ✅")
                else:
                    for sug in suggestions:
                        css = (
                            "sug-card critical"
                            if sug["level"] == "critical"
                            else "sug-card good"
                            if sug["level"] == "good"
                            else "sug-card"
                        )
                        st.markdown(
                            f"<div class='{css}'>"
                            f"<div class='sug-title'>{sug['title']}</div>"
                            f"{sug['detail']}"
                            f"</div>",
                            unsafe_allow_html=True,
                        )

            with col4:
                st.subheader("⚠ Missing Details")
                if not missing:
                    st.success("No major details missing ✅")
                else:
                    st.markdown(
                        "<div class='missing-box'>"
                        + "".join(
                            f"<div class='missing-item'>⚠ {m}</div>"
                            for m in missing
                        )
                        + "</div>",
                        unsafe_allow_html=True,
                    )

                # Certifications
                if certs:
                    st.subheader("🏅 Certifications Found")
                    for c in certs:
                        st.write(f"• {c}")

            st.divider()

            # ══════════════════════════════════════════════
            # DOWNLOAD REPORT
            # ══════════════════════════════════════════════
            report_text = build_text_report(
                name, email, phone, github, linkedin,
                skills, projects, experience, certs,
                role, conf, score, suggestions, missing,
            )
            st.download_button(
                label="📥 Download Full Report (.txt)",
                data=report_text,
                file_name="resume_analysis_report.txt",
                mime="text/plain",
            )