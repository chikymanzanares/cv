# Model Selection Rationale

This project requires generating structured synthetic CV data in JSON format, as well as realistic candidate profile images to be embedded into PDF resumes for downstream ingestion into a Retrieval-Augmented Generation (RAG) pipeline.

## Task Requirements

The selected models must:

- Follow structured instructions reliably
- Generate valid JSON outputs
- Support multilingual content
- Operate within free-tier constraints
- Allow local reproducibility by reviewers without billing setup

---

## Selected Provider

The default provider selected for data generation is **Google AI Studio (Gemini)**.

Model selection is configurable via environment variables in order to support experimentation and provider fallback without modifying application code.

---

## Text Generation Model

```
models/gemini-2.0-flash
```

### Rationale

This model was selected due to:

- Reliable adherence to structured prompts
- Improved JSON output stability compared to open-source alternatives
- Instruction tuning suitable for synthetic document generation
- Free-tier availability via Google AI Studio
- Low latency enabling generation of ~30 CVs in reasonable time

---

## Image Generation Model

```
models/gemini-2.5-flash-image
```

### Rationale

This model enables generation of realistic headshots for synthetic CVs without requiring additional billing setup, allowing the full PDF rendering pipeline to operate using AI-generated visual content.

---

## Fallback Provider

In case the default provider is unavailable, the pipeline supports OpenRouter as an alternative LLM backend.

Fallback text model:

```
mistralai/mistral-small-3.1-24b-instruct:free
```

Selected for:

- Instruction tuning
- Adequate parameter size (24B) for structured generation tasks
- Free-tier availability via OpenRouter

Image generation via OpenRouter may require billing activation and is therefore not enabled by default.

---

## Reproducibility

All generation parameters (provider, model name, timestamp, configuration) are embedded in each generated `cv.json` file under the `meta` field to support traceability and reproducibility.
