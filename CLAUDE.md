# AI Job Matching — Project Context

EA-focused job matching tool. Matches a person's profile against open roles in
the effective-altruism job market, ranks them by fit, and explains why each one
fits. Two audiences: individual job seekers, and university / community group
organisers who help their members find roles.

## Current state

- `AI-Job-Matching/app.py` — Streamlit front end (to be replaced; see below).
- `AI-Job-Matching/matcher.py` — matching logic: takes a profile, ranks jobs,
  calls Claude to write the "why this fits" explanation. **Core asset, keep.**
- `AI-Job-Matching/data/jobs.json` — 15 sample EA jobs (title, org, salary,
  location, cause areas, description). Seed data; eventually replaced by live
  scraped listings tagged automatically.
- `requirements.txt`, `.env.example` — standard plumbing.

A separate HTML/CSS design prototype exists (light-blue palette, orange accent,
fit-score "dial", ranked preference chips). It is the intended front end. The
Streamlit app is a throwaway test harness, not the real UI.

## Direction (decisions made so far)

- Architecture: replace Streamlit. Expose the matcher as a small API endpoint
  (FastAPI fits the existing Python) and serve the prototype HTML as the front
  end. The organiser bulk view is the same endpoint called in a loop over a CSV.
- The matcher is a **weighted structured score**, not one big LLM call. Use code
  for what code is good at (filtering, scoring), and the LLM only for reading
  free text and writing explanations.

## Profile inputs the front end collects

- Cause areas — **ranked** (tap order = preference, #1 highest). ~22 options.
- Role type — **ranked** multi-select (Research, Operations, Software, Comms,
  Policy, Grantmaking, Data, People/HR, Finance, Events).
- Commitment type — multi-select filter (full-time, part-time, internship,
  volunteering, contract).
- Location preference.
- Years of experience.
- Free text: "what you want to work on" (goals/trajectory), "background &
  skills", and "other notes" (constraints: visa, salary, start date, etc.).

## Matching algorithm (target design)

Each job gets a 0–100 score blended from weighted components:

1. **Cause-area alignment (~35%)** — use the rank. Weight ranked causes
   (#1 = 1.0, #2 = 0.8, #3 = 0.65, decaying); a job's cause score is the best
   matching weight among its tags.
2. **Role-type alignment (~25%)** — same ranked logic against the job category.
3. **Hard filters (pass/fail, not scored)** — commitment type, location /
   right-to-work when it's a hard constraint. These exclude jobs entirely.
4. **Soft signals (adjust score)** — experience vs. role's expected level: a gap
   lowers the score and can surface as "you'd be stretching into this", never
   excludes.
5. **Free-text relevance (~25%)** — embeddings (cosine similarity between
   profile free-text and job description) to shortlist, optionally a Claude call
   to score the finalists 0–10 with a one-line reason.
6. **"Why this fits" explanation** — Claude, last step, only for the jobs being
   displayed (not all jobs), to control cost.

Pipeline:
```
profile → hard filters → structured score → semantic shortlist (top N)
        → optional LLM scoring on shortlist → sort → top 3–5
        → LLM "why this fits" per shown job → return with scores
```
The dial number shown in the UI is the final blended score.

## Build order

1. Make the structured score real in `matcher.py` (weighted cause + role +
   filters + experience). No AI yet; verify rankings by hand against `jobs.json`.
2. Add the Claude "why this fits" explanation.
3. Add embeddings for the free-text boxes.
4. Swap architecture: FastAPI endpoint + prototype HTML front end; add the
   organiser CSV bulk view.

## Open decisions to resolve

- **Job tagging at scale**: scoring depends on clean `cause_areas` / `role_type`
  tags. `jobs.json` is hand-tagged; live scraped jobs will need an auto-tagging
  step (likely a Claude call: read description → output structured tags). Design
  the job schema with this in mind now.
- **Weight tuning**: the 35/25/25 split is a starting guess. Build 5–10 real
  test profiles with hand-decided "correct" matches and tune weights until the
  algorithm agrees. These also act as regression tests.

## Conventions

- Keep matching logic deterministic and testable; isolate LLM calls behind small
  functions so they can be stubbed in tests.
- Don't reintroduce Streamlit for the production UI.
