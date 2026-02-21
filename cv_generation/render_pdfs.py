from __future__ import annotations

import json
import os
import random
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, select_autoescape
from weasyprint import HTML, CSS


@dataclass(frozen=True)
class RenderSettings:
    input_dir: Path
    output_dir: Path
    templates_dir: Path
    static_dir: Path
    css_file: Path
    seed: int | None
    write_html: bool
    force: bool


def _env(templates_dir: Path) -> Environment:
    env = Environment(
        loader=FileSystemLoader(str(templates_dir)),
        autoescape=select_autoescape(["html", "xml"]),
    )
    # Default section titles when section_labels not in CV
    env.globals["section_title"] = lambda cv, key: (cv.get("section_labels") or {}).get(key, {
        "summary": "Summary",
        "experience": "Experience",
        "education": "Education",
        "skills": "Skills",
        "languages": "Languages",
        "projects": "Projects",
        "certifications": "Certifications",
        "interests": "Interests",
        "profile": "Profile",
    }.get(key, key.title()))
    return env


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _list_cv_dirs(input_dir: Path) -> list[Path]:
    return sorted([p for p in input_dir.glob("cv_*") if p.is_dir()])


def _pick_template(cv_obj: dict[str, Any], templates: list[str]) -> str:
    """
    Pick template per CV to increase PDF diversity.
    Bias toward minimal when CV has few sections (avoids empty blocks).
    Deterministic if seed is set (handled by random.seed()).
    """
    data = cv_obj.get("data", {})
    has_education = bool(data.get("education"))
    has_projects = bool(data.get("projects"))
    has_certs = bool(data.get("certifications"))
    has_languages = bool(data.get("languages"))
    full_sections = sum([has_education, has_projects, has_certs, has_languages])

    minimal_tpl = "cv_minimal.html.j2"
    if full_sections == 0 and minimal_tpl in templates:
        # Prefer minimal when there are no optional sections
        weights = [1, 1, 3] if len(templates) == 3 else None
    else:
        weights = None

    if weights and len(weights) == len(templates):
        return random.choices(templates, weights=weights, k=1)[0]
    return random.choice(templates)


def _safe_filename(s: str) -> str:
    return "".join(ch for ch in s if ch.isalnum() or ch in ("-", "_")).strip() or "cv"


def main() -> None:
    settings = RenderSettings(
        input_dir=Path(os.getenv("GENERATION_OUTPUT_DIR", "cv_generation/data/cvs")),
        output_dir=Path(os.getenv("GENERATION_OUTPUT_DIR", "cv_generation/data/cvs")),
        templates_dir=Path(os.getenv("CV_TEMPLATES_DIR", "cv_generation/templates")),
        static_dir=Path(os.getenv("CV_STATIC_DIR", "cv_generation/static")),
        css_file=Path(os.getenv("CV_CSS_FILE", "cv_generation/static/cv.css")),
        seed=int(os.getenv("PDF_SEED")) if os.getenv("PDF_SEED") else None,
        write_html=os.getenv("WRITE_HTML", "1") == "1",
        force=os.getenv("FORCE_PDF", "0") == "1",
    )

    if settings.seed is not None:
        random.seed(settings.seed)

    if not settings.templates_dir.exists():
        raise FileNotFoundError(f"Missing templates dir: {settings.templates_dir}")
    if not settings.css_file.exists():
        raise FileNotFoundError(f"Missing CSS file: {settings.css_file}")

    templates = [
        "cv_modern.html.j2",
        "cv_classic.html.j2",
        "cv_minimal.html.j2",
        "cv_sidebar.html.j2",
        "cv_compact.html.j2",
        "cv_accent.html.j2",
        "cv_warm.html.j2",
        "cv_green.html.j2",
    ]

    jenv = _env(settings.templates_dir)
    css = CSS(filename=str(settings.css_file))

    cv_dirs = _list_cv_dirs(settings.input_dir)
    if not cv_dirs:
        raise RuntimeError(f"No CV folders found in {settings.input_dir} (expected cv_001/ etc.)")

    ok = 0
    for cv_dir in cv_dirs:
        cv_json = cv_dir / "cv.json"
        photo = cv_dir / "photo.png"  # we always write photo.png in your pipeline
        if not cv_json.exists():
            print(f"[SKIP] Missing cv.json in {cv_dir}")
            continue
        if not photo.exists():
            print(f"[WARN] Missing photo.png in {cv_dir} (will render without photo)")

        cv_obj = _load_json(cv_json)
        meta = cv_obj.get("meta", {})
        data = cv_obj.get("data", {})

        # Output names
        pdf_path = cv_dir / "cv.pdf"
        html_path = cv_dir / "cv.html"

        if pdf_path.exists() and not settings.force:
            print(f"[SKIP] Exists {pdf_path} (set FORCE_PDF=1 to overwrite)")
            continue

        available_templates = list(templates)
        if data.get("narrative"):
            available_templates.append("cv_narrative.html.j2")
        tpl_name = _pick_template(cv_obj, available_templates)
        tpl = jenv.get_template(tpl_name)

        # Use relative path so the written HTML works when opened in browser (same dir as photo).
        # WeasyPrint will resolve it via base_url set to cv_dir below.
        photo_uri = "photo.png" if photo.exists() else None

        # Optional theme for cv_modern (so it sometimes has color; other templates have fixed theme)
        theme = (
            random.choice(["", "theme-accent", "theme-warm", "theme-green"])
            if tpl_name == "cv_modern.html.j2"
            else ""
        )

        # Render HTML
        html = tpl.render(
            meta=meta,
            cv=data,
            photo_uri=photo_uri,
            theme=theme,
        )

        if settings.write_html:
            # Inject CSS so the HTML looks like the PDF when opened in a browser (e.g. photo size)
            css_inline = settings.css_file.read_text(encoding="utf-8")
            html_with_css = html.replace("</head>", f"<style>\n{css_inline}\n</style>\n</head>")
            html_path.write_text(html_with_css, encoding="utf-8")

        # Write PDF: base_url = cv_dir so relative "photo.png" resolves; CSS is passed via stylesheets
        HTML(string=html, base_url=str(cv_dir.resolve())).write_pdf(
            str(pdf_path),
            stylesheets=[css],
        )

        ok += 1
        print(f"[OK] Rendered {cv_dir.name} -> {pdf_path.name} (template={tpl_name})")

    print(f"\n🎉 Done. PDFs rendered: {ok}/{len(cv_dirs)}")


if __name__ == "__main__":
    main()