# 🧠 How the AI Study Planner Works — Logic Explained

---

## The Core Idea

The app looks at how much a student scored in their mid-semester exam and figures out which subjects they are weak in. It then gives more study hours to the weaker subjects and less to the stronger ones. Simple as that.

---

## Step 1 — Collecting Input

The student fills out a form with:
- Their **target CGPA** (how well they want to do)
- For each subject:
  - Subject name
  - Mid-semester score (out of 20)
  - Credit weight (how many credits that subject carries)

---

## Step 2 — Calculating Weakness

For every subject, the app calculates a **weakness percentage**:

```
weakness (%) = (1 - mid_score / 20) × 100
```

Examples:

| Score | Weakness | Meaning |
|---|---|---|
| 4 / 20 | 80% | Very weak — needs a lot of attention |
| 10 / 20 | 50% | Average — needs moderate attention |
| 16 / 20 | 20% | Strong — just needs maintenance |
| 20 / 20 | 0% | Perfect — minimal study needed |

---

## Step 3 — Distributing Study Hours

The total study budget is **12 hours per week**.

Each subject gets a share of those 12 hours based on two things combined:

```
weight = weakness × credits
```

The more weak a subject is AND the more credits it carries, the bigger its share of the 12 hours.

Then hours are distributed proportionally:

```
hours for subject = (subject weight / total weight of all subjects) × 12
```

Every subject is guaranteed a minimum of **0.5 hours** per week, even if they scored perfectly.

---

## Step 4 — Assigning Priority Labels

Based on the weakness percentage, each subject gets a priority label:

| Weakness % | Priority |
|---|---|
| 70% and above | 🔴 Critical |
| 45% – 69% | 🟠 High |
| 25% – 44% | 🟡 Medium |
| Below 25% | 🟢 Low |

---

## Step 5 — Calling the AI (Claude)

After the hours are calculated, the app sends a message to **Claude (Anthropic's AI)** with:
- The student's target CGPA
- The names of their weakest subjects

Claude responds with **3 short, encouraging study tips** tailored to those weak subjects. This is the only part that uses AI — the hour distribution math is done by the app itself.

---

## Step 6 — Saving to Database

Every generated plan is saved to a **SQLite database** (a simple local file called `study_planner.db`) with:
- The target CGPA
- The full timetable (all subjects, scores, hours, priority)
- The date and time it was created

This is what powers the **History page** — it just reads all saved plans from that file.

---

## The Full Flow in One Picture

```
Student fills form
        ↓
App reads scores → calculates weakness % per subject
        ↓
App multiplies weakness × credits → gets a weight per subject
        ↓
App divides 12 hours proportionally using those weights
        ↓
Claude AI reads the weak subjects → gives study tips
        ↓
Plan is saved to SQLite database
        ↓
Result page shows the timetable
        ↓
History page shows all past plans
```

---

## Why Credits Matter

Two subjects can have the same weakness score, but if one carries 4 credits and the other carries 2 credits, the 4-credit subject gets more study time. This is because failing a high-credit subject hurts your CGPA much more than failing a low-credit one.

---

## Why the AI is Only Used for Tips

The hour distribution is pure math — it doesn't need AI. Claude is only called for the motivational tips because that part benefits from natural language. This also means the app still works for the core plan even if the AI call fails for any reason.
