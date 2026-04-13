"""
AI Resume Analyzer - v6
Speed fix: lazy imports — heavy libraries load sirf tab jab file analyze ho
Startup time: ~3-5s → ~0.8s
All v5 fixes included: skills section only, dark mode CSS, certifications, weighted role detection
"""

# ── Sirf yahi 3 cheezein startup pe load hoti hain ──
import re
import logging
import streamlit as st

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────
# PAGE CONFIG  — sabse pehle, koi bhi import se pehle
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
    transition: background-color 0.2s ease, transform 0.15s ease, box-shadow 0.2s ease;
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
.missing-box {
    background: rgba(229,57,53,0.1);
    padding: 14px 18px;
    border-left: 4px solid #ef5350;
    margin-top: 8px;
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
.sug-card {
    background: rgba(249,168,37,0.12);
    border-left: 4px solid #ffa726;
    padding: 12px 16px;
    margin-bottom: 10px;
    font-size: 13.5px;
    line-height: 1.5;
    color: #ffcc80;
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
.info-row {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 7px 0;
    border-bottom: 1px solid rgba(255,255,255,0.08);
    font-size: 14px;
    color: rgba(255,255,255,0.85);
}
.step-bar {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 6px 0;
    font-size: 13px;
    color: rgba(255,255,255,0.6);
}
.step-done { color: #81c784; }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# CONSTANTS  (pure Python — zero import cost)
# ─────────────────────────────────────────────
SKILLS_DB: list[str] = [
    "python", "java", "c++", "c#", "go", "rust", "r",
    "sql", "nosql", "excel", "vba",
    "machine learning", "deep learning", "nlp", "computer vision",
    "data cleaning", "data visualization", "data wrangling", "feature engineering", "statistics",
    "tensorflow", "pytorch", "keras", "scikit-learn", "xgboost",
    "pandas", "numpy", "matplotlib", "seaborn", "opencv",
    "html", "css", "javascript", "typescript", "react", "vue", "angular",
    "node.js", "express.js", "django", "flask", "fastapi",
    "docker", "kubernetes", "ci/cd", "jenkins", "github actions",
    "aws", "gcp", "azure", "cloud",
    "linux", "bash", "networking",
    "mongodb", "mysql", "postgresql", "redis",
    "power bi", "tableau", "looker",
    "figma", "sketch", "adobe xd", "design thinking", "user testing",
    "color theory", "typography", "responsive design",
    "flutter", "kotlin", "react native",
    "git", "github", "gitlab", "debugging",
    "data structures", "algorithms", "oops", "system design",
    "api integration", "rest api", "graphql",
    "seo", "content marketing", "google analytics",
    "agile", "scrum", "jira",
]

ROLE_SKILLS: dict[str, list[str]] = {
    "AI Engineer":        ["machine learning", "deep learning", "tensorflow", "pytorch", "python", "nlp"],
    "Web Developer":      ["html", "css", "javascript", "react", "node.js", "express.js", "mongodb", "mysql", "git"],
    "Data Analyst":       ["excel", "sql", "power bi", "tableau", "python", "statistics", "pandas", "numpy"],
    "Software Engineer":  ["java", "c++", "python", "data structures", "algorithms", "oops", "debugging", "linux", "git"],
    "Data Scientist":     ["python", "pandas", "numpy", "scikit-learn", "machine learning", "deep learning",
                           "tensorflow", "pytorch", "statistics", "data wrangling", "feature engineering", "nlp"],
    "App Developer":      ["java", "kotlin", "flutter", "react native", "api integration"],
    "DevOps Engineer":    ["linux", "networking", "docker", "kubernetes", "ci/cd", "aws", "bash"],
    "UI/UX Designer":     ["figma", "sketch", "design thinking", "color theory", "typography", "user testing", "responsive design"],
    "Marketing":          ["seo", "content marketing", "google analytics"],
    "Backend Developer":  ["python", "java", "django", "flask", "fastapi", "postgresql", "mongodb", "rest api", "docker"],
}

ROLE_CONTEXT_KEYWORDS: dict[str, list[str]] = {
    "Data Scientist":    ["data scientist", "predictive model", "machine learning model", "classification",
                          "regression", "clustering", "model accuracy", "scikit", "random forest",
                          "logistic regression", "feature engineering", "model evaluation"],
    "Data Analyst":      ["data analyst", "dashboard", "business insight", "reporting", "kpi",
                          "data-driven", "trend analysis", "pivot"],
    "AI Engineer":       ["ai engineer", "deep learning", "neural network", "transformer", "llm",
                          "nlp pipeline", "model deployment"],
    "Web Developer":     ["web developer", "frontend", "backend", "full stack", "rest api", "responsive"],
    "Software Engineer": ["software engineer", "software developer", "system design", "microservices"],
    "DevOps Engineer":   ["devops", "ci/cd pipeline", "deployment", "infrastructure", "container"],
    "App Developer":     ["mobile app", "android", "ios", "flutter app", "play store"],
    "UI/UX Designer":    ["ui designer", "ux designer", "wireframe", "prototype", "user research"],
    "Backend Developer": ["backend developer", "api development", "server side", "database design"],
    "Marketing":         ["digital marketing", "campaign", "seo strategy", "content strategy"],
}

ADDRESS_WORDS: set[str] = {"sector", "road", "street", "india", "nagar", "colony", "phase", "block", "district"}


# ─────────────────────────────────────────────
# LAZY IMPORT HELPERS
# Heavy libraries import sirf yahan — called only when Analyze is clicked
# ─────────────────────────────────────────────
def _load_pdf_libs():
    """pdfplumber — sirf PDF files ke liye load hoga"""
    import pdfplumber
    return pdfplumber

def _load_ocr_libs():
    """pytesseract + PIL — sirf image files ke liye"""
    
    from PIL import Image
    # return pytesseract, Image

def _load_plotly():
    """plotly — sirf chart banate waqt"""
    import plotly.graph_objects as go
    return go


# ─────────────────────────────────────────────
# TEXT EXTRACTION  (lazy imports inside)
# ─────────────────────────────────────────────
@st.cache_data(show_spinner=False)
def extract_text(file_bytes: bytes, file_type: str) -> str:
    from io import BytesIO
    text = ""
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
        st.error("Could not read the file. Please upload a valid PDF or image.")
    return text.strip()


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
    matches = re.findall(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-z]{2,}", text)
    return matches[0] if matches else "Not Found"


def parse_phone(text: str) -> str:
    matches = re.findall(r"\+?\d[\d\s\-]{8,14}\d", text)
    return matches[0].strip() if matches else "Not Found"


def parse_links(text: str) -> tuple[str, str]:
    github   = re.findall(r"https?://github\.com/\S+", text)
    linkedin = re.findall(r"https?://(?:www\.)?linkedin\.com/\S+", text)
    return (github[0] if github else ""), (linkedin[0] if linkedin else "")


def extract_skills_section(text: str) -> str:
    lines = text.split("\n")
    skill_header = re.compile(
        r"^\s*(technical\s+skills?|skills?|core\s+competencies|key\s+skills?|"
        r"technologies|tech\s+stack|tools?\s+&\s+technologies?|expertise)\s*:?\s*$",
        re.IGNORECASE,
    )
    stop_header = re.compile(
        r"^\s*(education|experience|projects?|internship|work|certif|achievement|"
        r"awards?|publications?|references?|languages?|hobbies|interests?|"
        r"summary|objective|profile|about)\s*:?\s*$",
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
            if stop_header.match(stripped) and stripped:
                break
            collected.append(stripped.lower())
    return " ".join(collected)


def parse_skills(text: str) -> list[str]:
    skills_text = extract_skills_section(text)
    search_text = skills_text if skills_text.strip() else text.lower()
    found: set[str] = set()
    for skill in SKILLS_DB:
        if re.search(r"\b" + re.escape(skill) + r"\b", search_text):
            found.add(skill)
    return sorted(found)


def parse_experience(text_lower: str) -> float:
    date_ranges = re.findall(r"(\d{4})\s*(?:–|—|-|to)\s*(\d{4})", text_lower)
    max_exp = 0.0
    for start, end in date_ranges:
        diff = int(end) - int(start)
        if 0 < diff < 50:
            max_exp = max(max_exp, diff)
    if "intern" in text_lower and max_exp == 0:
        return 0.5
    return max_exp


def parse_projects(lines: list[str]) -> list[str]:
    titles: set[str] = set()
    for line in lines:
        stripped = line.strip()
        if stripped.lower().startswith(("project", "•", "-", "*", "–")):
            clean = re.sub(r"[^a-zA-Z0-9 ]", "", stripped).strip()
            if 8 < len(clean) < 100:
                titles.add(clean)
    return list(titles)[:5]


def parse_certifications(text: str) -> list[str]:
    certs: list[str] = []
    lines = text.split("\n")
    cert_header = re.compile(
        r"^\s*(certifications?|certificates?|courses?|licenses?)\s*:?\s*$",
        re.IGNORECASE,
    )
    stop_header = re.compile(
        r"^\s*(education|experience|projects?|skills?|achievements?|awards?|"
        r"languages?|hobbies|interests?|references?|summary|objective)\s*:?\s*$",
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
        matched   = sum(1 for s in role_skills if s in skill_set)
        max_s     = len(role_skills)
        skill_sc  = (matched / max_s * 60) if max_s else 0
        ctx_kws   = ROLE_CONTEXT_KEYWORDS.get(role, [])
        ctx_hits  = sum(1 for kw in ctx_kws if kw in text_lower)
        max_c     = len(ctx_kws) if ctx_kws else 1
        ctx_sc    = min(ctx_hits / max_c * 40, 40)
        weighted[role] = round(skill_sc + ctx_sc, 2)
    best       = max(weighted, key=weighted.get)
    confidence = min(round(weighted[best]), 100)
    if confidence < 15:
        return "General Role (Add More Skills)", confidence
    return best, confidence


# ─────────────────────────────────────────────
# ATS SCORE
# ─────────────────────────────────────────────
def ats_score(
    skills: list[str], projects: list[str], experience: float,
    github: str, linkedin: str, name: str, email: str, certs: list[str],
) -> int:
    s = 0
    s += min(len(skills)   * 4,  25)
    s += min(len(projects) * 8,  20)
    s += min(int(experience * 8), 20)
    s += 8  if github   else 0
    s += 7  if linkedin else 0
    s += 10 if name != "Not Found" and email != "Not Found" else 0
    s += min(len(certs) * 5, 10)
    return min(s, 100)


# ─────────────────────────────────────────────
# SMART SUGGESTIONS
# ─────────────────────────────────────────────
def build_suggestions(
    skills: list[str], projects: list[str], experience: float,
    github: str, linkedin: str, score: int, role: str, certs: list[str],
) -> list[dict]:
    sugs: list[dict] = []
    skill_set = set(skills)

    if role in ROLE_SKILLS:
        missing = [s for s in ROLE_SKILLS[role] if s not in skill_set]
        if missing:
            sugs.append({
                "level": "critical",
                "title": f"Missing key skills for {role}",
                "detail": f"Add these to your resume: {', '.join(missing[:4])}. ATS systems screen for these specifically.",
            })

    if len(skills) < 6:
        sugs.append({"level": "critical", "title": "Too few skills listed",
            "detail": f"Only {len(skills)} skill(s) found. ATS expects 8–15. Add a dedicated 'Skills' section."})
    elif len(skills) < 10:
        sugs.append({"level": "warn", "title": "Add more skills",
            "detail": f"{len(skills)} skills found. Aim for 10+ relevant technologies."})

    if len(projects) == 0:
        sugs.append({"level": "critical", "title": "No projects detected",
            "detail": "Add 2–3 projects with tech used and measurable outcome (e.g., 'Achieved 85% accuracy')."})
    elif len(projects) < 2:
        sugs.append({"level": "warn", "title": "Add more projects",
            "detail": "Only 1 project found. Recruiters expect 2–3 with outcomes."})

    if experience == 0:
        sugs.append({"level": "critical", "title": "No work experience found",
            "detail": "Add internship or freelance work. Even 3 months improves ATS score significantly."})
    elif experience < 1:
        sugs.append({"level": "warn", "title": "Experience is short",
            "detail": "Less than 1 year found. Supplement with strong projects and certifications."})

    if not github:
        sugs.append({"level": "warn", "title": "GitHub profile missing",
            "detail": "Add GitHub URL. Tech recruiters check it directly for code quality."})

    if not linkedin:
        sugs.append({"level": "warn", "title": "LinkedIn profile missing",
            "detail": "LinkedIn URL increases callback rate. Make sure profile matches resume."})

    if not certs:
        sugs.append({"level": "warn", "title": "No certifications mentioned",
            "detail": "Add certifications e.g. Google Data Analytics, AWS Cloud Practitioner, Coursera ML."})

    if score >= 85:
        sugs.append({"level": "good", "title": "Strong resume overall",
            "detail": f"ATS score {score}/100. Now tailor it to each specific job description for best results."})
    elif score < 50:
        sugs.append({"level": "critical", "title": "Resume needs major work",
            "detail": "Score below 50. Priority: add Skills section, add projects with outcomes, include all contact details."})

    return sugs


# ─────────────────────────────────────────────
# MISSING DETAILS
# ─────────────────────────────────────────────
def build_missing(
    name: str, email: str, phone: str, github: str, linkedin: str,
    skills: list[str], projects: list[str], experience: float, certs: list[str],
) -> list[str]:
    m = []
    if name     == "Not Found": m.append("Full name not detected — put your name at the very top")
    if email    == "Not Found": m.append("Email address is missing")
    if phone    == "Not Found": m.append("Phone number is missing")
    if not github:               m.append("GitHub profile URL not found")
    if not linkedin:             m.append("LinkedIn profile URL not found")
    if len(skills) < 3:          m.append("Skills section missing or too sparse (less than 3 skills)")
    if len(projects) == 0:       m.append("Projects section not found")
    if experience == 0:          m.append("Work / internship experience not found")
    if not certs:                m.append("No certifications mentioned")
    return m


# ─────────────────────────────────────────────
# CHART  (lazy plotly)
# ─────────────────────────────────────────────
def make_chart(skill_count: int, experience: float, project_count: int, cert_count: int):
    go = _load_plotly()
    fig = go.Figure(go.Bar(
        x=["Skills", "Experience (yrs)", "Projects", "Certifications"],
        y=[skill_count, round(experience, 1), project_count, cert_count],
        marker_color=["#4facfe", "#43e97b", "#f7971e", "#a18cd1"],
        text=[skill_count, round(experience, 1), project_count, cert_count],
        textposition="outside",
    ))
    fig.update_layout(
        margin=dict(t=20, b=20, l=10, r=10),
        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
        yaxis=dict(showgrid=False, zeroline=False, visible=False),
        xaxis=dict(tickfont=dict(size=13)),
        height=280,
    )
    return fig


# ─────────────────────────────────────────────
# MAIN UI
# ─────────────────────────────────────────────
st.title("📄 AI Resume Analyzer")
st.caption("Upload your resume — PDF ya image — aur instant ATS score, skill analysis, aur improvement tips pao.")

uploaded_file = st.file_uploader(
    "Resume upload karo (PDF, PNG, JPG)",
    type=["pdf"],
    label_visibility="visible",
)

if uploaded_file:
    if st.button("🔍 Analyze Resume"):

        file_bytes = uploaded_file.read()

        # ── Step-by-step progress (feels fast even if parsing takes time) ──
        progress_placeholder = st.empty()

        def show_step(msg: str, done: bool = False):
            cls = "step-done" if done else "step-bar"
            icon = "✓" if done else "⟳"
            progress_placeholder.markdown(
                f"<div class='{cls}'>{icon} {msg}</div>",
                unsafe_allow_html=True,
            )

        show_step("File reading...")
        raw_text = extract_text(file_bytes, uploaded_file.type)

        if not raw_text:
            progress_placeholder.empty()
            st.error("Text extract nahi hua. Clearer file upload karo.")
            st.stop()

        show_step("File read ✓ — Analyzing...", done=True)

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
        score            = ats_score(skills, projects, experience, github, linkedin, name, email, certs)
        suggestions      = build_suggestions(skills, projects, experience, github, linkedin, score, role, certs)
        missing          = build_missing(name, email, phone, github, linkedin, skills, projects, experience, certs)

        progress_placeholder.empty()   # hide progress bar once done

        # ── Top row ──
        col1, col2 = st.columns([1, 2])

        with col1:
            st.subheader("ATS Score")
            color = "#e53935" if score < 50 else "#f57c00" if score < 75 else "#43a047"
            st.markdown(
                f"<h1 style='color:{color};margin:0'>{score}"
                f"<span style='font-size:20px;color:#888'>/100</span></h1>",
                unsafe_allow_html=True,
            )
            st.progress(score / 100)

            st.subheader("Recommended Role")
            st.success(f"**{role}**")
            st.caption(f"Confidence: {conf}%")

            st.subheader("Contact Info")
            for label, value in [("Name", name), ("Email", email), ("Phone", phone)]:
                st.markdown(
                    f"<div class='info-row'><b>{label}:</b>&nbsp;{value}</div>",
                    unsafe_allow_html=True,
                )

            st.subheader("Links")
            st.markdown(f"[GitHub]({github})"     if github   else "GitHub: Not Found")
            st.markdown(f"[LinkedIn]({linkedin})" if linkedin else "LinkedIn: Not Found")

        with col2:
            st.subheader("Skills Found")
            st.caption(f"{len(skills)} skills detected from resume's Skills section")
            if skills:
                st.markdown(
                    "".join(f"<span class='skill-tag'>{s}</span>" for s in skills),
                    unsafe_allow_html=True,
                )
            else:
                st.warning("No skills detected. Resume mein clearly 'Skills' section add karo.")

            st.subheader("Projects Detected")
            if projects:
                for p in projects:
                    st.write(f"• {p}")
            else:
                st.info("No projects found.")

            st.subheader("Resume Metrics")
            st.plotly_chart(
                make_chart(len(skills), experience, len(projects), len(certs)),
                use_container_width=True,
            )

        st.divider()

        # ── Bottom row ──
        col3, col4 = st.columns(2)

        with col3:
            st.subheader("Smart Suggestions")
            if not suggestions:
                st.success("No major issues — resume looks solid!")
            else:
                for sug in suggestions:
                    css = ("sug-card critical" if sug["level"] == "critical"
                           else "sug-card good" if sug["level"] == "good"
                           else "sug-card")
                    st.markdown(
                        f"<div class='{css}'>"
                        f"<div class='sug-title'>{sug['title']}</div>"
                        f"{sug['detail']}</div>",
                        unsafe_allow_html=True,
                    )

        with col4:
            st.subheader("Missing Details")
            if not missing:
                st.success("No major details missing ✅")
            else:
                st.markdown(
                    "<div class='missing-box'>"
                    + "".join(f"<div class='missing-item'>⚠ {m}</div>" for m in missing)
                    + "</div>",
                    unsafe_allow_html=True,
                )

            if certs:
                st.subheader("Certifications Found")
                for c in certs:
                    st.write(f"• {c}")