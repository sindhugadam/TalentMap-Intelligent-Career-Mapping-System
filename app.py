from flask import (Flask, render_template, request, redirect, session,
                   url_for, flash)
import sqlite3
import io
from werkzeug.security import generate_password_hash, check_password_hash
import careergudience as cg
from datetime import datetime

app = Flask(__name__)
app.secret_key = "your-secret-key-change-this"
app.config["MAX_CONTENT_LENGTH"] = 5 * 1024 * 1024  # 5 MB upload cap

ALLOWED_RESUME_EXT = (".pdf", ".docx", ".txt")


# ── Database ─────────────────────────────────────────────────────
def get_db():
    conn = sqlite3.connect("users.db")
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        )
    """)

    # Per-user (and per-guest) activity history.
    existing = cur.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='history'"
    ).fetchone()

    if not existing:
        cur.execute("""
            CREATE TABLE history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                owner TEXT NOT NULL,
                entry_type TEXT NOT NULL,
                detail TEXT,
                created_at TEXT NOT NULL
            )
        """)
    else:
        cols = [c[1] for c in cur.execute("PRAGMA table_info(history)")]
        if "owner" not in cols:
            # Legacy schema (e.g. user_id/action_type/details). Migrate it
            # into the new per-owner shape, preserving any existing rows.
            cur.execute("""
                CREATE TABLE history_new (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    owner TEXT NOT NULL,
                    entry_type TEXT NOT NULL,
                    detail TEXT,
                    created_at TEXT NOT NULL
                )
            """)
            owner_expr = "'u:' || user_id" if "user_id" in cols else "'g:legacy'"
            type_expr = "action_type" if "action_type" in cols else "'Activity'"
            detail_expr = "details" if "details" in cols else "''"
            ts_expr = "created_at" if "created_at" in cols else "''"
            cur.execute(f"""
                INSERT INTO history_new (owner, entry_type, detail, created_at)
                SELECT {owner_expr}, {type_expr}, {detail_expr}, {ts_expr} FROM history
            """)
            cur.execute("DROP TABLE history")
            cur.execute("ALTER TABLE history_new RENAME TO history")

    cur.execute("CREATE INDEX IF NOT EXISTS idx_history_owner ON history(owner)")
    conn.commit()
    conn.close()


# ── History helpers (now scoped per user / guest) ────────────────
def current_owner():
    """Owner key for history rows — only logged-in users have one."""
    if session.get("user_id"):
        return f"u:{session['user_id']}"
    return None


def save_history_db(entry_type, detail=""):
    # History is only recorded for logged-in users.
    owner = current_owner()
    if not owner:
        return
    conn = get_db()
    conn.execute(
        "INSERT INTO history (owner, entry_type, detail, created_at) VALUES (?, ?, ?, ?)",
        (owner, entry_type, detail,
         datetime.now().strftime("%Y-%m-%d %H:%M"))
    )
    conn.commit()
    conn.close()


def add_session_entry(entry_type, role=""):
    if "activity" not in session:
        session["activity"] = []
    activity = session["activity"]
    activity.append({"type": entry_type, "role": role})
    session["activity"] = activity


# ── Resume text extraction ───────────────────────────────────────
def _pdf_text_pypdf(data):
    try:
        from pypdf import PdfReader
        reader = PdfReader(io.BytesIO(data))
        return "\n".join((page.extract_text() or "") for page in reader.pages)
    except Exception as e:
        print("pypdf error:", e)
        return ""


def _pdf_text_pdfminer(data):
    try:
        from pdfminer.high_level import extract_text
        return extract_text(io.BytesIO(data)) or ""
    except Exception as e:
        print("pdfminer error:", e)
        return ""


def _pdf_text_pdfium(data):
    try:
        import pypdfium2 as pdfium
        pdf = pdfium.PdfDocument(data)
        out = []
        for page in pdf:
            tp = page.get_textpage()
            out.append(tp.get_text_range() or "")
        return "\n".join(out)
    except Exception as e:
        print("pypdfium2 error:", e)
        return ""


def _pdf_text_ocr(data):
    """OCR fallback for scanned/image PDFs. Tries RapidOCR first (pure
    pip install, no system binary needed), then Tesseract if present.
    Silently returns '' if no OCR engine is available."""
    # Render each page to an image once.
    try:
        import pypdfium2 as pdfium
        pdf = pdfium.PdfDocument(data)
        images = [page.render(scale=2.5).to_pil() for page in pdf]  # ~180 dpi
    except Exception as e:
        print("OCR render failed:", e)
        return ""

    # 1) RapidOCR (pip-only)
    try:
        import numpy as np
        from rapidocr_onnxruntime import RapidOCR
        ocr = RapidOCR()
        out = []
        for img in images:
            result, _ = ocr(np.array(img.convert("RGB")))
            if result:
                out.append(" ".join(line[1] for line in result))
        text = "\n".join(out)
        if text.strip():
            return text
    except Exception as e:
        print("RapidOCR skipped/failed:", e)

    # 2) Tesseract (needs the system binary, e.g. `brew install tesseract`)
    try:
        import pytesseract
        return "\n".join(pytesseract.image_to_string(img) for img in images)
    except Exception as e:
        print("Tesseract OCR skipped/failed:", e)
        return ""


def extract_resume_text(file_storage):
    """Pull plain text out of an uploaded .pdf / .docx / .txt file.
    PDFs go through several engines (and OCR) so scanned or awkwardly
    encoded files still work where possible."""
    filename = (file_storage.filename or "").lower()
    data = file_storage.read()
    if not data:
        return ""

    if filename.endswith(".pdf"):
        for engine in (_pdf_text_pypdf, _pdf_text_pdfminer, _pdf_text_pdfium):
            text = engine(data)
            if len(text.strip()) >= 20:   # got something usable
                return text
        # Nothing from the text-layer engines -> likely a scanned image PDF.
        return _pdf_text_ocr(data)

    if filename.endswith(".docx"):
        try:
            import docx
            document = docx.Document(io.BytesIO(data))
            return "\n".join(p.text for p in document.paragraphs)
        except Exception as e:
            print("DOCX parse error:", e)
            return ""

    # .txt or anything else: best-effort decode
    return data.decode("utf-8", errors="ignore")


# ── Core pages ───────────────────────────────────────────────────
@app.route('/')
def home():
    roles = list(cg.CAREER_DB.keys())
    user_name = session.get('user_name')
    return render_template('index.html', roles=roles, user_name=user_name)


@app.route('/menu', methods=['POST'])
def menu():
    choice = request.form.get('choice')
    if choice == "1":
        return redirect(url_for('recommend_form'))
    elif choice == "2":
        return redirect(url_for('gap_form'))
    elif choice == "3":
        return redirect(url_for('match_form'))
    elif choice == "4":
        return redirect(url_for('resume_form'))
    elif choice == "5":
        return redirect(url_for('demo'))
    elif choice == "6":
        return redirect(url_for('history'))
    elif choice == "7":
        return redirect(url_for('summary'))
    flash("Invalid menu choice.")
    return redirect(url_for('home'))


@app.route('/recommend-form')
def recommend_form():
    roles = list(cg.CAREER_DB.keys())
    return render_template('recommend_form.html', roles=roles)


@app.route('/gap-form')
def gap_form():
    roles = list(cg.CAREER_DB.keys())
    return render_template('gap_form.html', roles=roles)


@app.route('/match-form')
def match_form():
    return render_template('match_form.html')


@app.route('/match', methods=['POST'])
def match():
    skills_text = request.form.get('skills', '').strip()
    if not skills_text:
        flash("Please enter skills for career match.")
        return redirect(url_for('match_form'))

    skills = cg.parse_skills(skills_text)
    matches = cg.match_careers(skills)
    filtered_matches = [m for m in matches if m[1] > 0]
    top_role = filtered_matches[0][0] if filtered_matches else ""

    add_session_entry("match", top_role)
    save_history_db("Career Match", f"top: {top_role} | skills: {len(skills)}")

    return render_template('match.html', matches=filtered_matches, skills=skills)


@app.route('/gap', methods=['POST'])
def gap():
    role = request.form.get('role', '').strip()
    skills_text = request.form.get('skills', '').strip()
    if not role or not skills_text:
        flash("Please select a role and enter your skills.")
        return redirect(url_for('gap_form'))

    skills = cg.parse_skills(skills_text)
    role_data = cg.CAREER_DB.get(role)
    if not role_data:
        flash("Selected role not found.")
        return redirect(url_for('gap_form'))

    essential = [s.lower() for s in role_data.get("essential", [])]
    intermediate = [s.lower() for s in role_data.get("intermediate", [])]
    advanced = [s.lower() for s in role_data.get("advanced", [])]
    user_skills = [s.lower() for s in skills]

    have_essential = [s for s in essential if s in user_skills]
    missing_essential = [s for s in essential if s not in user_skills]
    have_intermediate = [s for s in intermediate if s in user_skills]
    missing_intermediate = [s for s in intermediate if s not in user_skills]

    total_required = len(essential) + len(intermediate)
    total_have = len(have_essential) + len(have_intermediate)
    coverage_percent = round((total_have / total_required) * 100, 1) if total_required else 0.0

    if coverage_percent >= 80:
        readiness = "Advanced"
    elif coverage_percent >= 60:
        readiness = "Intermediate"
    elif coverage_percent >= 35:
        readiness = "Developing"
    else:
        readiness = "Beginner"

    def progress_bar(percent, width=20):
        filled = int((percent / 100) * width)
        return "[" + "#" * filled + "-" * (width - filled) + f"] {percent}%"

    foundation = sorted(missing_essential, key=lambda x: cg.SKILL_DEMAND.get(x, 5), reverse=True)
    core = sorted(missing_intermediate, key=lambda x: cg.SKILL_DEMAND.get(x, 5), reverse=True)
    advanced_phase = sorted(advanced, key=lambda x: cg.SKILL_DEMAND.get(x, 5), reverse=True)

    gap_data = {
        "role": role,
        "user_skills": user_skills,
        "coverage_percent": coverage_percent,
        "readiness": readiness,
        "progress_bar": progress_bar(coverage_percent),
        "have_essential": have_essential,
        "missing_essential": missing_essential,
        "have_intermediate": have_intermediate,
        "missing_intermediate": missing_intermediate,
        "roadmap": {
            "Phase 1 - Foundation (Essential Skills)": foundation,
            "Phase 2 - Core Competency (Intermediate)": core,
            "Phase 3 - Advanced Expertise": advanced_phase
        }
    }

    add_session_entry("gap", role)
    save_history_db("Gap Analysis", f"{role} | skills: {len(skills)}")

    return render_template('gap.html', gap=gap_data, demand_map=cg.SKILL_DEMAND)


@app.route('/recommend', methods=['POST'])
def recommend():
    role = request.form.get('role', '').strip()
    if not role:
        flash("Please select a role.")
        return redirect(url_for('recommend_form'))

    rec = cg.recommend_skills(role)
    add_session_entry("recommend", role)
    save_history_db("Recommend", role)
    return render_template('recommend.html', rec=rec, demand_map=cg.SKILL_DEMAND)


# ── Resume Scanner: extract skills, find gap, build a study plan ──
@app.route('/resume-form')
def resume_form():
    roles = list(cg.CAREER_DB.keys())
    user_name = session.get('user_name')
    return render_template('resume_form.html', roles=roles, user_name=user_name)


@app.route('/resume', methods=['POST'])
def resume():
    role = request.form.get('role', '').strip()   # "" means auto-detect
    file = request.files.get('resume')

    if not file or not file.filename:
        flash("Please upload your resume (.pdf, .docx, or .txt).")
        return redirect(url_for('resume_form'))

    if not file.filename.lower().endswith(ALLOWED_RESUME_EXT):
        flash("Unsupported file type. Use .pdf, .docx, or .txt.")
        return redirect(url_for('resume_form'))

    text = extract_resume_text(file)
    if not text.strip():
        flash("Couldn't read any text from that PDF, even with OCR. Make sure "
              "the dependencies are installed (run: pip install -r requirements.txt). "
              "If it's a very low-resolution scan, try a clearer copy, or upload "
              "your resume as a .docx or paste it into a .txt file.")
        return redirect(url_for('resume_form'))

    found_skills = cg.extract_skills_from_text(text)
    if not found_skills:
        flash("No recognised skills were found in the resume. "
              "Make sure skills like python, sql, react, etc. are listed.")
        return redirect(url_for('resume_form'))

    # Auto-detect the best-fit role if the user did not choose one.
    matches = cg.match_careers(found_skills)
    auto_detected = False
    if not role or role not in cg.CAREER_DB:
        role = matches[0][0] if matches else list(cg.CAREER_DB.keys())[0]
        auto_detected = True

    gap_data = cg.compute_gap(found_skills, role)
    plan = cg.skillup_plan(gap_data)
    conclusion = cg.projected_after_plan(gap_data)

    add_session_entry("resume", role)
    save_history_db("Resume Scan",
                    f"{role} | skills found: {len(found_skills)} | "
                    f"coverage: {gap_data['coverage_percent']}%")

    return render_template(
        'resume.html',
        roles=list(cg.CAREER_DB.keys()),
        user_name=session.get('user_name'),
        found_skills=found_skills,
        role=role,
        auto_detected=auto_detected,
        top_matches=matches[:3],
        gap=gap_data,
        plan=plan,
        conclusion=conclusion,
        demand_map=cg.SKILL_DEMAND,
    )


@app.route('/demo')
def demo():
    demo_output = []
    for demo in cg.DEMO_CASES:
        if demo["type"] == "recommend":
            rec = cg.recommend_skills(demo["role"])
            add_session_entry("recommend", demo["role"])
            save_history_db("Recommend", demo["role"])
            demo_output.append({"type": "recommend", "label": demo["label"], "rec": rec})

        elif demo["type"] == "gap":
            role = demo["role"]
            user_skills = [s.lower() for s in demo["user_skills"]]
            role_data = cg.CAREER_DB.get(role, {})
            essential = [s.lower() for s in role_data.get("essential", [])]
            intermediate = [s.lower() for s in role_data.get("intermediate", [])]
            advanced = [s.lower() for s in role_data.get("advanced", [])]

            have_essential = [s for s in essential if s in user_skills]
            missing_essential = [s for s in essential if s not in user_skills]
            have_intermediate = [s for s in intermediate if s in user_skills]
            missing_intermediate = [s for s in intermediate if s not in user_skills]

            total_required = len(essential) + len(intermediate)
            total_have = len(have_essential) + len(have_intermediate)
            coverage_percent = round((total_have / total_required) * 100, 1) if total_required else 0.0

            if coverage_percent >= 80:
                readiness = "Advanced"
            elif coverage_percent >= 60:
                readiness = "Intermediate"
            elif coverage_percent >= 35:
                readiness = "Developing"
            else:
                readiness = "Beginner"

            gap_data = {
                "role": role,
                "user_skills": user_skills,
                "coverage_percent": coverage_percent,
                "readiness": readiness,
                "have_essential": have_essential,
                "missing_essential": missing_essential,
                "have_intermediate": have_intermediate,
                "missing_intermediate": missing_intermediate,
                "roadmap": {
                    "Phase 1 - Foundation (Essential Skills)": sorted(
                        missing_essential, key=lambda x: cg.SKILL_DEMAND.get(x, 5), reverse=True),
                    "Phase 2 - Core Competency (Intermediate)": sorted(
                        missing_intermediate, key=lambda x: cg.SKILL_DEMAND.get(x, 5), reverse=True),
                    "Phase 3 - Advanced Expertise": sorted(
                        advanced, key=lambda x: cg.SKILL_DEMAND.get(x, 5), reverse=True)
                }
            }

            add_session_entry("gap", role)
            save_history_db("Gap Analysis", f"{role} | skills: {len(user_skills)}")
            demo_output.append({"type": "gap", "label": demo["label"], "gap": gap_data})

        elif demo["type"] == "match":
            matches = cg.match_careers(demo["user_skills"])
            top_role = matches[0][0] if matches else ""
            add_session_entry("match", top_role)
            save_history_db("Career Match", f"top: {top_role} | skills: {len(demo['user_skills'])}")
            demo_output.append({"type": "match", "label": demo["label"], "matches": matches[:3]})

    return render_template('demo.html', demos=demo_output, demand_map=cg.SKILL_DEMAND)


# ── History (per-user, from the database) ────────────────────────
@app.route('/history')
def history():
    user_name = session.get('user_name')
    owner = current_owner()
    if not owner:
        # Not logged in — don't show any history.
        return render_template('history.html', history=[], total=0,
                               logged_in=False, user_name=None)

    conn = get_db()
    total = conn.execute(
        "SELECT COUNT(*) AS c FROM history WHERE owner = ?", (owner,)
    ).fetchone()["c"]
    rows = conn.execute(
        "SELECT id, created_at, entry_type, detail FROM history "
        "WHERE owner = ? ORDER BY id DESC LIMIT 20", (owner,)
    ).fetchall()
    conn.close()

    # Keep the template contract: (row_id, "display line")
    indexed_history = [
        (r["id"], f"{r['created_at']} | {r['entry_type']} | {r['detail']}")
        for r in rows
    ]
    return render_template('history.html', history=indexed_history, total=total,
                           logged_in=True, user_name=user_name)


@app.route('/delete-history/<int:index>', methods=['POST'])
def delete_history(index):
    # 'index' is the history row id; scoped to the logged-in owner so
    # nobody can delete another user's entries.
    owner = current_owner()
    if not owner:
        return redirect(url_for('login'))
    conn = get_db()
    conn.execute("DELETE FROM history WHERE id = ? AND owner = ?", (index, owner))
    conn.commit()
    conn.close()
    return redirect(url_for('history'))


@app.route('/summary')
def summary():
    activity = session.get("activity", [])
    if not activity:
        return render_template('summary.html', empty=True)

    counts = {}
    roles = {}
    for item in activity:
        t = item["type"]
        counts[t] = counts.get(t, 0) + 1
        r = item.get("role")
        if r:
            roles[r] = roles.get(r, 0) + 1

    type_str = ", ".join([f"{k}({v})" for k, v in counts.items()])
    top_roles = sorted(roles.items(), key=lambda x: x[1], reverse=True)[:3]
    role_str = ", ".join([f"{r}({n})" for r, n in top_roles])

    return render_template('summary.html', total=len(activity),
                           type_str=type_str, role_str=role_str, empty=False)


# ── Auth ─────────────────────────────────────────────────────────
@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']
        confirm_password = request.form['confirm_password']

        if password != confirm_password:
            return "Passwords do not match"

        hashed_password = generate_password_hash(password)
        conn = get_db()
        cur = conn.cursor()
        cur.execute("SELECT * FROM users WHERE email = ?", (email,))
        if cur.fetchone():
            conn.close()
            return "Email already registered"

        cur.execute("INSERT INTO users (name, email, password) VALUES (?, ?, ?)",
                    (name, email, hashed_password))
        conn.commit()
        conn.close()
        return redirect('/login')

    return render_template('signup.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        conn = get_db()
        cur = conn.cursor()
        cur.execute("SELECT * FROM users WHERE email = ?", (email,))
        user = cur.fetchone()
        conn.close()

        if user and check_password_hash(user["password"], password):
            session['user_id'] = user["id"]
            session['user_name'] = user["name"]
            session['user_email'] = user["email"]
            return redirect('/')
        return "Invalid email or password"

    return render_template('login.html')


@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')


init_db()

if __name__ == '__main__':
    app.run(debug=True)
