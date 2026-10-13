#!/usr/bin/env python3
"""Ask a separate expert model session a physics or method question. It holds the mx3-physics library in its context.

    consult.py ask "question" [--attach FILE]... [--session NAME] [--new]
    consult.py history [--session NAME]          the questions and answers so far
    consult.py check                              is a model reachable, and how large is the library

The session is a conversation: later questions can refer to earlier answers. It is kept in
.mx3-consult/<session>.json under the current directory; every exchange is also appended to .mx3-consult/log.md.
--new starts the session over. Attachments are sent as text (each cut to --attach-limit characters): notes, a
residual table, a script, a short CSV. Never attach whole simulation outputs.

Connection (environment): MX3_CONSULT_BASE_URL, else ANTHROPIC_BASE_URL, else https://api.anthropic.com;
MX3_CONSULT_MODEL, else ANTHROPIC_MODEL; key from MX3_CONSULT_API_KEY, ANTHROPIC_AUTH_TOKEN or ANTHROPIC_API_KEY.
MX3_CONSULT_THINKING=N gives the consultant up to N tokens of reasoning before it answers (default 6000; 0 = off;
dropped automatically if the endpoint does not support it).
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve()
PLUGIN = HERE.parents[3]
LIBRARY = PLUGIN / "skills" / "mx3-physics" / "references"
EXTRA = [PLUGIN / "skills" / "mx3-authoring" / "references" / "pitfalls.md"]
STORE = Path(".mx3-consult")
HISTORY_CHARS = 120_000          # older exchanges beyond this are dropped from what is sent (kept in the log)

ROLE = """You are the consultant: a senior micromagnetics researcher and numerical-methods expert. A colleague (a \
session running mumax3 simulations) sends you questions. You cannot run anything; you think, check and advise. The reference library below is yours to use; the colleague can read it too, so \
cite chapter names when you rely on it.

How to answer:
- Answer the question asked, first, in a few lines. Then the reasoning.
- Formulas in SI with units; name the mumax3 parameter for each symbol; say for which regime a formula holds and how \
far a real geometry may deviate from it.
- When the question gives numbers, do the arithmetic explicitly, check the units at every step, and re-check every \
power of ten before you answer.
- Look for the usual errors in what you are shown:
  units (mT versus T, Oe versus A/m, emu/cm3 versus A/m, D in mJ/m2 entered as J/m2), wrong prefactors (2 pi, mu0, \
the sqrt(2) in exchange-length conventions), sign conventions (D, Q, J, field directions);
  numerics (a cell coarser than l_ex or the wall width, too few cells across a texture, finite-size or periodic-image \
effects, a demag setting that double-counts shape anisotropy, aliasing or a record too short for the spectral \
resolution, a transient inside an averaging window, thermal results from one seed);
  physics (a closed form used outside its regime, an unsaturated state in a Kittel fit, Brown's paradox when comparing \
coercivities, a regime change such as an instability, breakdown or switching between data points);
  fitting (a parameter outside its plausible range, an observable that does not depend on the parameter it is used \
for, an under-determined or strongly correlated fit, chi2 far from its expected value).
- When something can only be settled by a simulation, say exactly which run or comparison would settle it and what \
each outcome would mean.
- Typical material values are ranges for orientation and for starting values, never a substitute for the colleague's \
own measurements or fits.
- If you are not sure, say so and say what would decide it. Never invent references or numbers.
- Keep the answer under about 700 words unless asked for more."""


def library_text():
    parts = []
    for f in sorted(LIBRARY.glob("*.md")) + [e for e in EXTRA if e.is_file()]:
        parts.append(f"<chapter file=\"{f.relative_to(PLUGIN).as_posix()}\">\n{f.read_text(encoding='utf-8')}\n</chapter>")
    return "\n\n".join(parts)


def connection():
    base = (os.environ.get("MX3_CONSULT_BASE_URL") or os.environ.get("ANTHROPIC_BASE_URL")
            or "https://api.anthropic.com").rstrip("/")
    model = os.environ.get("MX3_CONSULT_MODEL") or os.environ.get("ANTHROPIC_MODEL")
    headers = {"content-type": "application/json", "anthropic-version": "2023-06-01"}
    key = os.environ.get("MX3_CONSULT_API_KEY") or os.environ.get("ANTHROPIC_AUTH_TOKEN")
    if key:
        headers["authorization"] = f"Bearer {key}"
    elif os.environ.get("ANTHROPIC_API_KEY"):
        headers["x-api-key"] = os.environ["ANTHROPIC_API_KEY"]
    return base, model, headers


def call(messages, system, max_tokens, thinking):
    base, model, headers = connection()
    if not model:
        sys.exit("no model: set MX3_CONSULT_MODEL (or ANTHROPIC_MODEL)")
    body = {"model": model, "max_tokens": max_tokens, "system": system, "messages": messages}
    if thinking > 0:
        body["thinking"] = {"type": "enabled", "budget_tokens": thinking}
        body["max_tokens"] = max_tokens + thinking
    req = urllib.request.Request(f"{base}/v1/messages", data=json.dumps(body).encode("utf-8"), headers=headers,
                                 method="POST")
    t0 = time.time()
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=900) as r:
                data = json.loads(r.read().decode("utf-8"))
            break
        except urllib.error.HTTPError as e:
            detail = e.read().decode("utf-8", "replace")[:400]
            if e.code == 400 and "thinking" in body and "thinking" in detail.lower():
                del body["thinking"]                     # this endpoint has no reasoning mode: ask without it
                body["max_tokens"] = max_tokens
                req = urllib.request.Request(req.full_url, data=json.dumps(body).encode("utf-8"), headers=headers,
                                             method="POST")
                continue
            if e.code in (429, 500, 502, 503, 529) and attempt < 2:
                time.sleep(20 * (attempt + 1))
                continue
            sys.exit(f"consultant unavailable: HTTP {e.code}: {detail}")
        except (urllib.error.URLError, TimeoutError, OSError) as e:
            if attempt < 2:
                time.sleep(20 * (attempt + 1))
                continue
            sys.exit(f"consultant unavailable: {e}")
    text = "\n".join(b.get("text", "") for b in data.get("content", []) if b.get("type") == "text").strip()
    usage = data.get("usage", {})
    return text, data.get("stop_reason"), usage, time.time() - t0, model


def session_file(name):
    return STORE / f"{name}.json"


def load_session(name):
    f = session_file(name)
    return json.loads(f.read_text(encoding="utf-8")) if f.exists() else {"created": time.strftime("%Y-%m-%dT%H:%M:%S"),
                                                                         "messages": []}


def trimmed(messages):
    """The most recent exchanges that fit in HISTORY_CHARS (always whole user/assistant pairs)."""
    out, size = [], 0
    for i in range(len(messages) - 1, -1, -2):
        pair = messages[max(i - 1, 0):i + 1]
        n = sum(len(m["content"]) for m in pair)
        if out and size + n > HISTORY_CHARS:
            break
        out = pair + out
        size += n
    return out


def cmd_ask(a):
    question = a.question.strip()
    if not question:
        sys.exit("empty question")
    parts = [question]
    for f in a.attach or []:
        p = Path(f)
        if not p.is_file():
            sys.exit(f"attachment {f} not found")
        t = p.read_text(encoding="utf-8", errors="replace")
        if len(t) > a.attach_limit:
            t = t[:a.attach_limit] + f"\n[... cut at {a.attach_limit} of {len(t)} characters]"
        parts.append(f"<attachment name=\"{p.as_posix()}\">\n{t}\n</attachment>")
    user = "\n\n".join(parts)
    STORE.mkdir(exist_ok=True)
    s = {"created": time.strftime("%Y-%m-%dT%H:%M:%S"), "messages": []} if a.new else load_session(a.session)
    msgs = trimmed(s["messages"]) + [{"role": "user", "content": user}]
    system = ROLE + "\n\n# Reference library\n\n" + library_text()
    thinking = int(os.environ.get("MX3_CONSULT_THINKING", "6000") or 0)
    text, stop, usage, secs, model = call(msgs, system, a.max_tokens, thinking)
    if not text and stop == "max_tokens":       # the reasoning used up the budget: once more with more room
        text, stop, usage, secs2, model = call(msgs, system, a.max_tokens * 2, thinking)
        secs += secs2
    if not text:
        sys.exit(f"the consultant returned no text (stop_reason {stop}); ask again, perhaps more narrowly")
    s["messages"] += [{"role": "user", "content": user}, {"role": "assistant", "content": text}]
    session_file(a.session).write_text(json.dumps(s, indent=1, ensure_ascii=False), encoding="utf-8")
    n = len(s["messages"]) // 2
    with open(STORE / "log.md", "a", encoding="utf-8") as f:
        f.write(f"\n## {a.session} #{n}, {time.strftime('%Y-%m-%d %H:%M:%S')} ({model}, {secs:.0f} s, "
                f"in {usage.get('input_tokens', '?')} / out {usage.get('output_tokens', '?')} tokens)\n\n"
                f"**Q:** {question}\n\n" + "".join(f"(attached: {x})\n\n" for x in (a.attach or [])) +
                f"**A:**\n\n{text}\n")
    print(text)
    if stop == "max_tokens":
        print("\n[the answer was cut at --max-tokens; ask for the rest, or ask more narrowly]")
    print(f"\n[consult {a.session} #{n}: {secs:.0f} s; logged in {STORE.as_posix()}/log.md]")


def cmd_history(a):
    s = load_session(a.session)
    if not s["messages"]:
        print(f"no questions yet in session {a.session}")
    for i in range(0, len(s["messages"]), 2):
        q = s["messages"][i]["content"].split("\n<attachment", 1)[0]
        ans = s["messages"][i + 1]["content"] if i + 1 < len(s["messages"]) else ""
        print(f"#{i // 2 + 1} Q: {q[:300]}\n   A: {ans[:300].replace(chr(10), ' ')}...\n")


def cmd_check(a):
    lib = library_text()
    base, model, headers = connection()
    print(f"library: {len(list(LIBRARY.glob('*.md')))} chapters, {len(lib):,} characters (~{len(lib) // 4:,} tokens)")
    print(f"endpoint: {base}/v1/messages, model: {model or '(none: set MX3_CONSULT_MODEL)'}, "
          f"key: {'yes' if 'authorization' in headers or 'x-api-key' in headers else 'no'}")
    text, stop, usage, secs, _ = call([{"role": "user", "content": "Reply with the single word: ready"}],
                                      "You are a test endpoint.", 50, 0)
    print(f"reply: {text!r} ({secs:.1f} s, stop {stop})")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    q = sub.add_parser("ask", help="ask a question")
    q.add_argument("question")
    q.add_argument("--attach", action="append", help="a text file to show the consultant (repeatable)")
    q.add_argument("--session", default="main", help="conversation name (default main)")
    q.add_argument("--new", action="store_true", help="start this session over")
    q.add_argument("--max-tokens", type=int, default=4000)
    q.add_argument("--attach-limit", type=int, default=20000, help="characters per attachment (default 20000)")
    h = sub.add_parser("history", help="questions and answers so far")
    h.add_argument("--session", default="main")
    sub.add_parser("check", help="test the connection")
    a = ap.parse_args()
    {"ask": cmd_ask, "history": cmd_history, "check": cmd_check}[a.cmd](a)


if __name__ == "__main__":
    main()
