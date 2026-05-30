This guide shows exact commands to push your repo to GitHub and then deploy to a Hugging Face Space using the CLI.

1) Ensure you have Git and Python installed and a working venv.

2) Commit your changes locally and push to GitHub (your commands):

```bash
# From repo root
git remote add origin https://github.com/RaviSoni804426/Personal-Rag-Project.git
git branch -M main
git push -u origin main
```

3) Install and login to the Hugging Face CLI (interactive) or use a token:

```bash
pip install huggingface-hub
# Interactive login (opens prompt)
huggingface-cli login
# OR non-interactive
export HF_TOKEN=hf_xxx
huggingface-cli login --token $HF_TOKEN
```

4) Create a Space (via web UI or CLI). To create via CLI:

```bash
huggingface-cli repo create YOUR_USERNAME/YOUR_SPACE_NAME --type space --sdk docker
```

5) Add HF remote and push (replace YOUR_USERNAME/YOUR_SPACE_NAME):

```bash
git remote add hf https://huggingface.co/spaces/YOUR_USERNAME/YOUR_SPACE_NAME
git push hf main:main -u
```

6) In the Space settings (gear icon) → Secrets, add:
- `GROQ_API_KEY` (if using Groq)
- `OPENAI_API_KEY` (optional)

7) Watch build logs in the Space UI. The included `Dockerfile` runs the app with `uvicorn datamind.main:app`.

Troubleshooting:
- If build fails, view logs in HF Space UI; common issues include missing secrets or dependency mismatches.
- If the Docker build exceeds resource limits, try removing heavy dev packages from `requirements.txt` or use a smaller base image.

