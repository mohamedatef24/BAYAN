# src/ — source code

Purpose

All core project code should live in `src/`: data loaders, preprocessing, training scripts, model definitions, and inference API.

Suggested layout

- `src/app.py` — lightweight Flask/FastAPI app for inference and testing
- `src/train.py` — training orchestration (argument parsing, checkpointing)
- `src/evaluate.py` — evaluation scripts and metrics
- `src/data_loader.py` — dataset loaders and helpers
- `src/preprocessing.py` — normalization, tokenization, and text cleaning
- `src/models/` — model classes or adapters
- `src/utils/` — utility functions (logging, metrics, etc.)
- `src/tests/` — unit and integration tests for core modules

File responsibilities and guidelines

- Keep functions small and well-documented.
- Expose a stable API for inference (e.g., `predict(text: str) -> dict`). Document the input/output shapes.
- Add type hints where practical.

Coding conventions

- Use the project style (PEP8). Add a linter config if needed (e.g., `pyproject.toml` or `.flake8`).
- Write tests for data loaders and small utilities. Place tests under `src/tests/` and use pytest.

What to add when working in `src/`

- Small, focused commits that update a single feature or test.
- If adding a new script, update top-level `README.md` with a one-line summary and usage example.
- If you modify input/output shapes for the inference API, update the API docs and communicate in the PR description.

Quick example: inference contract

- Input: Arabic text string (utf-8)
- Output: JSON object with fields such as `text`, `suggestions` (list), `confidence` (0-1), and optional `edits` with positions

Example output shape

```
{
  "text": "...",
  "suggestions": [
    {"start": 5, "end": 12, "replacement": "...", "explanation": "grammar: agreement"}
  ],
  "confidence": 0.87
}
```

Testing

- Add unit tests for `preprocessing.py` and `data_loader.py` (happy path + one edge case).
- Add a small integration test for `app.py` that exercises the prediction endpoint with a short sample input.