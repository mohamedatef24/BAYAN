# Arabic Grammarly (project)

Project overview

This repository contains the initial skeleton for an Arabic grammar & writing assistant (like Grammarly) project. It includes placeholders for data, models, and source code, plus configuration and dependency files. Use this repo as the single source-of-truth for team contributions.

Key features you may implement here

- Arabic spelling and grammar checking
- Style / clarity suggestions for Modern Standard Arabic (MSA) and dialects
- Sentence rewriting and paraphrasing suggestions
- Plagiarism or similarity checks (optional)
- Integration with web UI / browser extension / API

Repository layout

- `data/` — place raw and processed datasets (LANS, corpora, etc.). See `data/README.md` for details.
- `models/` — store training checkpoints and exports (do NOT commit large binary files). See `models/README.md`.
- `src/` — source code (training scripts, inference API, preprocessing). See `src/README.md`.
- `requirements.txt` — Python dependencies for the project.
- `.env.example` — template for environment variables.
- `.gitignore` — sensible defaults for this project.

Contributing notes

- Keep large datasets and model weights out of Git (use cloud storage or Git LFS / DVC / Hugging Face Hub).
- Add tests in `src/tests/` and keep the public API stable.
- Use small, focused pull requests that include a short description and test(s) if applicable.

Contact

If you have questions about where to add files or how to name things, ask in the team chat and follow the README inside each folder for more guidance.