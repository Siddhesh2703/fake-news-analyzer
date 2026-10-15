import streamlit as st

from detector import analyze

SUSPICIOUS_SAMPLE = {
    "headline": """SHOCKING!!! Doctors EXPOSED: This Miracle Fruit Cures ALL Diseases And Big Pharma Is HIDING It From You!""",
    "text": """You won't believe what they have been hiding from you for years! Experts say this one simple miracle fruit cures everything, from diabetes to cancer, and it works 100% of the time. Sources say the mainstream media has been silenced and is refusing to report the truth because the elites make billions from keeping you sick.

Everyone knows doctors never tell you the real secret. People are saying that thousands have already been healed overnight, and nobody is talking about it. This is the BIGGEST cover-up in history and the government does not want you to know!

WAKE UP before it is too late! Share this with everyone you love before it gets deleted!""",
}
CREDIBLE_SAMPLE = {
    "headline": """City council approves new bike lanes after months of public hearings""",
    "text": """The Rivertown City Council voted 7-2 on Tuesday to approve a plan that adds 12 miles of protected bike lanes by 2028, according to the council's official records. The project is expected to cost 4.2 million dollars, with about half of the funding coming from a state transportation grant.

"This plan reflects what residents told us during six public hearings," council member Maria Alvarez said. "Safety was the top concern."

However, some business owners have criticized the plan. Local shop owner David Chen told reporters that reduced parking could hurt sales. A spokesperson for the transportation department said the agency will review parking options before construction begins, and a traffic study published in the Journal of Urban Planning found that similar projects in other cities had mixed effects on nearby businesses.

Construction is scheduled to start in March, and the council will review progress in a public meeting next year.""",
}

st.set_page_config(page_title="AI Fake News Analyzer", page_icon="📰", layout="centered")

if "headline" not in st.session_state:
    st.session_state["headline"] = ""
if "article" not in st.session_state:
    st.session_state["article"] = ""


def load_sample(sample):
    st.session_state["headline"] = sample["headline"]
    st.session_state["article"] = sample["text"]


def clear_inputs():
    st.session_state["headline"] = ""
    st.session_state["article"] = ""


def safe(text):
    return " ".join(str(text).replace("`", "'").split())


st.title("📰 AI Fake News Analyzer")
st.info(
    "This tool checks writing style and sourcing signals using simple rules. "
    "It cannot confirm whether a claim is true or false, so always verify important news "
    "with trusted fact-checking sites."
)

st.text_input("Headline (optional)", key="headline", placeholder="Paste the article headline here...")
st.text_area("Article text", key="article", height=260, placeholder="Paste the full article or post text here...")

c1, c2, c3 = st.columns(3)
c1.button("Load suspicious sample", on_click=load_sample, args=(SUSPICIOUS_SAMPLE,))
c2.button("Load credible sample", on_click=load_sample, args=(CREDIBLE_SAMPLE,))
c3.button("Clear", on_click=clear_inputs)

if st.button("Analyze article", type="primary"):
    article = st.session_state.get("article", "").strip()
    headline = st.session_state.get("headline", "").strip()
    if not article:
        st.error("Please paste the article text first.")
    else:
        try:
            with st.spinner("Analyzing..."):
                result = analyze(article, headline)
        except ValueError as err:
            st.error(str(err))
        except Exception:
            st.error("Something unexpected went wrong. Please try again with different text.")
        else:
            st.divider()
            st.subheader("Result")
            col1, col2 = st.columns(2)
            col1.metric("Warning score (higher = riskier)", str(result["score"]) + " / 100")
            col2.metric("Verdict", result["verdict"])
            st.progress(result["score"] / 100)
            st.caption(
                "Based on " + str(result["details"]["words"]) + " words. "
                "Red-flag points: " + str(result["details"]["red_points"])
                + " | Credibility points subtracted: " + str(result["details"]["credibility_points"])
            )

            st.subheader("🚩 Red flags")
            if result["red_flags"]:
                for flag in result["red_flags"]:
                    st.markdown("**" + flag["title"] + "** (+" + str(flag["points"]) + ")")
                    st.write(flag["explanation"])
                    if flag["examples"]:
                        st.write("Found: " + ", ".join("`" + safe(e) + "`" for e in flag["examples"]))
            else:
                st.write("No red flags were detected.")

            st.subheader("✅ Credibility signals")
            if result["credibility"]:
                for sig in result["credibility"]:
                    st.markdown("**" + sig["title"] + "** (-" + str(sig["points"]) + ")")
                    st.write(safe(sig["detail"]))
            else:
                st.write("No credibility signals were detected.")

            st.subheader("🔎 How to verify it yourself")
            for item in result["checklist"]:
                st.write("- " + item)

            st.caption("A low score does not prove an article is true, and a high score does not prove it is false.")
