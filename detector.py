"""Core logic for the AI Fake News Analyzer.

This is a transparent, rule-based NLP checker. It looks for writing patterns that
are common in misleading articles (sensational wording, shouting, vague sources,
conspiracy talk) and for signs of credible reporting (named sources, quotes,
figures, balance). It CANNOT verify whether a claim is true.
"""

import html
import math
import re

MIN_WORDS = 30
MAX_CHARS = 30000

SENSATIONAL = [
    "shocking", "shocked", "unbelievable", "bombshell", "miracle", "exposed", "devastating",
    "outrage", "outrageous", "scandal", "explosive", "horrifying", "terrifying", "jaw-dropping",
    "mind-blowing", "insane", "disgusting", "banned", "censored", "urgent", "breaking",
    "secret", "secrets", "stunning", "unthinkable", "destroyed", "slammed", "gone wrong",
    "you won't believe", "you will not believe", "what happens next", "will shock you",
    "hoax", "cure-all", "cures all", "cures everything", "forbidden",
]

CLICKBAIT_HEADLINE = [
    "you won't believe", "you will not believe", "this one trick", "what happens next",
    "will shock you", "doctors hate", "one weird trick", "the truth about", "what they don't want you to know",
    "never seen before", "goes viral", "must see", "must watch",
]

ABSOLUTE = [
    "always", "never", "everyone", "nobody", "no one", "100%", "guaranteed", "proven",
    "undeniable", "all scientists", "all doctors", "completely", "totally", "absolutely",
    "without a doubt", "the only way", "every single", "impossible", "cures all",
]

VAGUE_SOURCING = [
    "experts say", "experts claim", "sources say", "sources claim", "people are saying",
    "some say", "many believe", "many people say", "it is rumored", "it is rumoured",
    "insiders say", "an insider", "a source close", "anonymous source", "they say",
    "scientists say", "studies show", "studies prove", "research proves", "everybody knows",
    "reportedly", "allegedly", "word is",
]

CONSPIRACY = [
    "mainstream media", "wake up", "sheeple", "deep state", "big pharma", "hidden agenda",
    "they are hiding", "they're hiding", "hiding the truth", "cover-up", "cover up",
    "don't want you to know", "do not want you to know", "new world order", "globalist",
    "crisis actor", "false flag", "silenced", "suppressed", "what they won't tell you",
    "they don't want", "the elites",
]

CALL_TO_ACTION = [
    "share this", "share before", "share now", "forward this", "spread the word",
    "send this to everyone", "before it gets deleted", "before it is deleted", "before they delete",
    "share with everyone", "tell everyone", "repost", "go viral",
]

TRUSTED_TERMS = [
    "reuters", "associated press", "bbc", "peer-reviewed", "peer reviewed", "journal",
    "world health organization", "centers for disease control", "nasa", "official statement",
    "court documents", "press release", "university", "data from", "census", "ministry",
    "department of", "published in", "press conference", "public hearing", "official records",
]

BALANCE = [
    "however", "critics", "on the other hand", "denied", "disputed", "declined to comment",
    "did not respond", "in response", "spokesperson", "opponents", "supporters", "but officials",
    "according to officials", "has not been confirmed", "unconfirmed",
]

OK_ACRONYMS = {
    "NASA", "NATO", "COVID", "UNICEF", "UNESCO", "FIFA", "OPEC", "ASEAN", "HIV", "AIDS", "OECD",
    "NBA", "NFL", "FBI", "CIA", "USA", "ISRO", "DRDO", "ICMR", "GDP", "CEO", "CNBC", "NDTV", "WHO",
    "CDC", "AFP", "BBC", "ISIS", "SARS", "NASDAQ", "IPCC", "UNHCR", "AIIMS", "RBI", "SEBI", "IPL",
}


def _find_terms(terms, lowered):
    """Return the distinct terms from the list that appear in the text."""
    found = []
    for term in terms:
        pattern = r"(?<![a-z0-9])" + re.escape(term) + r"(?![a-z0-9])"
        if re.search(pattern, lowered):
            found.append(term)
    return found


def _clean_snippet(text):
    return re.sub(r"\s+", " ", text.replace("`", "'")).strip()


def analyze(text, headline="", strictness=1.0):
    text = (text or "").strip()
    headline = (headline or "").strip()
    if len(text) > MAX_CHARS:
        raise ValueError("The text is too long. Please paste up to " + str(MAX_CHARS) + " characters.")
    words = re.findall(r"[A-Za-z0-9'\u2019-]+", text)
    if len(words) < MIN_WORDS:
        raise ValueError("Please paste more text (at least " + str(MIN_WORDS) + " words) so the analysis is meaningful.")

    full = (headline + "\n" + text).strip()
    lowered = full.lower().replace("\u2019", "'").replace("\u2018", "'")

    red_flags = []
    credibility = []
    red_points = 0
    cred_points = 0

    def add_flag(title, explanation, examples, points):
        nonlocal red_points
        red_points += points
        red_flags.append({"title": title, "explanation": explanation, "examples": examples, "points": points})

    def add_cred(title, detail, points):
        nonlocal cred_points
        cred_points += points
        credibility.append({"title": title, "detail": detail, "points": points})

    highlights = []

    def mark(terms, category):
        for t in terms:
            highlights.append((t, category))

    # ---------------- Red flags ----------------
    found = _find_terms(SENSATIONAL, lowered)
    mark(found, "sensational")
    if found:
        add_flag("Sensational or emotional wording",
                 "Reliable reporting usually uses neutral language. Hype words try to trigger emotion instead of informing.",
                 found[:8], min(25, 4 * len(found)))

    if headline:
        hl = headline.lower().replace("\u2019", "'")
        hl_found = _find_terms(CLICKBAIT_HEADLINE, hl)
        mark(hl_found, "sensational")
        hl_notes = list(hl_found)
        if re.match(r"^\s*\d+\s+(things|reasons|ways|secrets|facts|signs|tricks)\b", hl):
            hl_notes.append("numbered list headline")
        if "!!" in headline or (headline.count("!") >= 1 and headline.isupper()):
            hl_notes.append("exclamation marks in headline")
        letters = [c for c in headline if c.isalpha()]
        if len(letters) >= 10 and sum(1 for c in letters if c.isupper()) / len(letters) > 0.6:
            hl_notes.append("headline mostly in capital letters")
        if hl_notes:
            add_flag("Clickbait-style headline",
                     "Headlines written to provoke clicks often exaggerate what the article actually shows.",
                     hl_notes[:6], min(12, 5 * len(hl_notes)))

    caps = [w for w in re.findall(r"\b[A-Z]{4,}\b", full) if w not in OK_ACRONYMS]
    caps_distinct = sorted(set(caps))
    if len(caps) >= 3:
        mark(caps_distinct, "caps")
        add_flag("Words written in ALL CAPS",
                 "Shouting in capital letters is a common tactic to create urgency or outrage.",
                 caps_distinct[:8], min(15, 2 * len(caps)))

    exclaims = full.count("!")
    if exclaims >= 2:
        add_flag("Many exclamation marks",
                 "News reports rarely use repeated exclamation marks.",
                 [str(exclaims) + " exclamation marks"], min(10, 2 * exclaims))

    found = _find_terms(ABSOLUTE, lowered)
    mark(found, "absolute")
    if found:
        add_flag("Absolute or exaggerated claims",
                 "Words like 'always', 'never' and '100%' overstate certainty. Real evidence is usually more nuanced.",
                 found[:8], min(12, 3 * len(found)))

    found = _find_terms(VAGUE_SOURCING, lowered)
    mark(found, "vague")
    if found:
        add_flag("Vague or unnamed sources",
                 "Claims attributed to unnamed 'experts' or 'sources' cannot be checked.",
                 found[:8], min(18, 6 * len(found)))

    found = _find_terms(CONSPIRACY, lowered)
    mark(found, "conspiracy")
    if found:
        add_flag("Conspiracy-style language",
                 "Phrases claiming that someone is hiding or suppressing the truth are typical of misleading content.",
                 found[:8], min(18, 6 * len(found)))

    found = _find_terms(CALL_TO_ACTION, lowered)
    mark(found, "pressure")
    if found:
        add_flag("Pressure to share",
                 "Urging readers to share immediately helps misinformation spread before it can be checked.",
                 found[:6], min(12, 6 * len(found)))

    # ---------------- Credibility signals ----------------
    attrib_patterns = [
        r"(?:according to|reported by|reports from|statement from|spokesperson for|researchers at|professor at|study by|published in)\s+(?:the\s+)?[A-Z][\w.&'-]+",
        r"\b[A-Z][a-z]+(?:\s[A-Z][a-z]+)?\s(?:said|told|stated|added|confirmed|announced|explained|noted)\b",
    ]
    named = []
    for pat in attrib_patterns:
        for m in re.finditer(pat, text):
            snippet = _clean_snippet(m.group(0))
            if snippet not in named:
                named.append(snippet)
    if named:
        add_cred("Named sources or attribution",
                 "Statements are tied to identifiable people or organizations: " + "; ".join(named[:4]),
                 min(16, 4 * len(named)))

    quotes = re.findall(r"[\"\u201c][^\"\u201d]{20,}[\"\u201d]", text)
    if quotes:
        add_cred("Direct quotes", str(len(quotes)) + " direct quotation(s) found.", min(9, 3 * len(quotes)))

    numbers = re.findall(r"\b\d[\d,.]*\b", text)
    if len(numbers) >= 2:
        add_cred("Specific figures or dates", str(len(numbers)) + " numbers or dates mentioned.", min(8, len(numbers)))

    links = re.findall(r"https?://\S+|www\.\S+", text)
    if links:
        add_cred("Links or references", str(len(links)) + " link(s) to check.", min(6, 3 * len(links)))

    found = _find_terms(TRUSTED_TERMS, lowered)
    if found:
        add_cred("Reference to institutions or records", "Mentions: " + ", ".join(found[:6]) + ".", min(12, 4 * len(found)))

    found = _find_terms(BALANCE, lowered)
    if found:
        add_cred("Balance and response", "Includes signs of multiple viewpoints or requests for comment: " + ", ".join(found[:6]) + ".",
                 min(9, 3 * len(found)))

    if not credibility:
        add_flag("No verifiable sourcing found",
                 "The text does not name any people, institutions, quotes, links or figures that you could check.",
                 [], 15)

    score = max(0, min(100, int(round(red_points * strictness - cred_points))))
    if score < 25:
        verdict = "Few warning signs"
    elif score < 50:
        verdict = "Some warning signs"
    elif score < 75:
        verdict = "Many warning signs"
    else:
        verdict = "Strong warning signs"

    # ---------------- Verification checklist ----------------
    checklist = [
        "Search the main claim together with the words 'fact check' on Snopes, PolitiFact, FactCheck.org, or AFP Fact Check.",
        "Look for the same story in at least two independent, well-known news outlets.",
        "Check who published it: read the site's About page, the author name, and the publication date.",
        "Read the whole article, not just the headline, and look for the original study, document, or statement.",
    ]
    titles = [f["title"] for f in red_flags]
    if "Vague or unnamed sources" in titles or "No verifiable sourcing found" in titles:
        checklist.append("Find the original source behind phrases like 'experts say'. If you cannot find one, treat the claim as unverified.")
    if "Pressure to share" in titles:
        checklist.append("Do not share it until you have verified it, even if it says it will be deleted.")
    checklist.append("If there is a photo or video, run a reverse image search (Google Lens or TinEye) to see if it is old or from another event.")

    sentences = max(1, len(re.findall(r"[.!?]+(?:\s|$)", text)))
    stats = {
        "words": len(words),
        "sentences": sentences,
        "avg_sentence_words": round(len(words) / float(sentences), 1),
        "reading_minutes": max(1, int(math.ceil(len(words) / 200.0))),
        "caps_words": len(caps),
        "exclamations": exclaims,
    }

    return {
        "highlights": highlights,
        "stats": stats,
        "score": score,
        "verdict": verdict,
        "red_flags": red_flags,
        "credibility": credibility,
        "checklist": checklist,
        "details": {
            "words": len(words),
            "red_points": red_points,
            "credibility_points": cred_points,
        },
    }


def highlight_html(text, highlights):
    """Return HTML-safe text with flagged phrases wrapped in <mark> tags."""
    safe = html.escape(text or "", quote=False)
    cat_of = {}
    for term, cat in highlights:
        cat_of.setdefault(term.lower(), cat)
    if cat_of:
        terms = sorted(cat_of, key=len, reverse=True)
        pattern = re.compile(
            r"(?<![A-Za-z0-9])(" + "|".join(re.escape(t) for t in terms) + r")(?![A-Za-z0-9])", re.IGNORECASE
        )

        def repl(match):
            cat = cat_of.get(match.group(1).lower(), "caps")
            return '<mark class="fn-' + cat + '">' + match.group(1) + "</mark>"

        safe = pattern.sub(repl, safe)
    return safe.replace("\n", "<br>")


def build_report(result, headline=""):
    """Plain-text report for download."""
    lines = ["AI FAKE NEWS ANALYZER - REPORT", "=" * 32, ""]
    if headline:
        lines.append("Headline: " + headline)
    lines.append("Warning score: " + str(result["score"]) + "/100 (" + result["verdict"] + ")")
    lines.append("Note: this checks writing style and sourcing only. It cannot confirm that a claim is true or false.")
    lines += ["", "RED FLAGS"]
    if result["red_flags"]:
        for f in result["red_flags"]:
            line = "- " + f["title"] + " (+" + str(f["points"]) + "): " + f["explanation"]
            if f["examples"]:
                line += " Found: " + ", ".join(f["examples"])
            lines.append(line)
    else:
        lines.append("- None detected")
    lines += ["", "CREDIBILITY SIGNALS"]
    if result["credibility"]:
        for c in result["credibility"]:
            lines.append("- " + c["title"] + " (-" + str(c["points"]) + "): " + c["detail"])
    else:
        lines.append("- None detected")
    lines += ["", "HOW TO VERIFY"]
    for item in result["checklist"]:
        lines.append("- " + item)
    return "\n".join(lines) + "\n"
