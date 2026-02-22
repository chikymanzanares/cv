from dataclasses import dataclass
import os


@dataclass(frozen=True)
class Settings:
    llm_provider: str
    anthropic_api_key: str | None
    anthropic_text_model: str
    openrouter_api_key: str | None
    openrouter_text_model: str
    openrouter_image_model: str
    generate_images: bool
    pipeline_version: str
    output_dir: str
    max_tokens: int


def get_settings() -> Settings:
    return Settings(
        llm_provider=os.getenv("LLM_PROVIDER", "anthropic"),
        anthropic_api_key=os.getenv("ANTHROPIC_API_KEY"),
        anthropic_text_model=os.getenv(
            "ANTHROPIC_TEXT_MODEL",
            "claude-3-haiku-20240307"
        ),
        openrouter_api_key=os.getenv("OPENROUTER_API_KEY"),
        openrouter_text_model=os.getenv(
            "OPENROUTER_TEXT_MODEL",
            "mistralai/mistral-small-3.1-24b-instruct:free"
        ),
        openrouter_image_model=os.getenv(
            "OPENROUTER_IMAGE_MODEL",
            "black-forest-labs/flux.1-schnell"
        ),
        generate_images=os.getenv("GENERATE_IMAGES", "0") == "1",
        pipeline_version=os.getenv("GENERATION_PIPELINE_VERSION", "1.1.0"),
        output_dir=os.getenv("GENERATION_OUTPUT_DIR", "cv_generation/data/cvs"),
        max_tokens=int(os.getenv("CV_GEN_MAX_TOKENS", "4096")),
    )