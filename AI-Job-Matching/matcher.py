import json
import os
import re
from pathlib import Path

import anthropic
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity

DATA_PATH = Path(__file__).parent / "data" / "jobs.json"


def load_jobs():
    with open(DATA_PATH) as f:
        return json.load(f)


def job_to_text(job):
    return (
        f"{job['title']} at {job['org']}. "
        f"Cause areas: {', '.join(job['cause_areas'])}. "
        f"Skills: {', '.join(job['skills'])}. "
        f"Role type: {job['role_type']}. "
        f"{job['description']}"
    )


def profile_to_text(profile):
    return (
        f"Person interested in: {profile.get('cause_areas', '')}. "
        f"Skills: {profile.get('skills', '')}. "
        f"Goals: {profile.get('goals', '')}. "
        f"Location preference: {profile.get('location', 'flexible')}. "
        f"Role type preference: {profile.get('role_type', 'any')}."
    )


def get_embeddings(texts, client):
    # Use a simple TF-IDF-style word overlap as fallback if no API,
    # but here we use Anthropic's claude to score directly instead of embeddings
    # since Anthropic doesn't have a dedicated embeddings endpoint.
    # We use keyword overlap for ranking, then LLM for explanations.
    pass


def keyword_score(profile_text, job_text):
    """Simple word overlap score as a proxy for similarity."""
    profile_words = set(re.findall(r'\w+', profile_text.lower()))
    job_words = set(re.findall(r'\w+', job_text.lower()))
    if not profile_words:
        return 0
    overlap = profile_words & job_words
    return len(overlap) / (len(profile_words) ** 0.5)


def rank_jobs(profile, jobs, top_n=5):
    profile_text = profile_to_text(profile)
    scored = []
    for job in jobs:
        job_text = job_to_text(job)
        score = keyword_score(profile_text, job_text)
        scored.append((score, job))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [job for _, job in scored[:top_n]]


def explain_matches(profile, top_jobs, client):
    profile_text = profile_to_text(profile)
    jobs_text = "\n\n".join(
        f"{i+1}. {job['title']} at {job['org']}: {job['description']}"
        for i, job in enumerate(top_jobs)
    )

    prompt = f"""You are a career advisor specialising in high-impact careers in the effective altruism ecosystem.

Here is a candidate's profile:
{profile_text}

Here are their top job matches:
{jobs_text}

For each job, write 2 sentences explaining specifically why it is a good fit for this person based on their goals, skills, and cause area interests. Be concrete and personal, not generic.

Format your response as a numbered list matching the job order above."""

    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1024,
        messages=[{"role": "user", "content": prompt}],
    )
    return message.content[0].text


def parse_explanations(explanation_text, n):
    """Split Claude's numbered response into per-job explanations."""
    parts = re.split(r'\n(?=\d+\.)', explanation_text.strip())
    explanations = []
    for part in parts:
        cleaned = re.sub(r'^\d+\.\s*', '', part).strip()
        if cleaned:
            explanations.append(cleaned)
    # Pad or trim to match n jobs
    while len(explanations) < n:
        explanations.append("This role aligns well with your background and interests.")
    return explanations[:n]


def match_profile(profile, api_key, top_n=5):
    jobs = load_jobs()
    top_jobs = rank_jobs(profile, jobs, top_n=top_n)

    client = anthropic.Anthropic(api_key=api_key)
    explanation_text = explain_matches(profile, top_jobs, client)
    explanations = parse_explanations(explanation_text, len(top_jobs))

    results = []
    for job, explanation in zip(top_jobs, explanations):
        results.append({**job, "explanation": explanation})
    return results
