"""Motore statistico: frequenze, ambi, ritardi."""
from __future__ import annotations

from collections import Counter
from itertools import combinations

import pandas as pd


def compute_delays(seq: list[tuple], max_num: int) -> dict[int, int]:
    """Ritardo = estrazioni trascorse dall'ultima uscita del numero."""
    n, last = len(seq), {}
    for idx, nums in enumerate(seq):
        for x in nums:
            last[x] = idx
    return {k: (n - 1 - last[k]) if k in last else n for k in range(1, max_num + 1)}


def millionday_table(df: pd.DataFrame, window: int) -> pd.DataFrame:
    """Tutti i 55 numeri ordinati per uscite nelle ultime `window` estrazioni
    (a parità: prima il più recente)."""
    recent = df.tail(window)
    cnt = Counter(x for nums in recent["nums"] for x in nums)
    delays = compute_delays(list(df["nums"]), 55)
    rows = [(k, cnt.get(k, 0), delays[k]) for k in range(1, 56)]
    out = pd.DataFrame(rows, columns=["numero", "uscite", "ritardo"])
    return out.sort_values(["uscite", "ritardo", "numero"],
                           ascending=[False, True, True]).reset_index(drop=True)


def _pair_delay(seq: list[tuple], pair: tuple[int, int]) -> int:
    a, b = pair
    for d, nums in enumerate(reversed(seq)):
        if a in nums and b in nums:
            return d
    return len(seq)


def lotto_pairs(df_wheel: pd.DataFrame, window: int, top_n: int = 5) -> pd.DataFrame:
    """Ambi più frequenti su una ruota nelle ultime `window` estrazioni."""
    recent = df_wheel.tail(window)
    cnt: Counter = Counter()
    for nums in recent["nums"]:
        cnt.update(combinations(sorted(nums), 2))
    seq = list(df_wheel["nums"])
    cand = sorted(cnt.items(), key=lambda kv: (-kv[1], kv[0]))[:40]
    rows = [(p, c, _pair_delay(seq, p)) for p, c in cand]
    out = pd.DataFrame(rows, columns=["ambo", "uscite", "ritardo"])
    out = out.sort_values(["uscite", "ritardo"], ascending=[False, True])
    return out.head(top_n).reset_index(drop=True)


def lotto_delayed(df_wheel: pd.DataFrame, lo: int, hi: int) -> pd.DataFrame:
    """Numeri con ritardo in [lo, hi], dal più ritardato."""
    delays = compute_delays(list(df_wheel["nums"]), 90)
    rows = [(k, d) for k, d in delays.items() if lo <= d <= hi]
    out = pd.DataFrame(rows, columns=["numero", "ritardo"])
    return out.sort_values(["ritardo", "numero"], ascending=[False, True]).reset_index(drop=True)


def lotto_near_band(df_wheel: pd.DataFrame, lo: int) -> pd.DataFrame:
    """Numeri con ritardo appena sotto la fascia (< lo), dal più ritardato."""
    delays = compute_delays(list(df_wheel["nums"]), 90)
    rows = [(k, d) for k, d in delays.items() if d < lo]
    out = pd.DataFrame(rows, columns=["numero", "ritardo"])
    return out.sort_values(["ritardo", "numero"], ascending=[False, True]).reset_index(drop=True)
