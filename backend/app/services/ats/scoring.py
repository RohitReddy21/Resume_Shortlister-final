import json
import re
import logging
import os
from typing import Any, Dict

logger = logging.getLogger(__name__)

_model = None
_model_load_attempted = False


def _get_semantic_model():
    global _model, _model_load_attempted
    if os.getenv("ATS_ENABLE_SEMANTIC_SCORING", "").lower() not in {"1", "true", "yes"}:
        return None
    if _model_load_attempted:
        return _model

    _model_load_attempted = True
    try:
        from sentence_transformers import SentenceTransformer

        _model = SentenceTransformer("all-MiniLM-L6-v2", local_files_only=True)
    except Exception as exc:
        logger.warning("Semantic scoring model unavailable, falling back to Jaccard: %s", exc)
        _model = None
    return _model


def normalize_skill_name(skill: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", skill.lower()).strip()


def _load_json_text(text: str) -> list[str]:
    try:
        data = json.loads(text)
        if isinstance(data, list):
            return [str(x) for x in data if x is not None]
    except Exception:
        pass
    if not text:
        return []
    return [part.strip() for part in re.split(r"[,;|\\n]+", text) if part.strip()]


def _extract_resume_skills(parsed: dict[str, Any]) -> list[str]:
    skills = parsed.get("skills") or []
    extracted = []
    for item in skills:
        if isinstance(item, dict):
            extracted.append(item.get("name") or item.get("value") or "")
        else:
            extracted.append(str(item))
    return [normalize_skill_name(s) for s in extracted if s]


def _extract_job_skills(job: Any) -> list[str]:
    if job is None:
        return []
    if isinstance(job.skills, str):
        return [normalize_skill_name(s) for s in _load_json_text(job.skills)]
    if isinstance(job.skills, list):
        return [normalize_skill_name(str(s)) for s in job.skills]
    return []


def _extract_text_fields(parsed: dict[str, Any], keys: list[str]) -> str:
    pieces: list[str] = []
    for key in keys:
        value = parsed.get(key)
        if isinstance(value, str):
            pieces.append(value)
        elif isinstance(value, dict):
            pieces.append(str(value.get("value", "")))
        elif isinstance(value, list):
            for item in value:
                if isinstance(item, str):
                    pieces.append(item)
                elif isinstance(item, dict):
                    pieces.extend(
                        str(item.get(field, ""))
                        for field in ("raw", "title_company", "title_line", "company_line", "name", "value")
                        if item.get(field)
                    )
    return " ".join(pieces).strip()


def _jaccard_similarity(set_a: set[str], set_b: set[str]) -> float:
    if not set_a or not set_b:
        return 0.0
    intersection = set_a.intersection(set_b)
    union = set_a.union(set_b)
    return len(intersection) / len(union)


def _semantic_similarity(text_a: str, text_b: str) -> float:
    """Calculate semantic similarity between two texts using SentenceTransformers."""
    if not text_a or not text_b:
        return 0.0
    
    model = _get_semantic_model()
    if model is None:
        # Fallback to Jaccard if model is not available
        return _jaccard_similarity(
            set(normalize_skill_name(word) for word in text_a.split()),
            set(normalize_skill_name(word) for word in text_b.split())
        )
    
    try:
        from sklearn.metrics.pairwise import cosine_similarity

        embeddings = model.encode([text_a[:2000], text_b[:2000]]) # Limit length for speed/memory
        sim = cosine_similarity([embeddings[0]], [embeddings[1]])[0][0]
        # Map from [-1, 1] to [0, 1]
        return max(0.0, float(sim))
    except Exception as e:
        logger.error(f"Error computing semantic similarity: {e}")
        return 0.0


def _score_achievements(parsed_resume: dict[str, Any]) -> float:
    """Heuristics for scoring achievements based on quantitative metrics and action verbs."""
    resume_text = parsed_resume.get("parsed_text", "")
    if not resume_text:
        return 0.0
        
    # Look for numbers, percentages, dollar signs which indicate quantitative achievements
    quantitative_matches = len(re.findall(r'(\d+%|\$\d+|\d+\.\d+|\b\d+\b)', resume_text))
    
    # Action verbs indicating impact
    impact_verbs = ["increased", "reduced", "improved", "saved", "managed", "led", "developed", "launched", "delivered", "optimized"]
    verb_matches = sum(1 for verb in impact_verbs if verb in resume_text.lower())
    
    score = min(1.0, (quantitative_matches * 0.1) + (verb_matches * 0.05))
    return score


def _score_culture_fit(parsed_resume: dict[str, Any], job_text: str) -> float:
    """Heuristic for culture fit based on soft skills and keywords."""
    culture_keywords = ["collaborative", "team", "agile", "fast-paced", "innovative", "remote", "communication", "leadership", "mentoring", "autonomous"]
    
    job_culture_words = [word for word in culture_keywords if word in job_text.lower()]
    if not job_culture_words:
        return 0.5 # Neutral if job doesn't specify
        
    resume_text = parsed_resume.get("parsed_text", "").lower()
    matches = sum(1 for word in job_culture_words if word in resume_text)
    
    return min(1.0, matches / len(job_culture_words))


def score_resume_against_job(parsed_resume: dict[str, Any], job: Any) -> dict[str, Any]:
    # 1. Skills Scoring
    resume_skills = set(_extract_resume_skills(parsed_resume))
    job_skills = set(_extract_job_skills(job))

    matched = sorted(resume_skills.intersection(job_skills))
    missing = sorted(job_skills.difference(resume_skills))

    skill_score = 0.0
    if job_skills:
        skill_score = len(matched) / len(job_skills)

    # 2. Experience Overlap (now using Semantic Similarity as an option)
    resume_experience_text = _extract_text_fields(parsed_resume, ["experiences", "companies"])
    job_text = " ".join(
        filter(
            None,
            [
                getattr(job, "description", None),
                getattr(job, "title", None),
                getattr(job, "requirements", None),
            ],
        )
    )
    
    experience_match_score = _semantic_similarity(resume_experience_text, job_text)

    # 3. Education Match
    education_text = _extract_text_fields(parsed_resume, ["education", "certifications", "languages"])
    education_match_score = 0.5 if education_text else 0.0
    
    # 4. Project Relevance
    resume_projects_text = _extract_text_fields(parsed_resume, ["projects"])
    project_score = _semantic_similarity(resume_projects_text, job_text) if resume_projects_text else 0.0

    # 5. Achievements
    achievement_score = _score_achievements(parsed_resume)
    
    # 6. Overall Similarity (Semantic)
    resume_full_text = parsed_resume.get("parsed_text") or ""
    overall_similarity = _semantic_similarity(resume_full_text, job_text)

    # 7. Culture Fit
    culture_fit_score = _score_culture_fit(parsed_resume, job_text)

    # 8. Confidence Score (based on parsed data completeness)
    fields_found = sum(1 for key in ["skills", "experiences", "education", "projects", "emails", "phones"] if parsed_resume.get(key))
    confidence_score = min(1.0, fields_found / 6.0)

    weights = {
        "skills": 0.35,
        "experience": 0.20,
        "similarity": 0.15,
        "projects": 0.10,
        "achievements": 0.10,
        "education": 0.05,
        "culture_fit": 0.05,
    }

    total_score = (
        skill_score * weights["skills"]
        + experience_match_score * weights["experience"]
        + overall_similarity * weights["similarity"]
        + project_score * weights["projects"]
        + achievement_score * weights["achievements"]
        + education_match_score * weights["education"]
        + culture_fit_score * weights["culture_fit"]
    )

    strengths = []
    weaknesses = []
    if matched:
        strengths.append(f"Matched {len(matched)} required skill(s)")
    if missing:
        weaknesses.append(f"Missing {len(missing)} required skill(s)")
    if experience_match_score < 0.4:
        weaknesses.append("Experience doesn't closely align with job description.")
    if achievement_score > 0.7:
        strengths.append("Strong quantitative achievements and impact demonstrated.")
    if confidence_score < 0.5:
        weaknesses.append("Resume parsing was incomplete; some sections may be missing.")

    recommendations = []
    if missing:
        recommendations.append("Add or highlight the missing required skills in your resume.")
    if experience_match_score < 0.4:
        recommendations.append("Emphasize relevant projects, companies, or accomplishments tied to this job.")
    if achievement_score < 0.3:
        recommendations.append("Include more quantitative metrics and impactful action verbs in your experience.")

    score_breakdown = {
        "skills": f"Candidate matches {len(matched)} out of {len(job_skills)} required skills.",
        "experience": f"Semantic overlap between candidate's work history and job requirements is {experience_match_score:.0%}.",
        "similarity": f"Overall contextual alignment with the job description is {overall_similarity:.0%}.",
        "projects": f"Relevance of listed projects to the role is {project_score:.0%}.",
        "achievements": f"Evidence of impact (numbers, metrics, action verbs) scored at {achievement_score:.0%}.",
        "education": "Relevant education or certifications were detected." if education_match_score > 0 else "No education/certifications detected.",
        "culture_fit": f"Alignment with indicated soft skills and culture keywords is {culture_fit_score:.0%}.",
        "confidence": f"Parser successfully extracted {fields_found} standard sections, yielding {confidence_score:.0%} confidence in this score."
    }

    return {
        "total_score": round(total_score, 4),
        "score_percentage": round(total_score * 100.0, 2),
        "confidence_score": round(confidence_score, 4),
        "weights": weights,
        "component_scores": {
            "skills": round(skill_score, 4),
            "experience": round(experience_match_score, 4),
            "similarity": round(overall_similarity, 4),
            "projects": round(project_score, 4),
            "achievements": round(achievement_score, 4),
            "education": round(education_match_score, 4),
            "culture_fit": round(culture_fit_score, 4),
        },
        "score_breakdown": score_breakdown,
        "matched_skills": matched,
        "missing_skills": missing,
        "strengths": strengths,
        "weaknesses": weaknesses,
        "recommendations": recommendations,
        "explanation": (
            f"Skills: {skill_score:.2f} | Exp: {experience_match_score:.2f} | Sim: {overall_similarity:.2f} | "
            f"Proj: {project_score:.2f} | Achv: {achievement_score:.2f} | Cult: {culture_fit_score:.2f}"
        ),
    }
