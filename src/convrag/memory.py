import re

PASSAGES = [("budget.md", 'The error budget is 43 minutes.'), ("rollback.md", 'Rollback is allowed when the error rate doubles.')]
SESSIONS = {}
STOP = {"the", "a", "an", "is", "of", "to", "it", "that"}


def words(text):
    return set(re.findall(r"[a-z0-9]+", text.lower())) - STOP


def ask(session_id, question):
    if not session_id or not isinstance(session_id, str):
        raise ValueError("session_id is required")
    history = SESSIONS.setdefault(session_id, [])
    combined = " ".join(history[-4:] + [question])
    query = words(combined)
    ranked = sorted(
        ({"source": name, "text": text, "overlap": len(query & words(text))} for name, text in PASSAGES),
        key=lambda row: -row["overlap"],
    )
    best = ranked[0]
    history.append(question)
    answered = best["overlap"] >= 2
    return {
        "answered": answered,
        "answer": best["text"] if answered else "No passage shares enough terms.",
        "citation": best["source"] if answered else None,
        "turns": len(history),
        "passages": ranked,
    }
