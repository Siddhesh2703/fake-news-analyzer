# AI Fake News Analyzer (v2)

Paste an article, load it from a link, or upload a .txt file. You get a warning score, a breakdown of what
moved the score, the article with suspicious phrases highlighted, a downloadable report, and a checklist
with fact-checking links. Pure Python + Streamlit: no paid APIs, no models, no extra dependencies.

**Important:** it analyzes writing style and sourcing with simple rules. It cannot tell whether a claim is
actually true. A low score does not prove an article is true, and a high score does not prove it is false.

## What's new in v2
- Modern layout: header banner, tabs, colored score card, bar breakdown of what raised or lowered the score
- Highlighted article text with a color legend
- Load from a link (standard library only, blocks private/local addresses, friendly errors)
- Upload a .txt file, built-in suspicious and credible samples, Clear button
- Strictness setting (Lenient / Normal / Strict), reading stats, session history
- Download the report as a .txt file, plus quick fact-check search links

## Files (all go in the top level of the folder and repository)
| File | Purpose |
|---|---|
| `app.py` | Streamlit app (the **main file**) |
| `detector.py` | Analysis rules, scoring, highlighting, report |
| `fetcher.py` | Loads an article from a link |
| `samples.py` | Built-in sample articles |
| `requirements.txt` | Dependency list (`streamlit` only) |
| `sample_suspicious_article.txt`, `sample_credible_article.txt` | Test files for the .txt upload tab |

## Run locally in VS Code (Windows)
1. Install **Python 3.10 - 3.13** from https://www.python.org/downloads/ and tick **"Add python.exe to PATH"**.
2. Install **VS Code** and its **Python** extension.
3. Put all project files in one folder (e.g. `C:\Users\YourName\fake-news-analyzer`) and use **File > Open Folder**.
4. In **Terminal > New Terminal** run:
   ```
   python -m venv .venv
   .venv\Scripts\Activate.ps1
   pip install -r requirements.txt
   streamlit run app.py
   ```
   If PowerShell blocks activation: `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`, answer `Y`, retry.
5. Open http://localhost:8501. Try **Load suspicious sample** then **Analyze article** (score near 100),
   then **Load credible sample** (score near 0). Try the **From a .txt file** tab with the sample files.

## Deployment: does it change?
No. It is still one dependency and one main file.
- **Main file path stays `app.py`.** The new files (`detector.py`, `fetcher.py`, `samples.py`) just sit beside it.
- **`requirements.txt` stays `streamlit`.** Link loading uses Python's built-in `urllib` and `html.parser`.
- **Updating an already-deployed app:** upload/replace the files in the same GitHub repository. Streamlit Community Cloud redeploys automatically within a minute or two (use the app's menu > Reboot app if needed).
- **Link loading on the cloud:** works, because Streamlit Cloud can reach the internet, but some news sites block automated requests. The app shows a clear message and you can paste the text instead.
- Nothing is stored: pasted text, uploads, and history exist only in the browser session.

## First-time deployment (GitHub + Streamlit Community Cloud)
**A. GitHub**
1. Create a free account at https://github.com, then **+ > New repository**, name it `fake-news-analyzer`, choose **Public**, **Create repository**.
2. Click **uploading an existing file**, drag in `app.py`, `detector.py`, `fetcher.py`, `samples.py`, `requirements.txt`, `README.md`, `.gitignore` and the two sample `.txt` files, then **Commit changes**. Do not upload `.venv`.

**B. Streamlit Community Cloud**
1. Go to https://share.streamlit.io, click **Continue with GitHub**, authorize.
2. Click **Create app**, choose your repository, branch `main`, **Main file path** `app.py`.
3. Click **Deploy**. In a few minutes you get a public `*.streamlit.app` link.

## What to work on next (easiest first)
1. Deploy v2 and test on your phone using the public link.
2. Tune the word lists at the top of `detector.py` with phrases you see in real misleading posts.
3. Add a free Google Fact Check Tools API lookup. Store the key in the app's **Secrets** setting and read it with `st.secrets`. Never commit keys to GitHub.
4. Add language support (Hindi, Marathi, etc.) by adding word lists for each language.
5. Only last: a trained classifier (`scikit-learn` + a labeled dataset). It needs the dataset and a small saved model in the repo, and such models often fail on new topics.

## Troubleshooting
- `python` not recognized: reinstall Python with "Add python.exe to PATH", reopen VS Code.
- `streamlit` not recognized: make sure `(.venv)` shows in the terminal; if not, rerun the activate command.
- Port busy: `streamlit run app.py --server.port 8502`.
- After deploying, if the app shows an import error, check that all `.py` files are in the repo's top level.
