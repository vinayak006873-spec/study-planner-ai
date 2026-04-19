"""
AI Study Planner  –  app.py
============================
Matches the three frontend templates exactly:
  index.html   →  GET  /
  result.html  →  POST /generate
  history.html →  GET  /history

Run:
    python app.py
"""

import os
import json
import sqlite3
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for
from dotenv import load_dotenv
import anthropic

# ── Load environment variables from .env ────────────────────────────────────
load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "dev-secret-key")

# ── Anthropic client (loaded once at startup) ────────────────────────────────
anthropic_client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY", ""))

# ── Constants ────────────────────────────────────────────────────────────────
DB_PATH        = "study_planner.db"   # SQLite file created in project root
TOTAL_HOURS    = 12                   # Total hrs/week to distribute
MIN_HOURS      = 0.5                  # Minimum hours guaranteed per subject
CLAUDE_MODEL   = "claude-sonnet-4-20250514"


# ════════════════════════════════════════════════════════════════════════════
#  DATABASE HELPERS
# ════════════════════════════════════════════════════════════════════════════

def get_db():
    """Return a sqlite3 connection with row_factory set."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Create the plans table if it doesn't already exist."""
    with get_db() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS plans (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                target_cgpa REAL    NOT NULL,
                timetable   TEXT    NOT NULL,   -- JSON string
                created_at  TEXT    NOT NULL
            )
        """)
        conn.commit()


# ════════════════════════════════════════════════════════════════════════════
#  STUDY-PLAN LOGIC
# ════════════════════════════════════════════════════════════════════════════

def compute_weakness(mid_score: float) -> int:
    """
    weakness = (1 - mid_score/20) * 100, clamped to [0, 100].
    A score of 0/20  → 100% weak
    A score of 20/20 →   0% weak
    """
    return round(max(0, min(100, (1 - mid_score / 20) * 100)))


def compute_priority(weakness: int) -> str:
    """Map weakness percentage to a human-readable priority label."""
    if weakness >= 70:
        return "🔴 Critical"
    if weakness >= 45:
        return "🟠 High"
    if weakness >= 25:
        return "🟡 Medium"
    return "🟢 Low"


def distribute_hours(subjects: list[dict]) -> list[dict]:
    """
    Distribute TOTAL_HOURS (12 hrs/week) across subjects proportionally,
    weighting each subject by:   weakness_factor × credit_weight

    A minimum of MIN_HOURS (0.5) is guaranteed to every subject.
    Returns the same list with 'hours', 'weakness', 'priority' added.
    """
    for s in subjects:
        s["weakness"] = compute_weakness(s["mid_score"])
        s["priority"] = compute_priority(s["weakness"])

    # Weighted score for each subject
    weighted = [
        (s["weakness"] / 100) * s["credits"]
        for s in subjects
    ]
    total_weight = sum(weighted) or 1  # avoid division by zero

    # Proportional allocation
    raw_hours = [
        max(MIN_HOURS, round((w / total_weight) * TOTAL_HOURS, 1))
        for w in weighted
    ]

    # Scale so the sum equals TOTAL_HOURS exactly
    total_raw = sum(raw_hours) or 1
    final_hours = [
        round((h / total_raw) * TOTAL_HOURS, 1)
        for h in raw_hours
    ]

    for s, h in zip(subjects, final_hours):
        s["hours"] = h

    return subjects


def call_claude_for_tips(subjects: list[dict], target_cgpa: float) -> str:
    """
    Ask Claude for a short, encouraging study tip paragraph
    that references the student's weak subjects by name.
    Returns plain text (used nowhere in the current templates but
    stored in DB for future use / optional display).
    """
    weak_names = [s["subject"] for s in subjects if s["weakness"] >= 45]
    weak_str   = ", ".join(weak_names) if weak_names else "none identified"

    prompt = (
        f"A college student is targeting a CGPA of {target_cgpa}. "
        f"Their weaker subjects are: {weak_str}. "
        f"Give them 3 concise, encouraging, actionable study tips in plain text (no markdown). "
        f"Keep it under 80 words total."
    )

    message = anthropic_client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=200,
        messages=[{"role": "user", "content": prompt}],
    )
    return message.content[0].text.strip()


# ════════════════════════════════════════════════════════════════════════════
#  ROUTES
# ════════════════════════════════════════════════════════════════════════════

@app.route("/")
def index():
    """Render the main input form (index.html)."""
    return render_template("index.html")


@app.route("/generate", methods=["POST"])
def generate():
    """
    1. Parse the submitted form data.
    2. Compute weakness & distribute study hours.
    3. Call Claude for motivational tips.
    4. Save the plan to SQLite.
    5. Render result.html with the timetable data.
    """
    try:
        # ── Parse form ──────────────────────────────────────────────────────
        target_cgpa  = float(request.form.get("target_cgpa", 8.0))
        num_subjects = int(request.form.get("num_subjects", 4))

        subjects = []
        for i in range(1, num_subjects + 1):
            name      = request.form.get(f"subject_name_{i}", "").strip()
            mid_score = float(request.form.get(f"mid_score_{i}", 0))
            credits   = int(request.form.get(f"credits_{i}", 4))

            if not name:
                raise ValueError(f"Subject name {i} is empty.")
            if not (0 <= mid_score <= 20):
                raise ValueError(f"Mid score for '{name}' must be 0–20.")
            if not (1 <= credits <= 6):
                raise ValueError(f"Credits for '{name}' must be 1–6.")

            subjects.append({
                "subject":   name,
                "mid_score": mid_score,
                "credits":   credits,
            })

        # ── Compute weakness & hours ─────────────────────────────────────────
        timetable = distribute_hours(subjects)

        # ── Call Claude (non-blocking best-effort) ───────────────────────────
        try:
            ai_tips = call_claude_for_tips(timetable, target_cgpa)
        except Exception:
            ai_tips = ""   # Never crash the page if AI fails

        # ── Persist to SQLite ────────────────────────────────────────────────
        with get_db() as conn:
            conn.execute(
                "INSERT INTO plans (target_cgpa, timetable, created_at) VALUES (?, ?, ?)",
                (
                    target_cgpa,
                    json.dumps(timetable),
                    datetime.now().strftime("%d %b %Y, %I:%M %p"),
                ),
            )
            conn.commit()

        # ── Render result ────────────────────────────────────────────────────
        return render_template(
            "result.html",
            target_cgpa  = target_cgpa,
            num_subjects = num_subjects,
            timetable    = timetable,
            ai_tips      = ai_tips,
        )

    except Exception as exc:
        # Log and redirect back to the form with an error flag
        print(f"[ERROR /generate] {exc}")
        return redirect(url_for("index", error=1))


@app.route("/history")
def history():
    """
    Fetch all saved plans from SQLite (newest first)
    and render history.html with the `plans` list.
    """
    with get_db() as conn:
        rows = conn.execute(
            "SELECT id, target_cgpa, timetable, created_at FROM plans ORDER BY id DESC"
        ).fetchall()

    plans = []
    for row in rows:
        plans.append({
            "id":          row["id"],
            "target_cgpa": row["target_cgpa"],
            "timetable":   json.loads(row["timetable"]),
            "created_at":  row["created_at"],
        })

    return render_template("history.html", plans=plans)


# ════════════════════════════════════════════════════════════════════════════
#  STARTUP
# ════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    init_db()   # Create DB table on first run
    print("✅  Study Planner running → http://localhost:5000")
    app.run(debug=True, host="0.0.0.0", port=5000)
