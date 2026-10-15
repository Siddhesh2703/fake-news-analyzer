# AI Fake News Analyzer

Paste an article (and optionally its headline) and get a warning score, red flags, credibility signals
and a checklist for verifying the story. Pure Python + Streamlit, no paid APIs, no models, no downloads.

**Important:** it analyzes writing style and sourcing with simple rules. It cannot tell whether a claim is
actually true. A low score does not prove an article is true, and a high score does not prove it is false.

## Files
| File | Purpose |
|---|---|
| `app.py` | Streamlit app (the **main file**) |
| `detector.py` | All analysis rules and scoring |
| `requirements.txt` | Dependency (`streamlit` only) |
| `sample_suspicious_article.txt` / `sample_credible_article.txt` | Test articles (also loadable with buttons in the app) |

Your Job Match Analyzer project stays untouched in its own folder. Keep the two projects in separate
folders and separate GitHub repositories.

## Run locally in VS Code (Windows)
1. Install **Python 3.10 - 3.13** from https://www.python.org/downloads/ and tick **"Add python.exe to PATH"**.
2. Install **VS Code** and its **Python** extension.
3. Put the project files in a new folder, e.g. `C:\Users\YourName\fake-news-analyzer`, then **File > Open Folder** in VS Code.
4. Open **Terminal > New Terminal** and run:
   ```
   python -m venv .venv
   .venv\Scripts\Activate.ps1
   pip install -r requirements.txt
   streamlit run app.py
   ```
   If PowerShell blocks activation, run `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`, answer `Y`, and retry.
5. Your browser opens at http://localhost:8501. Click **Load suspicious sample**, then **Analyze article** (expect a score near 100). Try **Load credible sample** (expect near 0).

## Deploy for free (GitHub + Streamlit Community Cloud)
**A. GitHub**
1. Create a free account at https://github.com, then **+ > New repository**, name it `fake-news-analyzer`, choose **Public**, click **Create repository**.
2. Click **uploading an existing file**, drag in `app.py`, `detector.py`, `requirements.txt`, `README.md`, `.gitignore` and the two sample `.txt` files, then **Commit changes**. Files must be at the top level, and do not upload `.venv`.

**B. Streamlit Community Cloud**
1. Go to https://share.streamlit.io and click **Continue with GitHub**, then authorize.
2. Click **Create app**, choose your repository, branch `main`, and set **Main file path** to `app.py`.
3. Click **Deploy**. After a few minutes you get a public `*.streamlit.app` link. Later uploads to GitHub redeploy automatically.

## Why deployment is easy
Only one dependency, no secrets or API keys, no local file paths, and the samples are built into `app.py`.
Pasted text is analyzed in memory and never stored.

## What to work on next (easiest first, keeping deployment simple)
1. **Deploy this version first.** Confirm the public link works before changing anything.
2. **Tune the word lists** in `detector.py` (the lists at the top). This is the safest improvement: add phrases you see in real misleading posts, and test with the two samples after each change.
3. **Add a "paste a link" option** using `requests` and `beautifulsoup4` (both install fine on Streamlit Cloud). Many sites block scrapers, so keep paste-text as the fallback.
4. **Add free fact-check lookup** using the Google Fact Check Tools API (free key). On Streamlit Cloud, store the key in **App settings > Secrets** and read it with `st.secrets`. Never put the key in GitHub.
5. **Try a trained classifier last.** `scikit-learn` plus a public labeled dataset (for example ISOT or LIAR) can be added, but the dataset must be inside the repo and the saved model small, otherwise deployment gets harder. Evaluate its accuracy honestly, since such models often fail on new topics.

## Troubleshooting
- `python` not recognized: reinstall Python with "Add python.exe to PATH", reopen VS Code.
- `streamlit` not recognized: make sure `(.venv)` shows in the terminal; if not, rerun the activate command.
- Port busy: `streamlit run app.py --server.port 8502`.
