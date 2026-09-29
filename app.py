"""Assistente Statistico e Finanziario – MillionDAY & Lotto (Streamlit, mobile-first)."""
from __future__ import annotations

import os
import re
from datetime import datetime

import pandas as pd
import streamlit as st

import data_sources as ds
import planner
import stats_engine as se
from config import (DAYS_IT, DEFAULT_WHEEL, LAG_MAX, LAG_MIN, MIN_LOTTO_HISTORY,
                    MIN_MD_HISTORY, WHEELS)

st.set_page_config(page_title="Assistente Estrazioni", page_icon="🎱",
                   layout="centered", initial_sidebar_state="collapsed")

CSS = """
@import url('https://fonts.googleapis.com/css2?family=Bricolage+Grotesque:wght@500;700;800&display=swap');
.block-container{padding:1rem .8rem 4rem;max-width:640px}
h1,h2,h3,.ball,.kpi b{font-family:'Bricolage Grotesque',system-ui,sans-serif}
.ball{display:inline-flex;align-items:center;justify-content:center;width:36px;height:36px;
  border-radius:50%;color:#fff;font-weight:800;font-size:15px;margin:2px 3px 2px 0;
  box-shadow:inset 0 -3px 0 rgba(0,0,0,.18),inset 0 2px 0 rgba(255,255,255,.25)}
.ball.md{background:#d62828}.ball.amb{background:#1d6fa5}.ball.rit{background:#d98e04}
.ball.sm{width:28px;height:28px;font-size:12.5px}
.kpis{display:flex;gap:8px;margin:.4rem 0 1rem}
.kpi{flex:1;padding:10px 12px;border-radius:14px;background:rgba(127,127,127,.10)}
.kpi b{display:block;font-size:22px;line-height:1.15}.kpi span{font-size:12px;opacity:.7}
.blk{border-radius:16px;margin:0 0 14px;padding:14px 14px 6px;border-left:6px solid var(--c);
  background:rgba(127,127,127,.08)}
.blk.md{--c:#d62828}.blk.amb{--c:#1d6fa5}.blk.rit{--c:#d98e04}
.blk h3{margin:0;font-size:19px}.blk .sub{font-size:13px;opacity:.7;margin:2px 0 8px}
.blk .tot{float:right;font-weight:700;font-size:15px}
.bet{display:flex;align-items:center;gap:10px;padding:9px 0;border-top:1px solid rgba(127,127,127,.22)}
.bet .when{flex:0 0 96px;font-size:13px;line-height:1.3}.bet .when small{opacity:.65}
.bet .nums{flex:1}.bet .stake{font-weight:800;font-size:16px;font-family:'Bricolage Grotesque',sans-serif}
.row{display:flex;align-items:center;gap:10px;padding:7px 0;border-top:1px solid rgba(127,127,127,.2)}
.row .txt{flex:1;font-size:14px}.row .txt small{opacity:.65;display:block}
.note{border-radius:12px;padding:10px 12px;font-size:13px;line-height:1.45;
  background:rgba(217,142,4,.14);margin:.2rem 0 1rem}
"""
st.markdown(f"<style>{CSS}</style>", unsafe_allow_html=True)


# ----------------------------------------------------------------- helpers
def get_setting(name: str, default: str = "") -> str:
    if os.environ.get(name):
        return os.environ[name]
    try:
        return str(st.secrets.get(name, default))
    except Exception:
        return default


def split_urls(text: str) -> list[str]:
    return [u.strip() for u in re.split(r"[,\n]", text or "") if u.strip()]


def balls(nums, cls: str, small: bool = False) -> str:
    size = " sm" if small else ""
    return "".join(f'<span class="ball {cls}{size}">{n}</span>' for n in nums)


def fmt_when(dt: datetime) -> str:
    return f"{DAYS_IT[dt.weekday()]} {dt:%d/%m} · {dt:%H:%M}"


def read_upload(file) -> str:
    raw = file.getvalue()
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError:
        return raw.decode("latin-1")


@st.cache_data(ttl=3600, show_spinner=False)
def load_online(lotto_urls: tuple, md_urls: tuple, years_back: int):
    lt, le = ds.fetch_all(list(lotto_urls), years_back)
    mt, me = ds.fetch_all(list(md_urls), years_back)
    return ds.parse_lotto(lt), ds.parse_millionday(mt), le + me


@st.cache_data(show_spinner=False)
def load_demo():
    return ds.demo_lotto(), ds.demo_millionday()


# ---------------------------------------------------------------- header
st.markdown("## 🎱 Assistente Estrazioni")
st.caption("MillionDAY e Lotto: statistica, budget e piano della settimana")

has_urls = bool(get_setting("LOTTO_URLS") or get_setting("MILLIONDAY_URLS"))

with st.expander("⚙️ Impostazioni"):
    source = st.radio("Fonte dati", ["Online", "File", "Demo"],
                      index=0 if has_urls else 2, horizontal=True)
    wheel_code = st.selectbox("Ruota del Lotto", list(WHEELS),
                              index=list(WHEELS).index(DEFAULT_WHEEL),
                              format_func=lambda c: WHEELS[c])
    budget = int(st.number_input("Budget settimanale (€)", 3, 100, 15, step=1))
    win_md = st.slider("Finestra MillionDAY (ultime estrazioni)", 50, 500, 150, step=10)
    win_lotto = st.slider("Finestra ambi Lotto (ultime estrazioni)", 100, 1000, 400, step=50)
    lotto_txt = md_txt = ""
    up_l = up_m = None
    if source == "Online":
        lotto_txt = st.text_area("URL archivio Lotto (uno per riga; {year} = anno)",
                                 value=get_setting("LOTTO_URLS"), height=70)
        md_txt = st.text_area("URL archivio MillionDAY (uno per riga; {year} = anno)",
                              value=get_setting("MILLIONDAY_URLS"), height=70)
    elif source == "File":
        up_l = st.file_uploader("File estrazioni Lotto (.txt/.csv)", type=["txt", "csv"])
        up_m = st.file_uploader("File estrazioni MillionDAY (.txt/.csv)", type=["txt", "csv"])
    if st.button("🔄 Aggiorna dati ora"):
        st.cache_data.clear()
        st.rerun()

# ---------------------------------------------------------------- dati
errors: list[str] = []
lotto_df, md_df = ds.empty_lotto(), ds.empty_md()
if source == "Online":
    l_urls, m_urls = split_urls(lotto_txt), split_urls(md_txt)
    if l_urls or m_urls:
        with st.spinner("Scarico le ultime estrazioni…"):
            lotto_df, md_df, errors = load_online(tuple(l_urls), tuple(m_urls), 2)
    else:
        st.warning("Nessuna fonte online configurata. Aggiungi gli URL in Impostazioni "
                   "(o nei Secrets), oppure usa File / Demo.")
elif source == "File":
    if up_l:
        lotto_df = ds.parse_lotto(read_upload(up_l))
    if up_m:
        md_df = ds.parse_millionday(read_upload(up_m))
else:
    lotto_df, md_df = load_demo()
    st.info("Modalità Demo: dati casuali sintetici, utili solo per provare l'app.")

for e in errors:
    st.error(f"Download non riuscito: {e}")

wheel_name = WHEELS[wheel_code]
lotto_w = lotto_df[lotto_df["wheel"] == wheel_code] if len(lotto_df) else lotto_df
md_ok = len(md_df) >= MIN_MD_HISTORY
lotto_ok = len(lotto_w) >= MIN_LOTTO_HISTORY

if len(md_df) and not md_ok:
    st.warning(f"MillionDAY: servono almeno {MIN_MD_HISTORY} estrazioni (trovate {len(md_df)}).")
if len(lotto_df) and not lotto_ok:
    st.warning(f"Lotto {wheel_name}: servono almeno {MIN_LOTTO_HISTORY} estrazioni "
               f"(trovate {len(lotto_w)}).")

md_tab = se.millionday_table(md_df, win_md) if md_ok else None
pairs = se.lotto_pairs(lotto_w, win_lotto, 5) if lotto_ok else None
delayed = se.lotto_delayed(lotto_w, LAG_MIN, LAG_MAX) if lotto_ok else None
near = se.lotto_near_band(lotto_w, LAG_MIN) if lotto_ok else None

tab_plan, tab_md, tab_lotto, tab_data = st.tabs(["📋 Piano", "🔴 MillionDAY", "🔵 Lotto", "🗂 Dati"])

# ------------------------------------------------------------------ Piano
with tab_plan:
    st.markdown(
        '<div class="note"><b>Prima di giocare:</b> le estrazioni sono indipendenti e casuali. '
        'Frequenze e ritardi non aumentano la probabilità di vincita, e il rendimento atteso '
        'è sempre inferiore al 100% della spesa. Il piano serve a organizzare il budget, '
        'non a prevedere i numeri. Se il gioco ti preoccupa: Telefono Verde 800 558822.</div>',
        unsafe_allow_html=True)

    if not (md_ok and lotto_ok):
        st.info("Servono dati validi sia per MillionDAY sia per la ruota scelta.")
    else:
        plan = planner.build_plan(
            budget=budget, wheel_name=wheel_name, wheel_code=wheel_code,
            md_top=md_tab.head(10)["numero"].tolist(),
            best_pair=tuple(pairs.iloc[0]["ambo"]) if len(pairs) else None,
            delayed=delayed["numero"].tolist() if len(delayed) else [],
            near=near["numero"].tolist())
        bets = plan.bets
        nxt = min(bets, key=lambda b: b.deadline) if bets else None
        ev = plan.lotto_expected_return()
        st.markdown(
            '<div class="kpis">'
            f'<div class="kpi"><b>€{plan.spent}</b><span>da investire su €{budget}</span></div>'
            f'<div class="kpi"><b>{len(bets)}</b><span>giocate</span></div>'
            f'<div class="kpi"><b>{fmt_when(nxt.deadline) if nxt else "–"}</b>'
            '<span>prossima scadenza</span></div></div>', unsafe_allow_html=True)

        cls = {"md": "md", "ambo": "amb", "rit": "rit"}
        for blk in plan.blocks:
            c = cls[blk.key]
            rows = ""
            for b in blk.bets:
                per = f'<br><small>{b.note}</small>' if b.note else ""
                rows += (f'<div class="bet"><div class="when"><b>{fmt_when(b.when)}</b><br>'
                         f'<small>gioca entro {b.deadline:%H:%M}</small></div>'
                         f'<div class="nums">{balls(b.numbers, c)}<small>{b.kind}'
                         f'{" · " + WHEELS[b.wheel] if b.wheel else ""}</small>{per}</div>'
                         f'<div class="stake">€{b.stake}</div></div>')
            if not blk.bets:
                rows = '<div class="bet"><small>Nessuna giocata disponibile.</small></div>'
            st.markdown(
                f'<div class="blk {c}"><span class="tot">€{blk.spent}/{blk.budget}</span>'
                f'<h3>{blk.title}</h3><div class="sub">{blk.subtitle}</div>{rows}</div>',
                unsafe_allow_html=True)

        for w in plan.warnings:
            st.warning(w)
        if ev:
            lotto_stake = sum(b.stake for b in bets if b.game == "Lotto")
            st.caption(f"Rendimento atteso teorico sul Lotto: circa €{ev:.2f} ogni "
                       f"€{lotto_stake} giocati (≈{ev / lotto_stake:.0%}). "
                       "Orari e giorni delle estrazioni sono indicativi: verifica il calendario ufficiale.")

# -------------------------------------------------------------- MillionDAY
with tab_md:
    if not md_ok:
        st.info("Nessun dato MillionDAY sufficiente.")
    else:
        last = md_df.iloc[-1]
        st.markdown(f"**Ultima estrazione** · {last['date']:%d/%m/%Y} {last['slot']}")
        st.markdown(balls(last["nums"], "md"), unsafe_allow_html=True)
        st.markdown(f"### Più frequenti nelle ultime {min(win_md, len(md_df))} estrazioni")
        html = ""
        for _, r in md_tab.head(10).iterrows():
            html += (f'<div class="row">{balls([r.numero], "md", True)}'
                     f'<div class="txt"><b>{r.uscite} uscite</b>'
                     f'<small>ritardo attuale: {r.ritardo}</small></div></div>')
        st.markdown(html, unsafe_allow_html=True)
        st.bar_chart(md_tab.sort_values("numero").set_index("numero")["uscite"],
                     color="#d62828", height=200)

# ------------------------------------------------------------------- Lotto
with tab_lotto:
    if not lotto_ok:
        st.info("Nessun dato Lotto sufficiente per la ruota scelta.")
    else:
        last = lotto_w.iloc[-1]
        st.markdown(f"**Ultima estrazione su {wheel_name}** · {last['date']:%d/%m/%Y}")
        st.markdown(balls(last["nums"], "amb"), unsafe_allow_html=True)

        st.markdown(f"### Ambi più frequenti ({min(win_lotto, len(lotto_w))} estrazioni)")
        html = ""
        for _, r in pairs.iterrows():
            html += (f'<div class="row">{balls(r.ambo, "amb", True)}'
                     f'<div class="txt"><b>{r.uscite} uscite</b>'
                     f'<small>ritardo attuale: {r.ritardo}</small></div></div>')
        st.markdown(html, unsafe_allow_html=True)

        st.markdown(f"### Ritardatari in fascia {LAG_MIN}–{LAG_MAX}")
        if len(delayed):
            html = ""
            for _, r in delayed.iterrows():
                html += (f'<div class="row">{balls([r.numero], "rit", True)}'
                         f'<div class="txt"><b>ritardo {r.ritardo}</b></div></div>')
            st.markdown(html, unsafe_allow_html=True)
        else:
            st.caption("Nessun numero in questa fascia sulla ruota scelta.")

# -------------------------------------------------------------------- Dati
with tab_data:
    st.markdown("**Verifica del parsing** (ultime righe lette)")
    if len(md_df):
        st.caption(f"MillionDAY · {len(md_df)} estrazioni · ultima {md_df.iloc[-1]['date']:%d/%m/%Y}")
        st.dataframe(md_df.tail(5).drop(columns="seq"), hide_index=True)
    if len(lotto_df):
        st.caption(f"Lotto · {len(lotto_df)} righe, {lotto_df['wheel'].nunique()} ruote · "
                   f"ultima {lotto_df.iloc[-1]['date']:%d/%m/%Y}")
        st.dataframe(lotto_w.tail(5).drop(columns="seq"), hide_index=True)
    if not len(md_df) and not len(lotto_df):
        st.caption("Ancora nessun dato caricato.")
    st.caption("Se le righe non coincidono con i risultati ufficiali, il formato della fonte "
               "non è stato letto correttamente: controlla il README.")
