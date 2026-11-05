# Bussola Scuola

Sito statico che raccoglie le ultime notizie del Ministero dell'Istruzione e del Merito e le principali regole per la scuola superiore. È pubblicato con GitHub Pages e si aggiorna da solo tramite GitHub Actions.

## Fonti

| Fonte | Tipo | Come viene letta |
|---|---|---|
| Ministero dell'Istruzione e del Merito | ufficiale | pagine HTML `home`, `news`, `notizie` e `normativa` (il MIM non ha un feed RSS funzionante) |
| Gazzetta Ufficiale, Serie Generale | ufficiale | feed RSS; si tengono solo gli atti del MIM o che riguardano la scuola |
| INDIRE | ufficiale (ente di ricerca del MIM) | feed RSS |
| Orizzonte Scuola | stampa specializzata | feed RSS; solo articoli su esami, riforme, studenti o scuola superiore |
| La Tecnica della Scuola | stampa specializzata | feed RSS; stesso filtro |

## Struttura

```
scripts/fonti.py      lettori delle fonti
scripts/sezioni.py    sezioni tematiche e parole chiave per classificare le notizie
scripts/aggiorna.py   raccoglie le notizie e aggiorna data/archivio.json
scripts/build.py      genera il sito statico in _site/
data/archivio.json    archivio cumulativo delle notizie (circa 13 mesi), aggiornato dal workflow
data/regole.json      schede sulle regole per la scuola superiore, scritte e verificate a mano
templates/            pagine HTML (Jinja2)
static/               CSS, JavaScript e icona
```

## Uso in locale

```sh
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python scripts/aggiorna.py   # raccoglie le notizie
.venv/bin/python scripts/build.py      # genera _site/
python3 -m http.server 8000 --directory _site
```

La prima raccolta legge gli abstract delle pagine del MIM 60 alla volta. Per leggerli tutti subito: `MAX_ABSTRACT=400 .venv/bin/python scripts/aggiorna.py`.

## Pubblicazione

Il workflow `.github/workflows/aggiorna-e-pubblica.yml` parte ogni 3 ore, a ogni push su `main` e a mano dalla scheda Actions. Raccoglie le notizie, salva l'archivio nel repository e pubblica il sito su GitHub Pages.

Note:

- Il sito di INDIRE non risponde ai server di GitHub Actions, quindi in automatico quella fonte risulta in errore. Le notizie INDIRE si possono aggiungere lanciando `scripts/aggiorna.py` in locale e facendo il push di `data/archivio.json`.
- Se il salvataggio dell'archivio non riesce, il sito viene pubblicato lo stesso e le notizie mancanti tornano al giro successivo.

Una tantum, nelle impostazioni del repository: **Settings → Pages → Build and deployment → Source: GitHub Actions**.

## Manutenzione

- **Sezioni**: per aggiungere una sezione o correggere una classificazione, modificare le parole chiave in `scripts/sezioni.py`. Le sezioni vengono ricalcolate su tutto l'archivio a ogni aggiornamento.
- **Regole**: `data/regole.json` va aggiornato a mano quando escono nuove norme, ad esempio l'ordinanza sulla maturità di ogni anno o le nuove indicazioni nazionali. Ogni regola deve avere un link a una fonte ufficiale (Normattiva, Gazzetta Ufficiale, MIM).
- **Pagine del MIM**: se il Ministero cambia il layout del sito, il lettore in `scripts/fonti.py` potrebbe non trovare più le notizie. Il workflow continua a pubblicare l'archivio esistente e la pagina "Fonti e metodo" mostra la data dell'ultima lettura riuscita di ogni fonte.
