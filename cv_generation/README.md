# CV Generation Pipeline

Offline pipeline to generate a synthetic dataset of realistic-looking CVs (résumés) in PDF format for the AI-Powered CV Screener (RAG workflow).

Goals:
- Keep the production API free of heavy LLM/image dependencies
- Enable reproducible dataset generation and experimentation
- Allow regenerating PDFs without re-calling the LLM

---

## Folder structure

```
cv_generation/
├── Makefile                 # gen-data, gen-pdf, gen-all, etc.
├── generate_data.py         # LLM-based CV JSON generation (Anthropic/Gemini/OpenRouter)
├── render_pdfs.py           # JSON → HTML (Jinja2) → PDF (WeasyPrint)
├── settings.py              # Env and provider settings
├── prompts/
│   ├── cv_json_v1.txt       # Legacy prompt
│   └── cv_json_v2.txt       # Current prompt (structure, variability)
├── templates/               # Jinja2 HTML templates
│   ├── cv_modern.html.j2
│   ├── cv_classic.html.j2
│   ├── cv_minimal.html.j2
│   ├── cv_sidebar.html.j2
│   ├── cv_compact.html.j2
│   ├── cv_accent.html.j2
│   ├── cv_warm.html.j2
│   ├── cv_green.html.j2
│   ├── cv_narrative.html.j2
│   └── base.html.j2
├── static/
│   └── cv.css               # Shared styles
├── services/                # LLM / image API clients
│   ├── anthropic_client.py
│   ├── google_gemini.py
│   └── openrouter_client.py
└── data/                    # Generated output (gitignored)
    └── cvs/
        ├── cv_001/
        │   ├── cv.json      # Structured CV data
        │   ├── cv.html      # Rendered HTML
        │   ├── cv.pdf       # Rendered PDF
        │   └── photo.png    # Headshot (generated or from assets)
        ├── cv_002/
        └── ...
```

---

## Quick commands

```bash
make -C cv_generation gen-all    # gen-data + gen-pdf
make -C cv_generation gen-data   # Generate JSON only (N=30 by default)
make -C cv_generation gen-pdf    # Render HTML + PDF from existing JSON
FORCE_PDF=1 make -C cv_generation gen-pdf   # Overwrite existing PDFs
```

Model selection and variability (writing styles, section labels, page length, etc.) are documented in [docs/adr/001-model-selection.md](../docs/adr/001-model-selection.md).
