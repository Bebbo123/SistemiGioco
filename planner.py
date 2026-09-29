"""Money management: trasforma la statistica in un piano settimanale."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from config import (CUTOFF_MINUTES, LOTTO_DRAW_TIME, LOTTO_DRAW_WEEKDAYS,
                    LOTTO_PAYOUT, MILLIONDAY_DRAW_TIMES, TZ_NAME)

TZ = ZoneInfo(TZ_NAME)


@dataclass
class Bet:
    game: str           # "MillionDAY" | "Lotto"
    kind: str           # "5 numeri" | "ambo" | "ambata"
    numbers: list[int]
    stake: int
    when: datetime      # ora dell'estrazione
    wheel: str | None = None
    note: str = ""

    @property
    def deadline(self) -> datetime:
        return self.when - timedelta(minutes=CUTOFF_MINUTES)


@dataclass
class Block:
    key: str
    title: str
    subtitle: str
    budget: int
    bets: list[Bet] = field(default_factory=list)

    @property
    def spent(self) -> int:
        return sum(b.stake for b in self.bets)


@dataclass
class Plan:
    blocks: list[Block]
    warnings: list[str]

    @property
    def spent(self) -> int:
        return sum(b.spent for b in self.blocks)

    @property
    def bets(self) -> list[Bet]:
        return sorted((b for blk in self.blocks for b in blk.bets), key=lambda x: x.when)

    def lotto_expected_return(self) -> float | None:
        """Ritorno atteso teorico (in euro) sulle sole giocate Lotto."""
        ev = 0.0
        for b in self.bets:
            if b.game != "Lotto":
                continue
            if b.kind == "ambo":
                ev += b.stake * LOTTO_PAYOUT["ambo"] * 10 / 4005
            elif b.kind == "ambata":
                ev += b.stake * LOTTO_PAYOUT["ambata"] * 5 / 90
        return ev


def _upcoming(now: datetime, times, weekdays=None, days: int = 7) -> list[datetime]:
    out = []
    for i in range(days + 1):
        d = (now + timedelta(days=i)).date()
        if weekdays is not None and d.weekday() not in weekdays:
            continue
        for t in times:
            dt = datetime.combine(d, t, tzinfo=TZ)
            if dt - timedelta(minutes=CUTOFF_MINUTES) > now and dt <= now + timedelta(days=days):
                out.append(dt)
    return sorted(out)


def upcoming_lotto(now: datetime) -> list[datetime]:
    return _upcoming(now, [LOTTO_DRAW_TIME], LOTTO_DRAW_WEEKDAYS)


def upcoming_millionday_evenings(now: datetime) -> list[datetime]:
    return _upcoming(now, [MILLIONDAY_DRAW_TIMES[-1]])


def split_budget(budget: int, parts: int = 3) -> list[int]:
    base, extra = divmod(int(budget), parts)
    return [base + (1 if i < extra else 0) for i in range(parts)]


def distribute(total: int, slots: int) -> list[int]:
    if slots <= 0 or total <= 0:
        return []
    slots = min(slots, total)
    base, extra = divmod(total, slots)
    return [base + (1 if i < extra else 0) for i in range(slots)]


def millionday_combos(top_numbers: list[int], n: int) -> list[list[int]]:
    """n combinazioni da 5 numeri ruotando sui 10 più frequenti (la prima = top 5)."""
    pool = list(top_numbers[:10])
    if len(pool) < 5 or n <= 0:
        return []
    L = len(pool)
    return [sorted(pool[(3 * k + j) % L] for j in range(5)) for k in range(n)]


def build_plan(*, budget: int, wheel_name: str, wheel_code: str,
               md_top: list[int], best_pair: tuple[int, int] | None,
               delayed: list[int], near: list[int] | None = None,
               now: datetime | None = None) -> Plan:
    now = now or datetime.now(TZ)
    b1, b2, b3 = split_budget(budget)
    warnings: list[str] = []

    # 1) MillionDAY: giocate da 1 € sui 10 numeri più frequenti, una per sera
    blk1 = Block("md", "MillionDAY", "Numeri più frequenti, una schedina da 1 € per volta", b1)
    evenings = upcoming_millionday_evenings(now)
    combos = millionday_combos(md_top, b1)
    if combos and evenings:
        for i, c in enumerate(combos):
            blk1.bets.append(Bet("MillionDAY", "5 numeri", c, 1, evenings[i % len(evenings)]))
    else:
        warnings.append("MillionDAY: dati o estrazioni future insufficienti.")

    # 2) Lotto ambo più frequente, spalmato sulle estrazioni della settimana
    blk2 = Block("ambo", f"Lotto · ambo su {wheel_name}",
                 "Ambo più frequente della ruota", b2)
    draws = upcoming_lotto(now)
    if best_pair and draws:
        for amt, dt in zip(distribute(b2, len(draws)), draws):
            blk2.bets.append(Bet("Lotto", "ambo", list(best_pair), amt, dt, wheel_code))
    else:
        warnings.append("Lotto ambo: dati o estrazioni future insufficienti.")

    # 3) Copertura: ambate sui ritardatari di fascia intermedia (1 € ciascuno)
    blk3 = Block("rit", f"Lotto · ritardatari su {wheel_name}",
                 "Ambate da 1 € sui ritardatari di fascia intermedia", b3)
    near = near or []
    chosen = list(delayed[:b3])
    filler = near[: max(0, b3 - len(chosen))]
    chosen += filler
    if chosen and draws:
        blk3.bets.append(Bet("Lotto", "ambata", chosen, len(chosen), draws[0], wheel_code,
                             note="1 € su ciascun numero"))
        if filler:
            warnings.append(f"Solo {len(delayed)} numeri in fascia intermedia: aggiunti "
                            f"{len(filler)} numeri appena sotto la fascia ({', '.join(map(str, filler))}) "
                            "per completare il blocco.")
        if len(chosen) < b3:
            warnings.append(f"Ritardatari: {b3 - len(chosen)} € non assegnati.")
    else:
        warnings.append("Ritardatari: nessun numero utile o nessuna estrazione disponibile.")

    return Plan([blk1, blk2, blk3], warnings)
