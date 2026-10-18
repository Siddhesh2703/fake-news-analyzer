import html
import time
from urllib.parse import quote_plus

import streamlit as st

from detector import analyze, build_report, highlight_html
from fetcher import fetch_article
from samples import CREDIBLE_SAMPLE, SUSPICIOUS_SAMPLE

st.set_page_config(page_title="AI Fake News Analyzer", page_icon="📰", layout="wide")

CSS = """
<style>
.fn-hero{background:linear-gradient(135deg,#1f3c88,#5b2a86);color:#fff;padding:22px 26px;border-radius:14px;margin-bottom:16px}
.fn-hero h1{margin:0;padding:0;font-size:1.9rem;color:#fff}
.fn-hero p{margin:6px 0 0;opacity:.92}
.fn-card{background:rgba(128,128,128,.10);border-radius:14px;padding:18px 22px;margin-bottom:12px}
.fn-score{font-size:3.4rem;font-weight:800;line-height:1}
.fn-score span{font-size:1.2rem;font-weight:500;opacity:.7}
.fn-verdict{font-size:1.2rem;font-weight:700;margin:8px 0 10px}
.fn-bar{height:12px;border-radius:8px;background:rgba(128,128,128,.25);overflow:hidden}
.fn-bar div{height:100%;border-radius:8px}
.fn-article{background:rgba(128,128,128,.08);border-radius:12px;padding:16px 18px;line-height:1.75;max-height:440px;overflow-y:auto}
mark{color:inherit;padding:0 3px;border-radius:4px}
mark.fn-sensational,.fn-chip.fn-sensational{background:rgba(255,152,0,.40)}
mark.fn-absolute,.fn-chip.fn-absolute{background:rgba(255,235,59,.40)}
mark.fn-vague,.fn-chip.fn-vague{background:rgba(171,71,188,.35)}
mark.fn-conspiracy,.fn-chip.fn-conspiracy{background:rgba(244,67,54,.35)}
mark.fn-pressure,.fn-chip.fn-pressure{background:rgba(233,30,99,.35)}
mark.fn-caps,.fn-chip.fn-caps{background:rgba(33,150,243,.35)}
.fn-chip{display:inline-block;padding:2px 10px;border-radius:12px;margin:0 6px 6px 0;font-size:.85rem}
.fn-row{display:grid;grid-template-columns:1.3fr 1.5fr 44px;gap:10px;align-items:center;margin:7px 0;font-size:.92rem}
.fn-rowbar{height:10px;border-radius:6px;background:rgba(128,128,128,.2);overflow:hidden}
.fn-rowbar div{height:100%}
.fn-rowpts{text-align:right;font-weight:600}
</style>
"""

STRICTNESS = {"Lenient": 0.8, "Normal": 1.0, "Strict": 1.25}
VERDICT_TEXT = {
    "Few warning signs": "The writing style looks fairly neutral and well sourced. Still verify important claims.",
    "Some warning signs": "A few style or sourcing problems were found. Read carefully and double-check key claims.",
    "Many warning signs": "This text has many traits of misleading content. Verify it before trusting or sharing it.",
    "Strong warning signs": "This text strongly resembles misleading or manipulative content. Do not share it before verifying.",
}
LEGEND = [
    ("sensational", "Sensational wording"),
    ("absolute", "Absolute claims"),
    ("vague", "Vague sources"),
    ("conspiracy", "Conspiracy language"),
    ("pressure", "Pressure to share"),
    ("caps", "ALL CAPS"),
]

st.markdown(CSS, unsafe_allow_html=True)

for key, default in (("headline", ""), ("article", ""), ("url", ""), ("history", []), ("result_pack", None)):
    if key not in st.session_state:
        st.session_state[key] = default


# ---------------------------------------------------------------- callbacks
def load_sample(sample):
    st.session_state["headline"] = sample["headline"]
    st.session_state["article"] = sample["text"]
    st.session_state["result_pack"] = None
    st.session_state["load_msg"] = ("success", "Sample loaded below. Click Analyze article.")


def clear_all():
    st.session_state["headline"] = ""
    st.session_state["article"] = ""
    st.session_state["url"] = ""
    st.session_state["result_pack"] = None


def clear_history():
    st.session_state["history"] = []


def do_fetch():
    try:
        headline, text = fetch_article(st.session_state.get("url", ""))
        st.session_state["headline"] = headline
        st.session_state["article"] = text
        st.session_state["result_pack"] = None
        st.session_state["load_msg"] = ("success", "Article loaded below. Check it looks right, then click Analyze article.")
    except ValueError as err:
        st.session_state["load_msg"] = ("error", str(err))
    except Exception:
        st.session_state["load_msg"] = ("error", "Could not load that link. Please paste the text instead.")


def do_file():
    uploaded = st.session_state.get("txt_file")
    if uploaded is None:
        st.session_state["load_msg"] = ("error", "Please choose a .txt file first.")
        return
    try:
        text = uploaded.getvalue().decode("utf-8", errors="replace").strip()
    except Exception:
        st.session_state["load_msg"] = ("error", "Could not read that file.")
        return
    if not text:
        st.session_state["load_msg"] = ("error", "That file is empty.")
        return
    st.session_state["headline"] = ""
    st.session_state["article"] = text
    st.session_state["result_pack"] = None
    st.session_state["load_msg"] = ("success", "File loaded below. Click Analyze article.")


# ---------------------------------------------------------------- helpers
def score_color(score):
    if score < 25:
        return "#2e9e5b"
    if score < 50:
        return "#e0a800"
    if score < 75:
        return "#e8710a"
    return "#d93025"


def bars_html(items):
    if not items:
        return "<p>Nothing to show.</p>"
    top = max(abs(p) for _, p in items) or 1
    rows = []
    for title, pts in items:
        color = "#d93025" if pts > 0 else "#2e9e5b"
        width = str(int(abs(pts) / float(top) * 100))
        label = ("+" if pts > 0 else "") + str(pts)
        rows.append(
            '<div class="fn-row"><div>' + html.escape(title) + '</div><div class="fn-rowbar"><div style="width:'
            + width + "%;background:" + color + '"></div></div><div class="fn-rowpts">' + label + "</div></div>"
        )
    return "".join(rows)


def safe(text):
    return " ".join(str(text).replace("`", "'").split())


# ---------------------------------------------------------------- sidebar
with st.sidebar:
    st.header("⚙️ Settings")
    level = st.select_slider("Strictness", options=list(STRICTNESS.keys()), value="Normal")
    st.caption("Strict counts red flags more heavily. Lenient counts them less.")
    st.divider()
    st.subheader("🕘 This session")
    if st.session_state["history"]:
        for entry in st.session_state["history"][:8]:
            st.text(entry["time"] + "  " + str(entry["score"]) + "/100  " + entry["title"])
        st.button("Clear history", on_click=clear_history)
    else:
        st.caption("Your analyses will appear here. Nothing is saved after you close the page.")
    st.divider()
    st.caption(
        "How it works: simple rules look for sensational words, shouting, vague sources and conspiracy "
        "phrases, and credit named sources, quotes, figures and balance."
    )

# ---------------------------------------------------------------- header + input
st.markdown(
    '<div class="fn-hero"><h1>📰 AI Fake News Analyzer</h1>'
    "<p>Spot misleading writing patterns in news articles and social posts, then learn how to verify them.</p></div>",
    unsafe_allow_html=True,
)
st.info(
    "This tool checks writing style and sourcing using simple rules. It cannot confirm whether a claim is "
    "true or false, so always verify important news with fact-checking sites."
)

st.subheader("1. Add an article")
tab_samples, tab_link, tab_file = st.tabs(["🧪 Try a sample", "🔗 From a link", "📄 From a .txt file"])
with tab_samples:
    s1, s2, s3 = st.columns(3)
    s1.button("Load suspicious sample", on_click=load_sample, args=(SUSPICIOUS_SAMPLE,))
    s2.button("Load credible sample", on_click=load_sample, args=(CREDIBLE_SAMPLE,))
    s3.button("Clear everything", on_click=clear_all)
with tab_link:
    st.text_input("Article link", key="url", placeholder="https://example.com/news/article")
    st.button("Fetch article", on_click=do_fetch)
    st.caption("Some websites block automated access. If that happens, copy the text and paste it below.")
with tab_file:
    st.file_uploader("Choose a .txt file", type=["txt"], key="txt_file")
    st.button("Load file", on_click=do_file)

message = st.session_state.pop("load_msg", None)
if message:
    if message[0] == "success":
        st.success(message[1])
    else:
        st.error(message[1])

st.text_input("Headline (optional)", key="headline", placeholder="Paste the headline here...")
st.text_area("Article text", key="article", height=260, placeholder="Paste the full article or post text here...")

if st.button("🔍 Analyze article", type="primary"):
    article = st.session_state.get("article", "").strip()
    headline = st.session_state.get("headline", "").strip()
    st.session_state["result_pack"] = None
    if not article:
        st.error("Please paste the article text first.")
    else:
        try:
            with st.spinner("Analyzing..."):
                result = analyze(article, headline, STRICTNESS[level])
        except ValueError as err:
            st.error(str(err))
        except Exception:
            st.error("Something unexpected went wrong. Please try again with different text.")
        else:
            st.session_state["result_pack"] = {
                "result": result, "headline": headline, "article": article, "level": level,
            }
            title = headline or article
            st.session_state["history"].insert(
                0, {"time": time.strftime("%H:%M"), "score": result["score"], "title": safe(title)[:40]}
            )
            st.session_state["history"] = st.session_state["history"][:20]

# ---------------------------------------------------------------- results
pack = st.session_state.get("result_pack")
if pack:
    result = pack["result"]
    headline = pack["headline"]
    article = pack["article"]
    score = result["score"]
    color = score_color(score)

    st.divider()
    st.subheader("2. Results")
    t_over, t_text, t_detail, t_verify = st.tabs(["📊 Overview", "🖍️ Highlighted text", "🚩 Details", "🔎 Verify"])

    with t_over:
        left, right = st.columns([1, 1.4])
        with left:
            st.markdown(
                '<div class="fn-card" style="border-left:8px solid ' + color + '">'
                '<div class="fn-score" style="color:' + color + '">' + str(score) + "<span> / 100</span></div>"
                '<div class="fn-verdict">' + html.escape(result["verdict"]) + "</div>"
                '<div class="fn-bar"><div style="width:' + str(score) + "%;background:" + color + '"></div></div>'
                '<p style="margin-top:12px">' + html.escape(VERDICT_TEXT[result["verdict"]]) + "</p>"
                '<p style="opacity:.7;font-size:.85rem">Higher score = more warning signs. Strictness: '
                + html.escape(pack["level"]) + "</p></div>",
                unsafe_allow_html=True,
            )
        with right:
            st.markdown("**What moved the score**")
            items = [(f["title"], f["points"]) for f in result["red_flags"]]
            items += [(c["title"], -c["points"]) for c in result["credibility"]]
            st.markdown(bars_html(items), unsafe_allow_html=True)
            st.caption("Red = adds to the warning score, green = reduces it.")

        stats = result["stats"]
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Words", stats["words"])
        m2.metric("Reading time", str(stats["reading_minutes"]) + " min")
        m3.metric("Avg sentence length", str(stats["avg_sentence_words"]) + " words")
        m4.metric("ALL CAPS / ! marks", str(stats["caps_words"]) + " / " + str(stats["exclamations"]))

        st.download_button(
            "⬇️ Download report (.txt)",
            data=build_report(result, headline),
            file_name="fake_news_report.txt",
            mime="text/plain",
        )

    with t_text:
        chips = "".join('<span class="fn-chip fn-' + k + '">' + label + "</span>" for k, label in LEGEND)
        st.markdown(chips, unsafe_allow_html=True)
        if result["highlights"]:
            if headline:
                st.markdown(
                    '<div class="fn-article"><b>' + highlight_html(headline, result["highlights"]) + "</b></div>",
                    unsafe_allow_html=True,
                )
            st.markdown(
                '<div class="fn-article">' + highlight_html(article, result["highlights"]) + "</div>",
                unsafe_allow_html=True,
            )
        else:
            st.write("No suspicious phrases were found to highlight.")
            st.markdown('<div class="fn-article">' + highlight_html(article, []) + "</div>", unsafe_allow_html=True)

    with t_detail:
        c_red, c_ok = st.columns(2)
        with c_red:
            st.markdown("#### 🚩 Red flags")
            if result["red_flags"]:
                for flag in result["red_flags"]:
                    st.markdown("**" + flag["title"] + "** (+" + str(flag["points"]) + ")")
                    st.write(flag["explanation"])
                    if flag["examples"]:
                        st.write("Found: " + ", ".join("`" + safe(e) + "`" for e in flag["examples"]))
            else:
                st.write("No red flags were detected.")
        with c_ok:
            st.markdown("#### ✅ Credibility signals")
            if result["credibility"]:
                for sig in result["credibility"]:
                    st.markdown("**" + sig["title"] + "** (-" + str(sig["points"]) + ")")
                    st.write(safe(sig["detail"]))
            else:
                st.write("No credibility signals were detected.")

    with t_verify:
        st.markdown("#### Checklist")
        for item in result["checklist"]:
            st.write("- " + item)
        query = (headline or " ".join(article.split()[:12])) + " fact check"
        st.markdown("#### Quick links")
        st.markdown("- [Search this story with 'fact check'](https://www.google.com/search?q=" + quote_plus(query) + ")")
        st.markdown(
            "- [Google Fact Check Explorer](https://toolbox.google.com/factcheck/explorer)\n"
            "- [Snopes](https://www.snopes.com/) | [PolitiFact](https://www.politifact.com/) | "
            "[FactCheck.org](https://www.factcheck.org/)\n"
            "- [AFP Fact Check](https://factcheck.afp.com/) | [Reuters Fact Check](https://www.reuters.com/fact-check/)\n"
            "- [BOOM](https://www.boomlive.in/) | [Alt News](https://www.altnews.in/)"
        )

    st.caption("A low score does not prove an article is true, and a high score does not prove it is false.")
