#!/bin/bash
cd "$(dirname "$0")"
exec > >(tee run_log.txt) 2>&1
echo "== Lesson Creation Tool setup $(date) =="
# 1) get a modern Python (3.12) via uv - macOS's built-in 3.9 is too old
export PATH="$HOME/.local/bin:$PATH"
if ! command -v uv >/dev/null; then
  echo "Installing uv (Python manager)..."; curl -LsSf https://astral.sh/uv/install.sh | sh
  export PATH="$HOME/.local/bin:$PATH"
fi
[ -d .venv312 ] || uv venv --python 3.12 .venv312
source .venv312/bin/activate
echo "python: $(python --version)"
uv pip install -q -r requirements.txt && echo "deps OK"
# 2) API key
[ -f .env ] || cp .env.example .env
if ! grep -q "^GEMINI_API_KEY=..*" .env; then
  echo "Paste your Gemini key and press Enter:"; read -r KEY
  sed -i '' "s|^GEMINI_API_KEY=.*|GEMINI_API_KEY=$KEY|" .env
fi
# 3) skip Streamlit's email prompt
mkdir -p ~/.streamlit; [ -f ~/.streamlit/credentials.toml ] || printf '[general]\nemail = ""\n' > ~/.streamlit/credentials.toml
# 4) tests + generate both sample lessons
python -m pytest -q 2>&1 | tail -2
python check_ai.py || { echo; echo 'AI check FAILED - copy the last 15 lines above and send them to Claude.'; exit 1; }
python -X faulthandler run_samples.py
echo "== DONE. Opening the app (close this window to stop) =="
streamlit run app.py --browser.gatherUsageStats false
