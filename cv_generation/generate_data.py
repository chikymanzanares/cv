from __future__ import annotations

import json
import os
import random
import re
from datetime import datetime, timezone
from pathlib import Path

from cv_generation.settings import get_settings
from cv_generation.services.anthropic_client import AnthropicClient
from cv_generation.services.openrouter_client import OpenRouterClient


PERSONA_TYPES = [
    "career switcher",
    "self-taught developer",
    "academic researcher",
    "startup engineer",
    "corporate enterprise architect",
]

SENIORITY_LEVELS = ["junior", "mid", "senior"]
EDU_COUNTRIES = ["Spain", "Germany", "UK", "India"]

WRITING_STYLES = [
    "formal",
    "concise",
    "verbose",
    "narrative",
    "technical",
    "action-oriented",
    "results-driven",
    "minimal",
    "detailed",
    "punchy",
    "descriptive",
    "academic",
    "business-casual",
    "storytelling",
    "dry and factual",
    "creative",
    "bullet-heavy",
]

ROLES = ["Backend Engineer", "Data Scientist", "Product Manager", "DevOps Engineer", "UX Designer"]
LANGUAGES = ["en", "es", "fr", "de"]

# Optional sections: randomly omit some to increase variability
OPTIONAL_SECTIONS = ["projects", "certifications", "education", "languages"]
SUMMARY_LENGTHS = ["one_line", "short", "paragraph"]
# Weight for using alternative section titles (more = more variety in section names)
USE_ALTERNATIVE_SECTION_LABELS_WEIGHT = 0.7

# Presets of section titles for variety (key -> display title). One preset chosen per CV when using alternatives.
SECTION_LABEL_PRESETS = [
    {"summary": "Summary", "experience": "Experience", "education": "Education", "skills": "Skills", "languages": "Languages", "projects": "Projects", "certifications": "Certifications", "interests": "Interests", "profile": "Profile"},
    {"summary": "Professional Summary", "experience": "Work History", "education": "Education", "skills": "Core Competencies", "languages": "Languages", "projects": "Key Projects", "certifications": "Certifications", "interests": "Interests", "profile": "Profile"},
    {"summary": "About Me", "experience": "Employment", "education": "Academic Background", "skills": "Skills", "languages": "Languages", "projects": "Projects", "certifications": "Licenses & Certifications", "interests": "Personal", "profile": "About Me"},
    {"summary": "Executive Summary", "experience": "Career History", "education": "Qualifications", "skills": "Technical Skills", "languages": "Language Skills", "projects": "Notable Projects", "certifications": "Certifications", "interests": "Outside Work", "profile": "Executive Summary"},
    {"summary": "Profile", "experience": "Professional Experience", "education": "Education", "skills": "Expertise", "languages": "Languages", "projects": "Selected Projects", "certifications": "Credentials", "interests": "Hobbies", "profile": "Profile"},
    {"summary": "Overview", "experience": "Work Experience", "education": "Studies", "skills": "Competencies", "languages": "Languages", "projects": "Projects", "certifications": "Certifications", "interests": "Leisure", "profile": "Overview"},
    {"summary": "Introduction", "experience": "Employment History", "education": "Academic", "skills": "Skills & Tools", "languages": "Languages", "projects": "Projects", "certifications": "Certifications", "interests": "Personal Interests", "profile": "Introduction"},
    {"summary": "Resumen profesional", "experience": "Experiencia laboral", "education": "Formación", "skills": "Competencias", "languages": "Idiomas", "projects": "Proyectos", "certifications": "Certificaciones", "interests": "Intereses", "profile": "Perfil"},
    {"summary": "Profil", "experience": "Berufserfahrung", "education": "Ausbildung", "skills": "Kompetenzen", "languages": "Sprachen", "projects": "Projekte", "certifications": "Zertifizierungen", "interests": "Interessen", "profile": "Profil"},
    {"summary": "Profil professionnel", "experience": "Expérience", "education": "Formation", "skills": "Compétences", "languages": "Langues", "projects": "Projets", "certifications": "Certifications", "interests": "Centres d'intérêt", "profile": "Profil"},
]
# "bullets" = classic bullet list; "paragraphs" = one narrative paragraph per role
EXPERIENCE_STYLES = ["bullets", "paragraphs"]
# Optional extra section (hobbies/interests) with variable name
INCLUDE_INTERESTS_SECTION_WEIGHT = 0.4  # 40% of CVs get this section

# Target length: one_page (compact), two_pages, long (2–3 pages)
PAGE_TARGET_WEIGHTS = [0.45, 0.35, 0.20]  # one_page, two_pages, long
PAGE_TARGETS = ["one_page", "two_pages", "long"]

# Content format: structured (sections/bullets) vs narrative (all in one prose block)
CONTENT_STYLE_WEIGHT_NARRATIVE = 0.15  # 15% of CVs: everything in one/few paragraphs

# Short guidance per writing style so the LLM varies tone and structure
WRITING_STYLE_GUIDANCE = {
    "formal": "Use formal language, complete sentences, avoid slang.",
    "concise": "Short sentences. One line per idea. No filler.",
    "verbose": "Full sentences and detailed descriptions. Explain context.",
    "narrative": "Tell a story. Use flowing prose and cause-effect.",
    "technical": "Precise terminology, metrics, tech stack names. Straight to the point.",
    "action-oriented": "Start bullets with strong verbs (Led, Built, Designed). Focus on impact.",
    "results-driven": "Emphasize outcomes and numbers (%, €, time saved). Quantify where possible.",
    "minimal": "Few words. Keywords and dates. No long sentences.",
    "detailed": "Expand on responsibilities and context. 2–3 sentences per role where useful.",
    "punchy": "Short, bold phrases. No filler. High impact per line.",
    "descriptive": "Rich adjectives and context. Describe the environment and scope.",
    "academic": "Precise, measured tone. Mention publications or research if it fits the persona.",
    "business-casual": "Professional but approachable. Slightly conversational where appropriate.",
    "storytelling": "Frame experience as a journey. Connect roles and growth.",
    "dry and factual": "Neutral tone. Dates, titles, facts only. No sales language.",
    "creative": "Vivid language. Stand-out phrasing. Avoid clichés.",
    "bullet-heavy": "Many short bullets per role. Scannable. Few full paragraphs.",
}


# ---------------------------
# PROVIDER RESOLUTION
# ---------------------------

def resolve_provider(settings) -> str:
    """
    If LLM_PROVIDER=random, choose available provider per CV.
    Otherwise use configured one.
    """
    if settings.llm_provider != "random":
        return settings.llm_provider

    available = []

    if settings.anthropic_api_key:
        available.append("anthropic")

    if settings.openrouter_api_key:
        available.append("openrouter")

    if not available:
        raise RuntimeError("LLM_PROVIDER=random but no API keys found.")

    return random.choice(available)


# ---------------------------
# PROMPT
# ---------------------------

def read_prompt_template(version: str = "v2") -> str:
    path = Path(f"cv_generation/prompts/cv_json_{version}.txt")
    if not path.exists():
        raise FileNotFoundError(f"Missing prompt template: {path}")
    return path.read_text(encoding="utf-8")


def _sanitize_json_control_chars(raw: str) -> str:
    """Escape control characters inside JSON string values so json.loads() succeeds."""
    result = []
    i = 0
    in_string = False
    escape_next = False
    while i < len(raw):
        c = raw[i]
        if escape_next:
            result.append(c)
            escape_next = False
            i += 1
            continue
        if c == "\\" and in_string:
            result.append(c)
            escape_next = True
            i += 1
            continue
        if c == '"' and not escape_next:
            in_string = not in_string
            result.append(c)
            i += 1
            continue
        if in_string and ord(c) < 32:
            if c == "\n":
                result.append("\\n")
            elif c == "\r":
                result.append("\\r")
            elif c == "\t":
                result.append("\\t")
            else:
                result.append(" ")
            i += 1
            continue
        result.append(c)
        i += 1
    return "".join(result)


def _prepare_json_raw(raw: str) -> str:
    """Strip markdown code fences and fix common LLM JSON mistakes."""
    raw = raw.strip()
    # Remove ```json ... ``` or ``` ... ```
    if raw.startswith("```"):
        raw = re.sub(r"^```(?:json)?\s*", "", raw)
        raw = re.sub(r"\s*```\s*$", "", raw)
        raw = raw.strip()
    # Fix trailing commas only when comma is immediately followed by ] or } (no space/newline),
    # so we never touch commas inside string values.
    raw = re.sub(r",([}\]])", r"\1", raw)
    return raw


def _close_truncated_json(raw: str) -> str:
    """If JSON was cut off mid-string or with unclosed brackets, close it so loads() can succeed."""
    in_string = False
    escape = False
    depth_curly = 0
    depth_square = 0
    i = 0
    while i < len(raw):
        c = raw[i]
        if escape:
            escape = False
            i += 1
            continue
        if c == "\\" and in_string:
            escape = True
            i += 1
            continue
        if c == '"':
            in_string = not in_string
            i += 1
            continue
        if not in_string:
            if c == "{":
                depth_curly += 1
            elif c == "}":
                depth_curly -= 1
            elif c == "[":
                depth_square += 1
            elif c == "]":
                depth_square -= 1
        i += 1
    out = raw
    if in_string:
        out += '"'
    out += "]" * max(0, depth_square) + "}" * max(0, depth_curly)
    return out


def build_structure_instructions(cfg: dict) -> str:
    """Build variability instructions for the LLM from profile config."""
    parts = []

    content_style = cfg.get("content_style", "structured")
    if content_style == "narrative":
        parts.append(
            "This CV must be written as continuous prose, 'a lo bestia'. Put the ENTIRE CV body in data.narrative: one or several long paragraphs covering summary, experience, education, skills, everything. No bullets, no section headings in the body—just flowing text. Leave experience, education, skills, summary as empty [] or omit; the only body content is the string data.narrative. Include dates and role names inside the prose."
        )
        return " ".join(parts)

    omit = cfg.get("omit_sections", [])
    if omit:
        parts.append(
            f"Do NOT include these sections (leave as empty arrays [] or omit the key): {', '.join(omit)}."
        )
    else:
        parts.append("Include all sections that fit the profile (experience, education, skills, etc.).")

    sl = cfg.get("summary_length", "paragraph")
    if sl == "one_line":
        parts.append("Summary must be exactly one short sentence (max 1–2 lines).")
    elif sl == "short":
        parts.append("Summary: 2–3 sentences only.")
    else:
        parts.append("Summary: one full paragraph (3–5 sentences).")

    preset = cfg.get("section_label_preset")
    if preset:
        labels_str = ", ".join(f"{k} -> \"{v}\"" for k, v in preset.items())
        parts.append(
            f"Use these exact section titles and return them in data.section_labels (use the same key): {labels_str}. Include in section_labels only the keys for sections you actually have in data."
        )
    else:
        parts.append("Use standard section titles (Summary, Experience, Education, Skills, Languages). You may omit section_labels or set it to {}.")

    exp_style = cfg.get("experience_style", "bullets")
    if exp_style == "paragraphs":
        parts.append(
            "For each experience entry provide a single 'paragraph' (narrative text describing the role and achievements). Leave 'bullets' empty [] or omit."
        )
    else:
        parts.append("For each experience use 'bullets' (list of 2–5 achievement bullets). No paragraph field needed.")

    if cfg.get("include_interests_section"):
        parts.append(
            "Include an optional section for hobbies/personal interests. Choose a title (e.g. Hobbies, Interests, Personal, Outside Work, Leisure, Personal Interests) and put it in section_labels.interests. Put the content in data.interests as an array of 2–5 short items (e.g. ['Reading', 'Cycling']) or as one short paragraph string."
        )

    page_target = cfg.get("page_target", "one_page")
    if page_target == "two_pages":
        parts.append(
            "This CV should fill about 2 pages. Include 4–5 experience entries, a full-paragraph summary (4–6 sentences), 4–5 bullets per role (or substantial paragraphs), 2+ education entries if relevant, and 1–2 projects. More content than a one-pager."
        )
    elif page_target == "long":
        parts.append(
            "This CV should be 2–3 pages long. Include 5–7 experience entries, a detailed summary (2 short paragraphs or 6–8 sentences), 5–6 bullets per role (or long narrative paragraphs), multiple education entries, 2–3 projects, certifications. Dense, comprehensive content."
        )
    else:
        parts.append("Keep this CV to about one page: 2–3 experience entries, concise summary, 2–4 bullets per role.")

    return " ".join(parts)


# ---------------------------
# RANDOM PROFILE CONFIG
# ---------------------------

def sample_profile_config() -> dict:
    # Omit a random subset of optional sections (often 0–2, sometimes more)
    n_omit = random.choices([0, 1, 2, 3], weights=[40, 35, 20, 5], k=1)[0]
    omit_sections = random.sample(OPTIONAL_SECTIONS, min(n_omit, len(OPTIONAL_SECTIONS)))
    use_alternative = random.random() < USE_ALTERNATIVE_SECTION_LABELS_WEIGHT
    section_label_preset = random.choice(SECTION_LABEL_PRESETS) if use_alternative else None

    page_target = random.choices(PAGE_TARGETS, weights=PAGE_TARGET_WEIGHTS, k=1)[0]
    content_style = "narrative" if random.random() < CONTENT_STYLE_WEIGHT_NARRATIVE else "structured"

    return {
        "language": random.choice(LANGUAGES),
        "seniority": random.choice(SENIORITY_LEVELS),
        "persona_type": random.choice(PERSONA_TYPES),
        "writing_style": random.choice(WRITING_STYLES),
        "role": random.choice(ROLES),
        "education_country": random.choice(EDU_COUNTRIES),
        "omit_sections": omit_sections,
        "summary_length": random.choice(SUMMARY_LENGTHS),
        "section_label_preset": section_label_preset,
        "experience_style": random.choice(EXPERIENCE_STYLES),
        "include_interests_section": random.random() < INCLUDE_INTERESTS_SECTION_WEIGHT,
        "page_target": page_target,
        "content_style": content_style,
    }


# ---------------------------
# LOCAL HEADSHOTS
# ---------------------------

def load_random_headshot(pool: list[Path]) -> tuple[bytes, str]:
    if not pool:
        raise RuntimeError("Headshot pool empty.")

    img = random.choice(pool)
    pool.remove(img)
    return img.read_bytes(), img.name


def load_headshot_pool() -> list[Path]:
    pool_dir = Path("cv_generation/assets/headshots")
    imgs = (
        list(pool_dir.glob("*.png")) +
        list(pool_dir.glob("*.jpg")) +
        list(pool_dir.glob("*.jpeg"))
    )
    if not imgs:
        raise FileNotFoundError(
            "Add at least 1 image to cv_generation/assets/headshots/"
        )
    random.shuffle(imgs)
    return imgs


# ---------------------------
# TEXT GENERATION
# ---------------------------

def generate_text(provider, anthropic, openrouter_text, settings, prompt) -> str:

    if provider == "anthropic":
        assert anthropic is not None
        return anthropic.generate_text(
            model=settings.anthropic_text_model,
            prompt=prompt,
            temperature=0.7,
        )

    elif provider == "openrouter":
        assert openrouter_text is not None
        return openrouter_text.chat_completion_text(
            model=settings.openrouter_text_model,
            prompt=prompt,
            temperature=0.7,
        )

    else:
        raise RuntimeError(f"Unsupported provider={provider}")


# ---------------------------
# MAIN
# ---------------------------

def main(n: int = 30) -> None:

    settings = get_settings()
    out_root = Path(settings.output_dir)
    out_root.mkdir(parents=True, exist_ok=True)

    prompt_version = "cv_json_v2"
    prompt_tpl = read_prompt_template("v2")
    headshot_pool = load_headshot_pool()

    anthropic = None
    openrouter_text = None

    if settings.anthropic_api_key:
        anthropic = AnthropicClient(api_key=settings.anthropic_api_key)

    if settings.openrouter_api_key:
        openrouter_text = OpenRouterClient(api_key=settings.openrouter_api_key)

    for i in range(1, n + 1):

        provider = resolve_provider(settings)

        cv_id = f"cv_{i:03d}"
        created_at = datetime.now(timezone.utc).isoformat()
        cfg = sample_profile_config()

        text_model = (
            settings.anthropic_text_model
            if provider == "anthropic"
            else settings.openrouter_text_model
        )

        structure_instructions = build_structure_instructions(cfg)
        writing_style_guidance = WRITING_STYLE_GUIDANCE.get(
            cfg["writing_style"], "Use clear, professional language."
        )
        prompt = prompt_tpl.format(
            cv_id=cv_id,
            created_at=created_at,
            pipeline_version=settings.pipeline_version,
            provider=provider,
            text_model=text_model,
            image_model=settings.openrouter_image_model,
            structure_instructions=structure_instructions,
            writing_style_guidance=writing_style_guidance,
            **cfg,
        )

        cv_dir = out_root / cv_id
        cv_dir.mkdir(parents=True, exist_ok=True)

        for attempt in range(2):
            raw = generate_text(provider, anthropic, openrouter_text, settings, prompt)
            raw = _sanitize_json_control_chars(raw)
            raw = _prepare_json_raw(raw)
            try:
                cv_obj = json.loads(raw)
                break
            except json.JSONDecodeError as e:
                if "Unterminated string" in str(e) or "Expecting" in str(e):
                    raw = _close_truncated_json(raw)
                    try:
                        cv_obj = json.loads(raw)
                        break
                    except json.JSONDecodeError:
                        pass
                if attempt == 0:
                    continue
                (cv_dir / "raw_llm_output.txt").write_text(raw, encoding="utf-8")
                raise RuntimeError(f"Invalid JSON for {cv_id} (after retry)")

        img_bytes, asset_name = load_random_headshot(headshot_pool)

        cv_obj.setdefault("meta", {})["prompt_version"] = prompt_version
        cv_obj["meta"]["photo_source"] = "local_asset"
        cv_obj["meta"]["photo_asset"] = asset_name
        # Persist the actual config we used so we know how this CV was generated
        cv_obj["meta"]["generation_config"] = {
            "writing_style": cfg["writing_style"],
            "summary_length": cfg["summary_length"],
            "experience_style": cfg["experience_style"],
            "omit_sections": cfg["omit_sections"],
            "include_interests_section": cfg["include_interests_section"],
            "section_label_preset": cfg.get("section_label_preset"),
            "page_target": cfg["page_target"],
            "content_style": cfg["content_style"],
        }

        (cv_dir / "cv.json").write_text(
            json.dumps(cv_obj, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        (cv_dir / "photo.png").write_bytes(img_bytes)

        print(f"[OK] Generated {cv_id} with {provider}")

    print(f"\n🎉 Generated {n} CVs.")


if __name__ == "__main__":
    n = int(os.getenv("N", "30"))
    main(n=n)