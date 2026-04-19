# 📚 AI Study Planner — Setup & Run Guide

## Project Structure (final layout)

```
study-planner/
├── app.py               ← Python backend (Flask)
├── requirements.txt     ← Python dependencies
├── .env                 ← Your secret keys (YOU create this)
├── .env.example         ← Template for .env
├── study_planner.db     ← SQLite database (auto-created on first run)
└── templates/
    ├── index.html       ← Home page / input form
    ├── result.html      ← Generated plan page
    └── history.html     ← Past plans page
```

---

## Step-by-Step Setup

### Step 1 — Install Python
Make sure Python 3.10 or newer is installed.
```bash
python --version   # Should print 3.10+
```

### Step 2 — Create a virtual environment
```bash
cd study-planner
python -m venv venv

# Activate it:
# macOS / Linux:
source venv/bin/activate

# Windows (Command Prompt):
venv\Scripts\activate.bat

# Windows (PowerShell):
venv\Scripts\Activate.ps1
```

### Step 3 — Install dependencies
```bash
pip install -r requirements.txt
```

### Step 4 — Create your .env file
```bash
cp .env.example .env
```
Then open `.env` and paste your real Anthropic API key:
```
ANTHROPIC_API_KEY=sk-ant-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
SECRET_KEY=any-random-string-you-choose
FLASK_ENV=development
```
Get your API key at → https://console.anthropic.com/

### Step 5 — Place the HTML templates
Make sure all three HTML files are inside a folder called `templates/`:
```
templates/
├── index.html
├── result.html
└── history.html
```

### Step 6 — Run the app
```bash
python app.py
```
You will see:
```
✅  Study Planner running → http://localhost:5000
```

### Step 7 — Open in your browser
Go to → http://localhost:5000

---

## How It Works (Data Flow)

```
User fills form (index.html)
        ↓
POST /generate  (app.py)
        ↓
  Parse subject names, mid scores, credits
        ↓
  Compute weakness % per subject  (1 - score/20)
        ↓
  Distribute 12 hrs/week proportionally (weakness × credits)
        ↓
  Call Claude API → get motivational tips for weak subjects
        ↓
  Save plan to SQLite (study_planner.db)
        ↓
Render result.html with timetable
        ↓
User clicks "View History" → GET /history → history.html
```

---

## Route Summary

| URL | Method | Template | What it does |
|---|---|---|---|
| `/` | GET | index.html | Show the input form |
| `/generate` | POST | result.html | Process form → build plan → show results |
| `/history` | GET | history.html | Show all past plans from the database |

---

## Weakness Scoring Logic

```
weakness (%) = (1 - mid_score / 20) × 100

Score  0/20 → 100% weak  → 🔴 Critical
Score  6/20 →  70% weak  → 🔴 Critical
Score  9/20 →  55% weak  → 🟠 High
Score 14/20 →  30% weak  → 🟡 Medium
Score 18/20 →  10% weak  → 🟢 Low
```

Hours per subject = proportional share of 12 hrs, weighted by:
`weakness_factor × credit_weight`

---

## Troubleshooting

| Problem | Fix |
|---|---|
| `ModuleNotFoundError: flask` | Run `pip install -r requirements.txt` with venv active |
| `anthropic.AuthenticationError` | Check your ANTHROPIC_API_KEY in `.env` |
| Templates not found | Make sure HTML files are inside a `templates/` folder |
| Port 5000 in use | Run `python app.py` → it auto-picks the next port, or change `port=5001` in app.py |
| Database errors | Delete `study_planner.db` and restart — it will recreate itself |
