from __future__ import annotations

import json
import os
import random
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
WRITING_STYLES = ["formal", "concise", "verbose"]
ROLES = ["Backend Engineer", "Data Scientist", "Product Manager", "DevOps Engineer", "UX Designer"]
LANGUAGES = ["en", "es", "fr", "de"]


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

def read_prompt_template() -> str:
    path = Path("cv_generation/prompts/cv_json_v1.txt")
    if not path.exists():
        raise FileNotFoundError(f"Missing prompt template: {path}")
    return path.read_text(encoding="utf-8")


# ---------------------------
# RANDOM PROFILE CONFIG
# ---------------------------

def sample_profile_config() -> dict:
    return {
        "language": random.choice(LANGUAGES),
        "seniority": random.choice(SENIORITY_LEVELS),
        "persona_type": random.choice(PERSONA_TYPES),
        "writing_style": random.choice(WRITING_STYLES),
        "role": random.choice(ROLES),
        "education_country": random.choice(EDU_COUNTRIES),
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

    prompt_tpl = read_prompt_template()
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

        prompt = prompt_tpl.format(
            cv_id=cv_id,
            created_at=created_at,
            pipeline_version=settings.pipeline_version,
            provider=provider,
            text_model=text_model,
            image_model=settings.openrouter_image_model,
            **cfg,
        )

        cv_dir = out_root / cv_id
        cv_dir.mkdir(parents=True, exist_ok=True)

        raw = generate_text(provider, anthropic, openrouter_text, settings, prompt)

        try:
            cv_obj = json.loads(raw)
        except json.JSONDecodeError:
            (cv_dir / "raw_llm_output.txt").write_text(raw, encoding="utf-8")
            raise RuntimeError(f"Invalid JSON for {cv_id}")

        img_bytes, asset_name = load_random_headshot(headshot_pool)

        cv_obj["meta"]["photo_source"] = "local_asset"
        cv_obj["meta"]["photo_asset"] = asset_name

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