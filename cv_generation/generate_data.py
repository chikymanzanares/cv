from __future__ import annotations

import json
import os
import random
import shutil
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


def read_prompt_template() -> str:
    path = Path("cv_generation/prompts/cv_json_v1.txt")
    if not path.exists():
        raise FileNotFoundError(f"Missing prompt template: {path}")
    return path.read_text(encoding="utf-8")


def sample_profile_config() -> dict:
    return {
        "language": random.choice(LANGUAGES),
        "seniority": random.choice(SENIORITY_LEVELS),
        "persona_type": random.choice(PERSONA_TYPES),
        "writing_style": random.choice(WRITING_STYLES),
        "role": random.choice(ROLES),
        "education_country": random.choice(EDU_COUNTRIES),
    }


def load_headshot_paths() -> list[Path]:
    pool = Path("cv_generation/assets/headshots")
    imgs = list(pool.glob("*.png")) + list(pool.glob("*.jpg")) + list(pool.glob("*.jpeg"))
    if not imgs:
        raise FileNotFoundError(
            "No headshot images found.\n"
            "Add at least 1 image under: cv_generation/assets/headshots/"
        )
    random.shuffle(imgs)
    return imgs


def generate_text_anthropic(client: AnthropicClient, settings, prompt: str) -> str:
    return client.generate_text(
        model=settings.anthropic_text_model,
        prompt=prompt,
        temperature=0.7,
        max_tokens=2000,
    )


def main(n: int = 1) -> None:
    settings = get_settings()

    if settings.llm_provider != "anthropic":
        raise RuntimeError("Use LLM_PROVIDER=anthropic for this setup")

    if not settings.anthropic_api_key:
        raise RuntimeError("ANTHROPIC_API_KEY missing.")

    anthropic = AnthropicClient(api_key=settings.anthropic_api_key)

    openrouter = None
    if settings.generate_images:
        if not settings.openrouter_api_key:
            raise RuntimeError("OPENROUTER_API_KEY required when GENERATE_IMAGES=1")
        openrouter = OpenRouterClient(api_key=settings.openrouter_api_key)

    out_root = Path(settings.output_dir)
    out_root.mkdir(parents=True, exist_ok=True)

    prompt_tpl = read_prompt_template()

    headshots = load_headshot_paths()
    head_idx = 0

    for i in range(1, n + 1):
        cv_id = f"cv_{i:03d}"
        created_at = datetime.now(timezone.utc).isoformat()
        cfg = sample_profile_config()

        prompt = prompt_tpl.format(
            cv_id=cv_id,
            created_at=created_at,
            pipeline_version=settings.pipeline_version,
            provider="anthropic",
            text_model=settings.anthropic_text_model,
            image_model=settings.openrouter_image_model,
            **cfg,
        )

        cv_dir = out_root / cv_id
        cv_dir.mkdir(parents=True, exist_ok=True)

        raw = generate_text_anthropic(anthropic, settings, prompt)

        try:
            cv_obj = json.loads(raw)
        except json.JSONDecodeError:
            (cv_dir / "raw_llm_output.txt").write_text(raw, encoding="utf-8")
            raise RuntimeError(
                f"LLM returned invalid JSON for {cv_id}"
            )

        photo_prompt = cv_obj.get("data", {}).get("photo_prompt") or (
            "Professional LinkedIn-style headshot photo, neutral background, realistic lighting, high quality."
        )

        cv_obj.setdefault("meta", {})

        if not settings.generate_images:
            if head_idx >= len(headshots):
                random.shuffle(headshots)
                head_idx = 0

            chosen = headshots[head_idx]
            head_idx += 1

            shutil.copyfile(chosen, cv_dir / "photo.png")

            cv_obj["meta"]["photo_source"] = "local_asset"
            cv_obj["meta"]["photo_asset"] = chosen.name

        else:
            try:
                assert openrouter is not None
                img_bytes = openrouter.chat_completion_image_bytes(
                    model=settings.openrouter_image_model,
                    prompt=photo_prompt,
                )
                (cv_dir / "photo.png").write_bytes(img_bytes)

                cv_obj["meta"]["photo_source"] = "openrouter_model"
                cv_obj["meta"]["photo_model"] = settings.openrouter_image_model

            except Exception as e:
                print(f"[WARN] Image generation failed ({e}) → local fallback")

                if head_idx >= len(headshots):
                    random.shuffle(headshots)
                    head_idx = 0

                chosen = headshots[head_idx]
                head_idx += 1

                shutil.copyfile(chosen, cv_dir / "photo.png")

                cv_obj["meta"]["photo_source"] = "local_asset_fallback"
                cv_obj["meta"]["photo_asset"] = chosen.name

        (cv_dir / "cv.json").write_text(
            json.dumps(cv_obj, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        print(f"[OK] Generated {cv_id} -> {cv_dir}")


if __name__ == "__main__":
    n = int(os.getenv("N_CVS", "1"))
    main(n=n)