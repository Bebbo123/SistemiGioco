# Assistente Estrazioni (MillionDAY & Lotto)

Web-app Streamlit mobile-first: scarica le estrazioni, calcola frequenze / ambi / ritardatari
e trasforma il risultato in un piano settimanale da 15 € (modificabile).

> ⚠️ Le estrazioni sono casuali e indipendenti: nessuna statistica aumenta le probabilità di
> vincita. L'app organizza il budget, non prevede i numeri. Telefono Verde: 800 558822.

## Pubblicazione gratuita (Streamlit Community Cloud)
1. Crea un repository **pubblico** su GitHub e carica tutti i file di questa cartella.
2. Vai su https://share.streamlit.io, accedi con GitHub → **Create app** → seleziona repo,
   branch `main`, file principale `app.py` → **Deploy**.
3. In **Advanced settings → Secrets** (o poi *Settings → Secrets*) incolla:

       LOTTO_URLS = "https://.../lotto_{year}.txt"
       MILLIONDAY_URLS = "https://.../millionday.txt"

   `{year}` viene sostituito con l'anno corrente e i 2 precedenti. Più URL: separali con virgola.
4. Apri il link `https://nomeapp.streamlit.app` da Safari su iPhone →
   **Condividi → Aggiungi alla schermata Home**.

L'app gratuita va in "sleep" dopo un periodo di inattività: al primo accesso tocca il pulsante
per riattivarla.

## Formato dei file letti
- **Lotto**: una riga per estrazione, con data (`2026/09/26`, `26/09/2026`…), ruota
  (codice `RM` o nome `Roma`) e 5 numeri. Sono accettate anche più ruote sulla stessa riga.
- **MillionDAY**: data, orario opzionale (`13:00`/`20:30`) e 5 numeri (1–55); gli Extra dopo i
  primi 5 numeri sono ignorati.

Dopo il primo avvio controlla la scheda **Dati**: le ultime righe devono coincidere con i
risultati ufficiali. Se il formato della tua fonte è diverso, adatta `parse_lotto` /
`parse_millionday` in `data_sources.py`.

## Personalizzazione
`config.py`: giorni e orari delle estrazioni (verifica il calendario ufficiale), fascia dei
ritardatari (`LAG_MIN`/`LAG_MAX`), premi Lotto, storico minimo.

## Prova in locale
    pip install -r requirements.txt
    streamlit run app.py
Con la fonte "Demo" l'app funziona subito con dati casuali sintetici.
