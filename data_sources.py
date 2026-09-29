"""Download e parsing delle estrazioni (Lotto e MillionDAY) + dati demo."""
from __future__ import annotations

import random
import re
from datetime import date, timedelta

import pandas as pd
import requests

from config import LOTTO_DRAW_WEEKDAYS, WHEEL_ALIASES, WHEELS

UA = {"User-Agent": "Mozilla/5.0 (compatible; AssistenteEstrazioni/1.0)"}

# Accetta 2026/09/29, 2026-09-29, 29/09/2026, 29-09-2026, 29.09.2026
DATE_RE = re.compile(
    r"(\d{4})[/\-.](\d{1,2})[/\-.](\d{1,2})|(\d{1,2})[/\-.](\d{1,2})[/\-.](\d{4})"
)
TIME_RE = re.compile(r"\b([01]?\d|2[0-3]):([0-5]\d)\b")

LOTTO_COLS = ["date", "wheel", "nums", "seq"]
MD_COLS = ["date", "slot", "nums", "seq"]


def empty_lotto() -> pd.DataFrame:
    return pd.DataFrame(columns=LOTTO_COLS)


def empty_md() -> pd.DataFrame:
    return pd.DataFrame(columns=MD_COLS)


def _to_date(m: re.Match) -> date | None:
    try:
        if m.group(1):
            return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
        return date(int(m.group(6)), int(m.group(5)), int(m.group(4)))
    except ValueError:
        return None


def _flush(rows, d, wheel, nums, seq):
    if wheel and len(nums) >= 5:
        rows.append((d, wheel, tuple(nums[:5]), seq))


def parse_lotto(text: str) -> pd.DataFrame:
    """Una riga = data + ruota (codice o nome) + 5 numeri.
    Supporta anche righe con più ruote per la stessa data."""
    rows = []
    for seq, line in enumerate(text.splitlines()):
        m = DATE_RE.search(line)
        if not m:
            continue
        d = _to_date(m)
        if d is None:
            continue
        wheel, nums = None, []
        for tok in re.findall(r"[^\W\d_]+|\d+", line[m.end():]):
            if tok.isdigit():
                n = int(tok)
                if wheel is not None and 1 <= n <= 90:
                    nums.append(n)
            else:
                code = WHEEL_ALIASES.get(tok.upper())
                if code:
                    _flush(rows, d, wheel, nums, seq)
                    wheel, nums = code, []
        _flush(rows, d, wheel, nums, seq)
    if not rows:
        return empty_lotto()
    df = pd.DataFrame(rows, columns=LOTTO_COLS)
    df = df.drop_duplicates(["date", "wheel"], keep="last")
    return df.sort_values(["date", "seq"]).reset_index(drop=True)


def parse_millionday(text: str) -> pd.DataFrame:
    """Una riga = data [+ orario] + 5 numeri (1-55). Eventuali numeri Extra
    dopo i primi 5 vengono ignorati."""
    rows = []
    for seq, line in enumerate(text.splitlines()):
        m = DATE_RE.search(line)
        if not m:
            continue
        d = _to_date(m)
        if d is None:
            continue
        rest = line[m.end():]
        slot = ""
        tm = TIME_RE.search(rest)
        if tm:
            slot = f"{int(tm.group(1)):02d}:{tm.group(2)}"
            rest = rest[: tm.start()] + " " + rest[tm.end():]
        nums = [int(t) for t in re.findall(r"\d+", rest)]
        nums = [n for n in nums if 1 <= n <= 55]
        if len(nums) in (6, 11):          # primo valore = numero di concorso
            nums = nums[1:]
        if len(nums) < 5:
            continue
        rows.append((d, slot, tuple(nums[:5]), seq))
    if not rows:
        return empty_md()
    df = pd.DataFrame(rows, columns=MD_COLS)
    df = df.drop_duplicates(["date", "slot", "nums"], keep="last")
    return df.sort_values(["date", "slot", "seq"]).reset_index(drop=True)


# ---------------------------------------------------------------- download
def fetch_text(url: str, timeout: int = 20) -> str:
    r = requests.get(url, timeout=timeout, headers=UA)
    r.raise_for_status()
    try:
        return r.content.decode("utf-8")
    except UnicodeDecodeError:
        return r.content.decode("latin-1")


def expand_urls(templates: list[str], years_back: int) -> list[str]:
    """Se l'URL contiene {year} scarica l'anno corrente e i precedenti."""
    urls, y = [], date.today().year
    for t in templates:
        if "{year}" in t:
            urls += [t.replace("{year}", str(y - i)) for i in range(years_back + 1)]
        else:
            urls.append(t)
    return urls


def fetch_all(templates: list[str], years_back: int = 2) -> tuple[str, list[str]]:
    texts, errors = [], []
    for url in expand_urls(templates, years_back):
        try:
            texts.append(fetch_text(url))
        except Exception as exc:  # rete, 404, ecc.
            errors.append(f"{url} → {exc}")
    return "\n".join(texts), errors


# -------------------------------------------------------------------- demo
def demo_lotto(days: int = 1000) -> pd.DataFrame:
    """Dati SINTETICI casuali, solo per provare l'interfaccia."""
    rng, rows, seq = random.Random(42), [], 0
    today = date.today()
    for i in range(days, -1, -1):
        d = today - timedelta(days=i)
        if d.weekday() in LOTTO_DRAW_WEEKDAYS:
            for w in WHEELS:
                rows.append((d, w, tuple(sorted(rng.sample(range(1, 91), 5))), seq))
                seq += 1
    return pd.DataFrame(rows, columns=LOTTO_COLS)


def demo_millionday(days: int = 400) -> pd.DataFrame:
    rng, rows, seq = random.Random(7), [], 0
    today = date.today()
    for i in range(days, -1, -1):
        d = today - timedelta(days=i)
        for slot in ("13:00", "20:30"):
            rows.append((d, slot, tuple(sorted(rng.sample(range(1, 56), 5))), seq))
            seq += 1
    return pd.DataFrame(rows, columns=MD_COLS)
