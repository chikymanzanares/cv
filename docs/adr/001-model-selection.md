# Model Selection

This document describes the selected models used for synthetic CV generation within the dataset creation pipeline. The pipeline supports multiple providers configured via environment variables.

---

## Text Generation Models

### Primary (default): Anthropic

The default Large Language Model (LLM) used for generating structured CV content is:

```
claude-3-haiku-20240307
```

**Provider:** Anthropic

**Selection rationale:**

* Reliable adherence to structured prompts
* Consistent generation of valid JSON outputs
* Instruction-tuned behaviour suitable for document generation
* Multilingual content generation support
* Low latency for batch processing
* Cost-efficiency under constrained usage budgets

Given the requirement to generate 25–30 structured CV profiles for downstream Retrieval-Augmented Generation (RAG) tasks, this model provides an appropriate trade-off between generation quality, speed, and cost.

---

### Alternative: Google (AI Studio / Gemini API)


```
models/gemini-2.0-flash
```

**Provider:** Google (AI Studio / Gemini API)

**Selection rationale:**

* Fast and cost-effective model for structured generation
* Good instruction-following for JSON-like outputs
* Strong multilingual capability
* Useful as an alternative provider when configured

---

## Image Generation Models

### Primary (optional): OpenRouter

When synthetic headshot generation is enabled (`GENERATE_IMAGES=1`) and the image pipeline uses OpenRouter, the model used is:

```
black-forest-labs/flux.1-schnell
```

**Provider:** OpenRouter

**Selection rationale:**

* Availability via OpenRouter API
* Capability to generate realistic headshot-style imagery
* Compatibility with batch generation workflows
* Low-latency inference suitable for dataset creation

The generated images are intended solely for embedding within synthetic CV documents to simulate realistic candidate profile photos.

---

### Alternative: Google (Gemini API)

When image generation is configured to use Google:

```
models/gemini-2.5-flash-image
```

**Provider:** Google (Gemini API)

**Selection rationale:**

* Native Gemini image generation capability
* Suitable for generating realistic headshot-style imagery
* Useful as an alternative image provider when configured

(Environment variable: `GEMINI_IMAGE_MODEL`.)

---

## Embedding Model (RAG pipeline)

### Primary: `intfloat/multilingual-e5-small`

Used to vectorize CV text chunks and search queries for the FAISS semantic index.

**Model:** [intfloat/multilingual-e5-small](https://huggingface.co/intfloat/multilingual-e5-small) (Hugging Face)

```
intfloat/multilingual-e5-small
```

**Provider:** HuggingFace (downloaded once, cached locally in Docker volume `hf_cache`)

**Selection rationale:**

* Trained for **retrieval** (query → passage), not paraphrase similarity — suitable for RAG and CV search
* Fully local — no external API, no cost, no rate limits
* Multilingual support (100 languages from xlm-roberta), matching the multilingual CV dataset
* 384-dimensional dense vectors, max sequence length 512 tokens
* ~117 MB model size, suitable for CPU-only Docker containers
* Inputs use `query: ` and `passage: ` prefixes as per model card; the pipeline applies these automatically

**Runtime config** (`.env`):

```
EMBEDDING_MODEL=intfloat/multilingual-e5-small
```

**Index artefacts** (`rag_store/manifest.json` records the model used at index time):

```json
{
  "embedding_model": "intfloat/multilingual-e5-small",
  "dim": 384,
  "chunk_count": 169,
  "chunk_chars": 500,
  "overlap_chars": 50
}
```

---

## Provider selection mode: `random`

In addition to choosing a single provider, the pipeline supports:

```
LLM_PROVIDER=random
```

This is not a provider in itself: when set, the system selects **at random** one of the available LLM providers (e.g. Anthropic, Google) for each request or batch segment. It is intended for load distribution, cost sampling, or A/B-style comparison across providers without code changes.

---

## Configuration

Model selection is externally configurable through environment variables:

**LLM provider (text):**

```
LLM_PROVIDER=anthropic   # default: Anthropic Claude
LLM_PROVIDER=google      # Google Gemini
LLM_PROVIDER=openrouter  # OpenRouter (text model)
LLM_PROVIDER=random      # randomly pick one of the configured providers
```

**Per-provider models:**

```
# Anthropic (when LLM_PROVIDER=anthropic)
ANTHROPIC_TEXT_MODEL=claude-3-haiku-20240307

# Google (when LLM_PROVIDER=google or when selected by random)
GEMINI_TEXT_MODEL=models/gemini-2.0-flash
GEMINI_IMAGE_MODEL=models/gemini-2.5-flash-image

# OpenRouter (text when LLM_PROVIDER=openrouter; image when using OpenRouter for images)
OPENROUTER_TEXT_MODEL=...   # e.g. model id from openrouter.ai
OPENROUTER_IMAGE_MODEL=black-forest-labs/flux.1-schnell
```

This enables reproducible dataset generation without requiring modification of application code.
