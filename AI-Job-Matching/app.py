import io
import os

import pandas as pd
import streamlit as st

from matcher import match_profile

st.set_page_config(page_title="EA Job Matcher", page_icon="🌍", layout="centered")

# ── Styling ──────────────────────────────────────────────────────────────────
st.markdown("""
<style>
.job-card {
    background: #f8f9fa;
    border-left: 4px solid #2e7d32;
    border-radius: 6px;
    padding: 1rem 1.2rem;
    margin-bottom: 1rem;
}
.job-title { font-size: 1.1rem; font-weight: 700; color: #1a1a1a; }
.job-meta { color: #555; font-size: 0.85rem; margin: 0.2rem 0 0.6rem; }
.job-explanation { color: #2e2e2e; font-size: 0.95rem; }
.tag {
    display: inline-block;
    background: #e8f5e9;
    color: #2e7d32;
    border-radius: 12px;
    padding: 2px 10px;
    font-size: 0.75rem;
    margin: 2px 2px 0 0;
}
</style>
""", unsafe_allow_html=True)

# ── Header ────────────────────────────────────────────────────────────────────
st.title("EA Job Matcher")
st.caption("Find high-impact roles matched to your skills, values, and goals.")
st.divider()

# ── API Key ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.header("Settings")
    api_key = st.text_input(
        "Anthropic API Key",
        type="password",
        placeholder="sk-ant-...",
        help="Get one at console.anthropic.com — $5 credit handles hundreds of searches.",
    )
    top_n = st.slider("Matches to show per person", 3, 8, 5)
    st.divider()
    st.caption("Built as a proof of concept for AI-powered EA career matching.")

# ── Mode toggle ───────────────────────────────────────────────────────────────
mode = st.radio("Who is using this?", ["Individual — find my matches", "Advisor — upload a CSV of candidates"], horizontal=True)
st.divider()

# ── Helper: render results ────────────────────────────────────────────────────
def render_results(name, results):
    if name:
        st.subheader(f"Matches for {name}")
    for i, job in enumerate(results):
        tags_html = "".join(f'<span class="tag">{t}</span>' for t in job["cause_areas"])
        st.markdown(f"""
<div class="job-card">
  <div class="job-title">#{i+1} — {job['title']}</div>
  <div class="job-meta">{job['org']} · {job['location']} · {job['salary']}</div>
  <div style="margin-bottom:0.5rem">{tags_html}</div>
  <div class="job-explanation">{job['explanation']}</div>
</div>
""", unsafe_allow_html=True)


# ── Mode A: Individual ────────────────────────────────────────────────────────
if mode.startswith("Individual"):
    with st.form("individual_form"):
        st.subheader("Tell us about yourself")
        col1, col2 = st.columns(2)
        with col1:
            name = st.text_input("Your name", placeholder="Alice")
            cause_areas = st.multiselect(
                "Cause areas you care about",
                ["AI safety", "AI governance", "Biosecurity", "Global health", "Global development",
                 "Nuclear risk", "Existential risk", "Longtermism", "Effective altruism", "Movement building"],
            )
            role_type = st.selectbox(
                "Preferred role type",
                ["Any", "Research", "Engineering", "Policy", "Operations", "Communications",
                 "Community", "Fundraising", "Talent", "Programme management"],
            )
        with col2:
            skills = st.text_input("Your key skills", placeholder="e.g. Python, research, writing, economics")
            location = st.text_input("Location preference", placeholder="e.g. Remote, UK, US, flexible")
            goals = st.text_area("Your goals in 1–2 sentences", placeholder="I want to transition into AI safety research from a software background...", height=100)

        submitted = st.form_submit_button("Find my matches", type="primary", use_container_width=True)

    if submitted:
        if not api_key:
            st.error("Please enter your Anthropic API key in the sidebar.")
        elif not cause_areas and not skills and not goals:
            st.warning("Please fill in at least one field.")
        else:
            profile = {
                "cause_areas": ", ".join(cause_areas),
                "skills": skills,
                "goals": goals,
                "location": location,
                "role_type": role_type if role_type != "Any" else "",
            }
            with st.spinner("Finding your best matches..."):
                try:
                    results = match_profile(profile, api_key, top_n=top_n)
                    st.success(f"Found {len(results)} matches for {name or 'you'}!")
                    render_results(name, results)
                except Exception as e:
                    st.error(f"Something went wrong: {e}")


# ── Mode B: Advisor CSV ───────────────────────────────────────────────────────
else:
    st.subheader("Upload candidate CSV")

    st.markdown("""
**Required columns:** `name`, `cause_areas`, `skills`, `goals`
**Optional columns:** `location`, `role_type`

Download a template below to get started.
""")

    template_df = pd.DataFrame([
        {"name": "Alice", "cause_areas": "AI safety; biosecurity", "skills": "research; writing", "goals": "Transition into AI safety research", "location": "Remote", "role_type": "Research"},
        {"name": "Bob", "cause_areas": "global health", "skills": "Python; data analysis", "goals": "Use technical skills for global health impact", "location": "UK", "role_type": "Technical"},
    ])
    csv_bytes = template_df.to_csv(index=False).encode()
    st.download_button("Download template CSV", csv_bytes, "candidates_template.csv", "text/csv")

    uploaded = st.file_uploader("Upload your CSV", type="csv")

    if uploaded:
        df = pd.read_csv(uploaded)
        required = {"name", "cause_areas", "skills", "goals"}
        missing = required - set(df.columns.str.lower())
        if missing:
            st.error(f"CSV is missing columns: {', '.join(missing)}")
        else:
            df.columns = df.columns.str.lower()
            st.success(f"Loaded {len(df)} candidates.")
            st.dataframe(df, use_container_width=True)

            if st.button("Run matching for all candidates", type="primary", use_container_width=True):
                if not api_key:
                    st.error("Please enter your Anthropic API key in the sidebar.")
                else:
                    all_results = []
                    progress = st.progress(0, text="Processing candidates...")

                    for i, row in df.iterrows():
                        progress.progress((i) / len(df), text=f"Matching {row.get('name', f'candidate {i+1}')}...")
                        profile = {
                            "cause_areas": str(row.get("cause_areas", "")),
                            "skills": str(row.get("skills", "")),
                            "goals": str(row.get("goals", "")),
                            "location": str(row.get("location", "flexible")),
                            "role_type": str(row.get("role_type", "")),
                        }
                        try:
                            results = match_profile(profile, api_key, top_n=top_n)
                            for rank, job in enumerate(results):
                                all_results.append({
                                    "candidate": row.get("name", f"Candidate {i+1}"),
                                    "rank": rank + 1,
                                    "job_title": job["title"],
                                    "org": job["org"],
                                    "location": job["location"],
                                    "salary": job["salary"],
                                    "cause_areas": ", ".join(job["cause_areas"]),
                                    "why_good_fit": job["explanation"],
                                })
                        except Exception as e:
                            st.warning(f"Error for {row.get('name', f'row {i}')}: {e}")

                    progress.progress(1.0, text="Done!")
                    st.divider()

                    # Show results per candidate
                    for name in df["name"].unique():
                        person_results = [r for r in all_results if r["candidate"] == name]
                        jobs_for_render = []
                        for r in person_results:
                            jobs_for_render.append({
                                "title": r["job_title"],
                                "org": r["org"],
                                "location": r["location"],
                                "salary": r["salary"],
                                "cause_areas": r["cause_areas"].split(", "),
                                "explanation": r["why_good_fit"],
                            })
                        render_results(name, jobs_for_render)
                        st.divider()

                    # Download button
                    results_df = pd.DataFrame(all_results)
                    csv_out = results_df.to_csv(index=False).encode()
                    st.download_button(
                        "Download all results as CSV",
                        csv_out,
                        "job_matches.csv",
                        "text/csv",
                        use_container_width=True,
                    )
