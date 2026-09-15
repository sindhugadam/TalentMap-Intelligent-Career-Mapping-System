2# ================================================================
#  career_guidance.py  —  Career Guidance & Skill Recommendation
#  Libraries: re, collections, os, datetime, math  (all built-in)
# ================================================================
#
#  FEATURES:
#   1. Job Role Skill Database — 12 career roles with tiered skills
#   2. Skill Recommender       — recommends skills for a given role
#   3. Skill Gap Analyzer      — compares user skills vs role needs
#   4. Career Path Matcher     — ranks best-fit roles for a skill set
#   5. Learning Roadmap        — step-by-step priority skill plan
#   6. Industry Trend Scores   — demand weightings per skill
#   7. History Log             — saves all sessions to history.txt
#   8. Session Summary         — stats across the session
#
#  Run:  python career_guidance.py
# ================================================================

import re
import os
import math
from collections import Counter, defaultdict
from datetime import datetime

# ── Job Role Skill Database ──────────────────────────────────────
# Each role: essential (must-have), intermediate, advanced, tools
CAREER_DB = {
    "Software Engineer": {
        "essential":    ["python", "data structures", "algorithms", "oop",
                         "git", "problem solving", "debugging", "linux"],
        "intermediate": ["java", "c++", "rest api", "sql", "software design",
                         "unit testing", "agile", "code review"],
        "advanced":     ["system design", "microservices", "cloud", "ci/cd",
                         "docker", "kubernetes", "distributed systems"],
        "tools":        ["git", "jira", "vs code", "postman", "docker"],
        "demand": 95,
        "avg_salary": "6-20 LPA",
        "growth": "High",
    },
    "Data Scientist": {
        "essential":    ["python", "statistics", "machine learning", "data analysis",
                         "sql", "data visualization", "pandas", "numpy"],
        "intermediate": ["scikit-learn", "feature engineering", "hypothesis testing",
                         "r", "tableau", "exploratory data analysis", "matplotlib"],
        "advanced":     ["deep learning", "tensorflow", "pytorch", "nlp",
                         "big data", "spark", "model deployment", "mlops"],
        "tools":        ["jupyter", "tableau", "sql server", "git", "airflow"],
        "demand": 98,
        "avg_salary": "8-25 LPA",
        "growth": "Very High",
    },
    "Machine Learning Engineer": {
        "essential":    ["python", "machine learning", "linear algebra",
                         "statistics", "algorithms", "data preprocessing"],
        "intermediate": ["scikit-learn", "tensorflow", "feature engineering",
                         "model evaluation", "deep learning", "neural networks"],
        "advanced":     ["pytorch", "mlops", "model deployment", "docker",
                         "kubernetes", "computer vision", "nlp", "llm"],
        "tools":        ["jupyter", "mlflow", "docker", "git", "wandb"],
        "demand": 97,
        "avg_salary": "10-30 LPA",
        "growth": "Very High",
    },
    "Data Analyst": {
        "essential":    ["sql", "excel", "data analysis", "data visualization",
                         "statistics", "reporting", "critical thinking"],
        "intermediate": ["python", "tableau", "power bi", "data cleaning",
                         "pivot tables", "business intelligence", "dashboard"],
        "advanced":     ["r", "advanced sql", "etl", "predictive analytics",
                         "machine learning basics", "storytelling with data"],
        "tools":        ["excel", "tableau", "power bi", "sql server", "python"],
        "demand": 90,
        "avg_salary": "4-15 LPA",
        "growth": "High",
    },
    "Web Developer": {
        "essential":    ["html", "css", "javascript", "responsive design",
                         "git", "web development basics", "debugging"],
        "intermediate": ["react", "node.js", "rest api", "mongodb", "sql",
                         "typescript", "frontend", "backend"],
        "advanced":     ["next.js", "graphql", "docker", "ci/cd",
                         "web security", "performance optimization", "pwa"],
        "tools":        ["vs code", "git", "figma", "postman", "chrome devtools"],
        "demand": 88,
        "avg_salary": "4-18 LPA",
        "growth": "High",
    },
    "Cybersecurity Analyst": {
        "essential":    ["networking basics", "linux", "security fundamentals",
                         "ethical hacking", "risk assessment", "firewall"],
        "intermediate": ["penetration testing", "vulnerability assessment",
                         "siem", "incident response", "python scripting",
                         "network protocols", "encryption"],
        "advanced":     ["malware analysis", "threat intelligence", "forensics",
                         "red teaming", "zero trust", "cloud security"],
        "tools":        ["kali linux", "wireshark", "metasploit", "nmap", "splunk"],
        "demand": 93,
        "avg_salary": "6-22 LPA",
        "growth": "Very High",
    },
    "Cloud Engineer": {
        "essential":    ["cloud computing", "linux", "networking", "aws basics",
                         "storage", "virtualization", "scripting"],
        "intermediate": ["aws", "azure", "docker", "kubernetes", "terraform",
                         "infrastructure as code", "devops", "monitoring"],
        "advanced":     ["multi-cloud", "serverless", "cloud security",
                         "cost optimization", "site reliability engineering",
                         "service mesh", "gitops"],
        "tools":        ["aws console", "terraform", "docker", "kubernetes", "ansible"],
        "demand": 94,
        "avg_salary": "8-28 LPA",
        "growth": "Very High",
    },
    "Business Analyst": {
        "essential":    ["requirements gathering", "business analysis", "sql",
                         "excel", "communication", "stakeholder management",
                         "documentation", "process mapping"],
        "intermediate": ["agile", "scrum", "uml", "jira", "power bi",
                         "risk analysis", "project management", "wireframing"],
        "advanced":     ["strategic planning", "change management", "erp",
                         "advanced analytics", "machine learning basics"],
        "tools":        ["jira", "confluence", "excel", "power bi", "visio"],
        "demand": 85,
        "avg_salary": "5-18 LPA",
        "growth": "Moderate",
    },
    "DevOps Engineer": {
        "essential":    ["linux", "git", "scripting", "networking",
                         "ci/cd", "automation", "bash", "problem solving"],
        "intermediate": ["docker", "kubernetes", "jenkins", "ansible",
                         "terraform", "monitoring", "logging", "devops"],
        "advanced":     ["sre", "chaos engineering", "gitops", "service mesh",
                         "devsecops", "cloud native", "platform engineering"],
        "tools":        ["jenkins", "docker", "kubernetes", "prometheus", "grafana"],
        "demand": 93,
        "avg_salary": "7-25 LPA",
        "growth": "Very High",
    },
    "NLP Engineer": {
        "essential":    ["python", "machine learning", "text processing",
                         "statistics", "regular expressions", "linguistics basics"],
        "intermediate": ["nltk", "spacy", "transformers", "bert",
                         "sentiment analysis", "named entity recognition",
                         "deep learning", "scikit-learn"],
        "advanced":     ["llm", "fine-tuning", "huggingface", "information extraction",
                         "question answering", "text generation", "rag"],
        "tools":        ["jupyter", "huggingface", "spacy", "nltk", "pytorch"],
        "demand": 96,
        "avg_salary": "10-30 LPA",
        "growth": "Very High",
    },
    "UI/UX Designer": {
        "essential":    ["ui design", "ux research", "wireframing", "prototyping",
                         "user research", "design thinking", "typography",
                         "color theory"],
        "intermediate": ["figma", "adobe xd", "usability testing", "information architecture",
                         "responsive design", "design systems", "accessibility"],
        "advanced":     ["motion design", "interaction design", "design strategy",
                         "front-end basics", "data-driven design", "design ops"],
        "tools":        ["figma", "adobe xd", "sketch", "invision", "miro"],
        "demand": 87,
        "avg_salary": "4-18 LPA",
        "growth": "High",
    },
    "Product Manager": {
        "essential":    ["product strategy", "requirements gathering", "roadmapping",
                         "stakeholder management", "agile", "communication",
                         "market research", "prioritization"],
        "intermediate": ["sql", "data analysis", "user stories", "okrs",
                         "product analytics", "a/b testing", "go to market"],
        "advanced":     ["growth strategy", "pricing strategy", "ml product sense",
                         "platform thinking", "strategic planning"],
        "tools":        ["jira", "confluence", "mixpanel", "amplitude", "figma"],
        "demand": 88,
        "avg_salary": "10-35 LPA",
        "growth": "High",
    },
}

# ── Skill Demand Weights (industry trend scores 1-10) ────────────
SKILL_DEMAND = {
    "python": 10, "machine learning": 10, "deep learning": 10,
    "llm": 10, "cloud": 9, "docker": 9, "kubernetes": 9,
    "sql": 9, "data analysis": 9, "react": 8, "aws": 9,
    "tensorflow": 9, "pytorch": 9, "git": 8, "ci/cd": 8,
    "devops": 9, "nlp": 9, "transformers": 10, "bert": 9,
    "cybersecurity": 9, "penetration testing": 8,
    "data visualization": 8, "agile": 7, "excel": 6,
    "html": 6, "css": 6, "javascript": 8, "linux": 8,
    "statistics": 8, "algorithms": 8, "rest api": 8,
}

# ── Text Cleaner ─────────────────────────────────────────────────
def clean(text):
    return re.sub(r'\s+', ' ', text.lower()).strip()

# ── Skill Extractor from user input ──────────────────────────────
ALL_SKILLS = set()
for role in CAREER_DB.values():
    for tier in ["essential", "intermediate", "advanced", "tools"]:
        ALL_SKILLS.update(role[tier])

def parse_skills(text):
    """Extract known skills from comma/newline separated user input."""
    text_lower = clean(text)
    # split on commas, semicolons, newlines
    tokens = re.split(r'[,;\n]+', text_lower)
    found  = []
    for token in tokens:
        t = token.strip()
        if t in ALL_SKILLS:
            found.append(t)
        else:
            # partial match for multi-word skills
            for skill in ALL_SKILLS:
                if skill in t or t in skill:
                    found.append(skill)
                    break
    return sorted(set(found))

# ── Resume Skill Extractor (free-text) ───────────────────────────
# Build, once, a regex that finds any known skill as a whole token.
# Boundaries are alnum-aware so "r" won't match inside "react" and
# "git" won't match inside "digit", while still allowing skills that
# contain punctuation like "c++", "ci/cd", "node.js", "scikit-learn".
_SORTED_SKILLS = sorted(ALL_SKILLS, key=len, reverse=True)  # longest first
_SKILL_PATTERNS = [
    (skill, re.compile(r'(?<![a-z0-9])' + re.escape(skill) + r'(?![a-z0-9])'))
    for skill in _SORTED_SKILLS
]


def extract_skills_from_text(text):
    """Scan free-form resume text and return all known skills found."""
    blob = clean(text)
    found = []
    for skill, pattern in _SKILL_PATTERNS:
        if pattern.search(blob):
            found.append(skill)
    return sorted(set(found))


# ── Reusable Gap Computation ─────────────────────────────────────
def compute_gap(user_skills, role_name):
    """Full gap analysis used by the resume scanner (and reusable
    elsewhere). Returns coverage, readiness, have/missing tiers and a
    demand-sorted 3-phase roadmap. Coverage is measured across the
    essential + intermediate tiers."""
    role_data = CAREER_DB.get(role_name)
    if not role_data:
        return None

    essential    = [s.lower() for s in role_data.get("essential", [])]
    intermediate = [s.lower() for s in role_data.get("intermediate", [])]
    advanced     = [s.lower() for s in role_data.get("advanced", [])]
    user_set     = set(s.lower() for s in user_skills)

    have_essential    = [s for s in essential    if s in user_set]
    missing_essential = [s for s in essential    if s not in user_set]
    have_intermediate = [s for s in intermediate if s in user_set]
    missing_intermediate = [s for s in intermediate if s not in user_set]
    have_advanced     = [s for s in advanced     if s in user_set]

    total_required = len(essential) + len(intermediate)
    total_have     = len(have_essential) + len(have_intermediate)
    coverage = round((total_have / total_required) * 100, 1) if total_required else 0.0

    def level_for(pct):
        if pct >= 80:
            return "Advanced"
        if pct >= 60:
            return "Intermediate"
        if pct >= 35:
            return "Developing"
        return "Beginner"

    by_demand = lambda lst: sorted(lst, key=lambda x: SKILL_DEMAND.get(x, 5), reverse=True)

    return {
        "role"                : role_name,
        "user_skills"         : sorted(user_set),
        "coverage_percent"    : coverage,
        "readiness"           : level_for(coverage),
        "have_essential"      : have_essential,
        "missing_essential"   : missing_essential,
        "have_intermediate"   : have_intermediate,
        "missing_intermediate": missing_intermediate,
        "have_advanced"       : have_advanced,
        "missing_advanced"    : by_demand([s for s in advanced if s not in user_set]),
        "roadmap": {
            "Phase 1 - Foundation (Essential Skills)" : by_demand(missing_essential),
            "Phase 2 - Core Competency (Intermediate)": by_demand(missing_intermediate),
            "Phase 3 - Advanced Expertise"            : by_demand([s for s in advanced if s not in user_set]),
        },
        "_total_required"     : total_required,
        "_level_for"          : level_for,
    }


# ── Dynamic Skill-Up Plan ────────────────────────────────────────
# The timeline is NOT fixed. We estimate days per skill based on its
# tier (depth) with a small bump for very high-demand skills, then lay
# out real, sequential day ranges. Fewer gaps -> shorter plan; more
# gaps -> longer plan.
TIER_BASE_DAYS = {
    "essential"   : 6,   # foundational, learned fastest
    "intermediate": 9,   # role-productive depth
    "advanced"    : 12,  # specialist depth
}


def estimate_days(skill, tier):
    """Rough study-days estimate for one skill (steady part-time effort)."""
    base = TIER_BASE_DAYS.get(tier, 8)
    if SKILL_DEMAND.get(skill, 5) >= 9:   # hot/deep skills take a bit longer
        base += 2
    return base


def _build_phase(title, focus, skills, tier, start_day):
    """Lay out one phase with cumulative day ranges. Returns (phase, next_start_day)."""
    by_demand = sorted(skills, key=lambda x: SKILL_DEMAND.get(x, 5), reverse=True)
    items = []
    day = start_day
    for s in by_demand:
        d = estimate_days(s, tier)
        items.append({
            "skill"    : s,
            "demand"   : SKILL_DEMAND.get(s, 5),
            "days"     : d,
            "day_start": day,
            "day_end"  : day + d - 1,
        })
        day += d
    phase = {
        "title"    : title,
        "focus"    : focus,
        "skills"   : skills,          # raw list (for quick checks)
        "items"    : items,
        "day_start": start_day if items else None,
        "day_end"  : day - 1 if items else None,
        "phase_days": (day - start_day) if items else 0,
    }
    return phase, day


def skillup_plan(gap):
    """Build a phased plan whose length is computed from the actual
    skills to cover. Returns phases plus total day/week estimates."""
    if not gap:
        return None

    day = 1
    phases = []

    p1 = gap["missing_essential"]
    p2 = gap["missing_intermediate"]
    p3 = sorted(gap["missing_advanced"], key=lambda x: SKILL_DEMAND.get(x, 5), reverse=True)[:5]

    if p1:
        ph, day = _build_phase(
            "Foundation — close the essential gaps",
            "Non-negotiable, must-have skills recruiters screen for. "
            "Build a small project that uses each one.",
            p1, "essential", day)
        phases.append(ph)
    if p2:
        ph, day = _build_phase(
            "Core competency — become productive",
            "The day-to-day toolkit for the role. Ship one end-to-end "
            "piece of work using these.",
            p2, "intermediate", day)
        phases.append(ph)

    days_to_ready = day - 1   # finishing essentials + intermediates = job-ready

    if p3:
        ph, day = _build_phase(
            "Advanced edge — stand out",
            "Differentiators that separate you from other applicants. "
            "Highest-demand items first.",
            p3, "advanced", day)
        phases.append(ph)

    total_days = day - 1
    return {
        "phases"       : phases,
        "total_days"   : total_days,
        "total_weeks"  : math.ceil(total_days / 7) if total_days else 0,
        "days_to_ready": days_to_ready,
        "weeks_to_ready": math.ceil(days_to_ready / 7) if days_to_ready else 0,
    }


# ── Projected Readiness (the "after the plan" conclusion) ────────
def projected_after_plan(gap):
    """Estimate readiness assuming the learner completes the essential
    and intermediate parts of the plan."""
    if not gap:
        return None

    total_required = gap["_total_required"]
    # After plan: all essentials + all intermediates are covered.
    projected_have = (len(gap["have_essential"]) + len(gap["missing_essential"]) +
                      len(gap["have_intermediate"]) + len(gap["missing_intermediate"]))
    projected = round(min(projected_have, total_required) / total_required * 100, 1) if total_required else 0.0

    new_skills = gap["missing_essential"] + gap["missing_intermediate"]
    return {
        "now_coverage"      : gap["coverage_percent"],
        "now_readiness"     : gap["readiness"],
        "projected_coverage": projected,
        "projected_readiness": gap["_level_for"](projected),
        "new_skills"        : new_skills,
        "new_skill_count"   : len(new_skills),
        "advanced_bonus"    : gap["missing_advanced"][:5],
    }


# ── Role Finder ──────────────────────────────────────────────────
def find_role(query):
    """Find best matching role name from user query."""
    query_lower = clean(query)
    # exact match
    for role in CAREER_DB:
        if clean(role) == query_lower:
            return role
    # partial match
    for role in CAREER_DB:
        if any(word in query_lower for word in clean(role).split()
               if len(word) > 3):
            return role
    return None

# ── Skill Recommender ────────────────────────────────────────────
def recommend_skills(role_name):
    """Return all skills for a role, tiered by priority."""
    role = CAREER_DB.get(role_name)
    if not role:
        return None
    return {
        "role"        : role_name,
        "essential"   : role["essential"],
        "intermediate": role["intermediate"],
        "advanced"    : role["advanced"],
        "tools"       : role["tools"],
        "demand"      : role["demand"],
        "avg_salary"  : role["avg_salary"],
        "growth"      : role["growth"],
    }

# ── Skill Gap Analyzer ───────────────────────────────────────────
def skill_gap(user_skills, role_name):
    """Compare user skills vs role requirements."""
    role     = CAREER_DB.get(role_name)
    if not role:
        return None
    user_set = set(user_skills)

    ess_have    = [s for s in role["essential"]    if s in user_set]
    ess_missing = [s for s in role["essential"]    if s not in user_set]
    int_have    = [s for s in role["intermediate"] if s in user_set]
    int_missing = [s for s in role["intermediate"] if s not in user_set]
    adv_have    = [s for s in role["advanced"]     if s in user_set]
    adv_missing = [s for s in role["advanced"]     if s not in user_set]

    total_core = len(role["essential"])
    coverage   = round(len(ess_have) / total_core * 100, 1) if total_core else 0

    # Readiness level
    readiness = ("Job-Ready"   if coverage >= 80
                 else "Developing" if coverage >= 50
                 else "Beginner")

    return {
        "role"        : role_name,
        "ess_have"    : ess_have,
        "ess_missing" : ess_missing,
        "int_have"    : int_have,
        "int_missing" : int_missing,
        "adv_have"    : adv_have,
        "adv_missing" : adv_missing,
        "coverage"    : coverage,
        "readiness"   : readiness,
    }

# ── Career Path Matcher ──────────────────────────────────────────
def match_careers(user_skills):
    """Rank all roles by how well user skills match."""
    user_set = set(user_skills)
    results  = []
    for role_name, role in CAREER_DB.items():
        all_skills = (set(role["essential"]) |
                      set(role["intermediate"]) |
                      set(role["advanced"]))
        matches    = user_set & all_skills
        ess_match  = user_set & set(role["essential"])

        # weighted: essential match counts more
        score = (len(ess_match) * 3 + len(matches - set(role["essential"])) * 1)
        denom = (len(role["essential"]) * 3 +
                 (len(role["intermediate"]) + len(role["advanced"])) * 1)
        pct   = round(score / denom * 100, 1) if denom else 0
        results.append((role_name, pct, len(ess_match),
                        role["demand"], role["avg_salary"]))

    results.sort(key=lambda x: (x[1], x[3]), reverse=True)
    return results

# ── Learning Roadmap ─────────────────────────────────────────────
def learning_roadmap(user_skills, role_name):
    """Generate a prioritised step-by-step learning plan."""
    gap   = skill_gap(user_skills, role_name)
    if not gap:
        return []
    steps = []

    if gap["ess_missing"]:
        # Sort missing essentials by demand score
        sorted_ess = sorted(gap["ess_missing"],
                            key=lambda s: SKILL_DEMAND.get(s, 5), reverse=True)
        steps.append(("Phase 1 — Foundation (Essential Skills)",
                      sorted_ess, "These are must-have skills. Start here."))

    if gap["int_missing"]:
        sorted_int = sorted(gap["int_missing"],
                            key=lambda s: SKILL_DEMAND.get(s, 5), reverse=True)
        steps.append(("Phase 2 — Core Competency (Intermediate)",
                      sorted_int[:6], "Build these after mastering Phase 1."))

    if gap["adv_missing"]:
        sorted_adv = sorted(gap["adv_missing"],
                            key=lambda s: SKILL_DEMAND.get(s, 5), reverse=True)
        steps.append(("Phase 3 — Advanced Expertise",
                      sorted_adv[:5], "These differentiate senior candidates."))

    return steps

# ── Display ──────────────────────────────────────────────────────
W = 66

def pbar(value, width=24):
    filled = int(round(value / 100 * width))
    return "[" + "#" * filled + "-" * (width - filled) + "]"

def display_recommendation(rec):
    print(f"\n{'='*W}")
    print(f"  SKILL RECOMMENDATIONS FOR: {rec['role'].upper()}")
    print(f"  Demand Score: {rec['demand']}/100  |  "
          f"Avg Salary: {rec['avg_salary']}  |  "
          f"Growth: {rec['growth']}")
    print(f"{'-'*W}")
    print(f"  ESSENTIAL SKILLS  (must-have to apply):")
    for s in rec["essential"]:
        demand = SKILL_DEMAND.get(s, 5)
        print(f"    * {s:35s}  demand: {'*'*demand}")
    print(f"\n  INTERMEDIATE SKILLS  (needed to grow):")
    for s in rec["intermediate"]:
        print(f"    + {s}")
    print(f"\n  ADVANCED SKILLS  (senior / specialist level):")
    for s in rec["advanced"]:
        print(f"    ^ {s}")
    print(f"\n  KEY TOOLS: {', '.join(rec['tools'])}")
    print(f"{'='*W}")

def display_gap(gap, roadmap):
    print(f"\n{'='*W}")
    print(f"  SKILL GAP ANALYSIS FOR: {gap['role'].upper()}")
    print(f"  Readiness: {gap['readiness']}  |  "
          f"Essential Coverage: {gap['coverage']}%")
    print(f"  {pbar(gap['coverage'])} {gap['coverage']}%")
    print(f"{'-'*W}")
    if gap["ess_have"]:
        print(f"  Have (Essential) : {', '.join(gap['ess_have'])}")
    if gap["ess_missing"]:
        print(f"  MISSING (Essential): {', '.join(gap['ess_missing'])}")
    if gap["int_have"]:
        print(f"  Have (Intermediate): {', '.join(gap['int_have'][:5])}")
    if gap["int_missing"]:
        print(f"  Missing (Intermediate): {', '.join(gap['int_missing'][:5])}")
    print(f"{'-'*W}")
    if roadmap:
        print(f"  LEARNING ROADMAP")
        for phase, skills, note in roadmap:
            print(f"\n  {phase}")
            print(f"  Note: {note}")
            for i, s in enumerate(skills, 1):
                d = SKILL_DEMAND.get(s, 5)
                print(f"    {i}. {s:30s}  [industry demand: {d}/10]")
    print(f"{'='*W}")

def display_matches(matches, user_skills):
    print(f"\n{'='*W}")
    print(f"  CAREER PATH MATCHER  —  {len(user_skills)} skills analysed")
    print(f"{'-'*W}")
    print(f"  {'Rank':<5} {'Role':<30} {'Match':<8} {'Salary':<14} Demand")
    print(f"  {'-'*58}")
    for i, (role, pct, ess, demand, salary) in enumerate(matches[:8], 1):
        marker = ">>" if i == 1 else "  "
        print(f"  {marker}{i:<3} {role:<30} {pct:>5.1f}%  "
              f"{salary:<14} {demand}/100")
    print(f"{'='*W}")

# ── History Log ──────────────────────────────────────────────────
HISTORY_FILE = "history.txt"
_session     = []

def save_history(entry_type, detail):
    with open(HISTORY_FILE, "a", encoding="utf-8") as f:
        ts = datetime.now().strftime("%Y-%m-%d %H:%M")
        f.write(f"{ts} | {entry_type:20s} | {detail}\n")

def view_history():
    if not os.path.exists(HISTORY_FILE):
        print("\n  No history yet.\n"); return
    lines = open(HISTORY_FILE, encoding="utf-8").readlines()
    print(f"\n{'='*W}\n  HISTORY (last 20 of {len(lines)} entries)\n{'='*W}")
    for i, line in enumerate(lines[-20:], 1):
        print(f"  {i:2d}. {line.rstrip()}")
    print(f"{'='*W}\n")

def session_summary():
    if not _session:
        print("\n  No queries this session.\n"); return
    counts = Counter(s["type"] for s in _session)
    roles  = Counter(s.get("role","") for s in _session if s.get("role"))
    print(f"\n{'='*W}")
    print(f"  SESSION SUMMARY  —  {len(_session)} queries")
    print(f"  Query types : " + ", ".join(f"{k}({v})" for k,v in counts.items()))
    if roles:
        print(f"  Top roles   : " + ", ".join(f"{r}({n})" for r,n in roles.most_common(3)))
    print(f"{'='*W}\n")

# ── Demo ─────────────────────────────────────────────────────────
DEMO_CASES = [
    {
        "type"      : "gap",
        "role"      : "Data Scientist",
        "user_skills": ["python", "statistics", "pandas", "data analysis",
                        "machine learning", "sql"],
        "label"     : "User with 6 skills querying Data Scientist gap",
    },
    {
        "type"      : "match",
        "user_skills": ["html", "css", "javascript", "react", "git",
                        "node.js", "mongodb", "rest api"],
        "label"     : "Web developer skills — career match",
    },
    {
        "type"      : "recommend",
        "role"      : "Machine Learning Engineer",
        "label"     : "Full skill recommendations for ML Engineer",
    },
]

# ── Main ─────────────────────────────────────────────────────────
def show_menu():
    print()
    print("  1. Get skill recommendations for a job role")
    print("  2. Skill gap analysis  (your skills vs a role)")
    print("  3. Career path matcher  (best roles for your skills)")
    print("  4. Run demo")
    print("  5. View history log")
    print("  6. Session summary")
    print("  7. Exit")
    print()
    print("  Available roles:")
    for i, role in enumerate(CAREER_DB, 1):
        print(f"    {i:2d}. {role}")
    print()

def get_user_skills():
    print("\n  Enter your skills (comma-separated):")
    raw = input("  > ").strip()
    skills = parse_skills(raw)
    if not skills:
        print("  [!] No recognised skills found. Try: python, sql, react, etc.")
    return skills

def main():
    print()
    print("=" * W)
    print("   CAREER GUIDANCE & SKILL RECOMMENDATION SYSTEM")
    print("   Features: Skill Recommender | Gap Analyzer |")
    print("   Career Matcher | Learning Roadmap | Trend Scores")
    print("   Libraries: re, collections, os, datetime, math")
    print("=" * W)
    show_menu()

    while True:
        choice = input("  Choose (1-7): ").strip()

        if choice == "1":
            query = input("\n  Enter job role: ").strip()
            role  = find_role(query)
            if not role:
                print(f"  [!] Role not found. Available: {', '.join(CAREER_DB)}")
            else:
                rec = recommend_skills(role)
                display_recommendation(rec)
                _session.append({"type": "recommend", "role": role})
                save_history("Recommend", role)
            input("\n  Press Enter to continue...")

        elif choice == "2":
            query = input("\n  Enter target job role: ").strip()
            role  = find_role(query)
            if not role:
                print(f"  [!] Role not found.")
            else:
                skills = get_user_skills()
                if skills:
                    gap  = skill_gap(skills, role)
                    road = learning_roadmap(skills, role)
                    display_gap(gap, road)
                    _session.append({"type": "gap", "role": role})
                    save_history("Gap Analysis", f"{role} | skills: {len(skills)}")
            input("\n  Press Enter to continue...")

        elif choice == "3":
            skills = get_user_skills()
            if skills:
                matches = match_careers(skills)
                display_matches(matches, skills)
                top = matches[0][0] if matches else ""
                _session.append({"type": "match", "role": top})
                save_history("Career Match", f"top: {top} | skills: {len(skills)}")
            input("\n  Press Enter to continue...")

        elif choice == "4":
            for demo in DEMO_CASES:
                print(f"\n  Demo: {demo['label']}")
                if demo["type"] == "recommend":
                    rec = recommend_skills(demo["role"])
                    display_recommendation(rec)
                elif demo["type"] == "gap":
                    gap  = skill_gap(demo["user_skills"], demo["role"])
                    road = learning_roadmap(demo["user_skills"], demo["role"])
                    display_gap(gap, road)
                elif demo["type"] == "match":
                    matches = match_careers(demo["user_skills"])
                    display_matches(matches, demo["user_skills"])
                _session.append({"type": demo["type"],
                                 "role": demo.get("role","")})
            input("\n  Press Enter to continue...")

        elif choice == "5":
            view_history()
            input("  Press Enter to continue...")

        elif choice == "6":
            session_summary()
            input("  Press Enter to continue...")

        elif choice == "7":
            session_summary()
            print("  Goodbye!\n"); break
        else:
            print("  [!] Enter 1 to 7.")

        show_menu()

if __name__ == "__main__":
    main()
