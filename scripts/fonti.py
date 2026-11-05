"""Lettori delle fonti: ognuno restituisce una lista di notizie "grezze".

Formato di una notizia grezza:
    {
        "url": str, "titolo": str, "abstract": str, "data": "YYYY-MM-DD",
        "fonte": id fonte, "tipo": "notizia" | "atto", "categorie": [str],
    }
"""

import calendar
import html
import logging
import re
import time
from datetime import date, datetime, timezone

import feedparser
import requests
from bs4 import BeautifulSoup

log = logging.getLogger("fonti")

USER_AGENT = "BussolaScuola/1.0 (aggregatore non commerciale di notizie scolastiche)"
TIMEOUT = 30

FONTI = {
    "mim": {
        "nome": "Ministero dell'Istruzione e del Merito",
        "breve": "MIM",
        "ufficiale": True,
        "sito": "https://www.mim.gov.it/",
        "descrizione": "Notizie, comunicati stampa e atti normativi (decreti, note, ordinanze) pubblicati sul sito del Ministero.",
    },
    "gu": {
        "nome": "Gazzetta Ufficiale",
        "breve": "Gazzetta Ufficiale",
        "ufficiale": True,
        "sito": "https://www.gazzettaufficiale.it/",
        "descrizione": "Atti della Serie Generale emanati dal Ministero dell'Istruzione e del Merito o che riguardano la scuola.",
    },
    "indire": {
        "nome": "INDIRE",
        "breve": "INDIRE",
        "ufficiale": True,
        "sito": "https://www.indire.it/",
        "descrizione": "Istituto Nazionale di Documentazione, Innovazione e Ricerca Educativa, ente di ricerca del Ministero.",
    },
    "orizzontescuola": {
        "nome": "Orizzonte Scuola",
        "breve": "Orizzonte Scuola",
        "ufficiale": False,
        "sito": "https://www.orizzontescuola.it/",
        "descrizione": "Testata specializzata. Raccogliamo solo gli articoli su esami, riforme, norme, studenti e scuola superiore.",
    },
    "tecnicadellascuola": {
        "nome": "La Tecnica della Scuola",
        "breve": "Tecnica della Scuola",
        "ufficiale": False,
        "sito": "https://www.tecnicadellascuola.it/",
        "descrizione": "Testata specializzata. Raccogliamo solo gli articoli su esami, riforme, norme, studenti e scuola superiore.",
    },
}

MESI = {
    "gennaio": 1, "febbraio": 2, "marzo": 3, "aprile": 4, "maggio": 5,
    "giugno": 6, "luglio": 7, "agosto": 8, "settembre": 9, "ottobre": 10,
    "novembre": 11, "dicembre": 12,
}

_sessione = requests.Session()
_sessione.headers.update({"User-Agent": USER_AGENT, "Accept-Language": "it-IT,it;q=0.9"})


def scarica(url: str) -> str:
    risposta = _sessione.get(url, timeout=TIMEOUT)
    risposta.raise_for_status()
    if not risposta.encoding or risposta.encoding.lower() == "iso-8859-1":
        risposta.encoding = risposta.apparent_encoding
    return risposta.text


def pulisci_testo(testo: str) -> str:
    testo = html.unescape(testo or "")
    testo = re.sub(r"<[^>]+>", " ", testo)
    return re.sub(r"\s+", " ", testo).strip()


def accorcia(testo: str, massimo: int = 280) -> str:
    testo = pulisci_testo(testo)
    if len(testo) <= massimo:
        return testo
    taglio = testo[:massimo].rsplit(" ", 1)[0].rstrip(",;:.–- ")
    return taglio + "…"


def data_italiana(testo: str):
    """'15 settembre 2026' -> '2026-09-15'; '05/11/2026' -> '2026-11-05'."""
    testo = pulisci_testo(testo).lower()
    m = re.search(r"(\d{1,2})\s+([a-z]+)\s+(\d{4})", testo)
    if m and m.group(2) in MESI:
        return date(int(m.group(3)), MESI[m.group(2)], int(m.group(1))).isoformat()
    m = re.search(r"(\d{1,2})/(\d{1,2})/(\d{4})", testo)
    if m:
        return date(int(m.group(3)), int(m.group(2)), int(m.group(1))).isoformat()
    m = re.search(r"(\d{4})-(\d{2})-(\d{2})", testo)
    if m:
        return m.group(0)
    return None


def data_feed(voce) -> str:
    struttura = voce.get("published_parsed") or voce.get("updated_parsed")
    if struttura:
        secondi = calendar.timegm(struttura)
        return datetime.fromtimestamp(secondi, tz=timezone.utc).date().isoformat()
    return date.today().isoformat()


# --------------------------------------------------------------------------
# Ministero dell'Istruzione e del Merito
# --------------------------------------------------------------------------

MIM_BASE = "https://www.mim.gov.it/web/guest/"


def _mim_lista_box(url: str, tipo: str):
    """Pagine /notizie e /normativa: blocchi div.box_list_large."""
    zuppa = BeautifulSoup(scarica(url), "html.parser")
    risultati = []
    for box in zuppa.select("div.box_list_large"):
        link = box.select_one("h3 a[href]")
        data_el = box.select_one(".date")
        if not link or not data_el:
            continue
        risultati.append({
            "url": link["href"].strip(),
            "titolo": pulisci_testo(link.get_text()),
            "abstract": "",
            "data": data_italiana(data_el.get_text()),
            "fonte": "mim",
            "tipo": tipo,
            "categorie": [],
        })
    return risultati


def _mim_news():
    """Pagina /news: elenco completo di notizie e comunicati, con categorie."""
    zuppa = BeautifulSoup(scarica(MIM_BASE + "news"), "html.parser")
    risultati = []
    for articolo in zuppa.select("article.article"):
        link = articolo.select_one("h3 a[href]")
        data_el = articolo.select_one(".article_data")
        if not link or not data_el:
            continue
        categorie = [pulisci_testo(a.get_text()) for a in articolo.select(".article_tags a")]
        risultati.append({
            "url": link["href"].strip(),
            "titolo": pulisci_testo(link.get_text()),
            "abstract": "",
            "data": data_italiana(data_el.get_text()),
            "fonte": "mim",
            "tipo": "notizia",
            "categorie": [c for c in categorie if c],
        })
    return risultati


def _mim_homepage():
    """Notizie in evidenza della homepage (carosello e riquadri con data)."""
    zuppa = BeautifulSoup(scarica(MIM_BASE + "home"), "html.parser")
    risultati = []
    for articolo in zuppa.select("article, .home-com-card"):
        link = articolo.select_one("a[href*='/-/']")
        tempo = articolo.select_one("time")
        if not link or not tempo:
            continue
        tipologia = articolo.select_one(".item-tipologia")
        risultati.append({
            "url": link["href"].strip(),
            "titolo": pulisci_testo(link.get_text()),
            "abstract": "",
            "data": data_italiana(tempo.get("datetime") or tempo.get_text()),
            "fonte": "mim",
            "tipo": "notizia",
            "categorie": [pulisci_testo(tipologia.get_text())] if tipologia else [],
        })
    return risultati


def abstract_mim(url: str) -> str:
    """Primo paragrafo significativo del contenuto di una pagina MIM."""
    zuppa = BeautifulSoup(scarica(url), "html.parser")
    contenitore = zuppa.select_one(".asset-full-content") or zuppa.select_one("main")
    if not contenitore:
        return ""
    for paragrafo in contenitore.find_all("p"):
        testo = pulisci_testo(paragrafo.get_text(" "))
        if len(testo) < 40:
            continue
        if re.match(r"^(nota prot|ufficio:|m_pi\.|tutti i diritti)", testo, re.I):
            continue
        if testo.lower().endswith(".pdf") or data_italiana(testo) == testo:
            continue
        return accorcia(testo)
    return ""


def leggi_mim():
    risultati = []
    for nome, funzione in [
        ("homepage", _mim_homepage),
        ("news", _mim_news),
        ("notizie", lambda: _mim_lista_box(MIM_BASE + "notizie", "notizia")),
        ("normativa", lambda: _mim_lista_box(MIM_BASE + "normativa", "atto")),
    ]:
        try:
            voci = funzione()
            log.info("MIM %s: %d voci", nome, len(voci))
            risultati.extend(voci)
        except Exception as errore:  # una pagina rotta non deve fermare le altre
            log.warning("MIM %s non disponibile: %s", nome, errore)
    risultati = [v for v in risultati if v["data"] and v["titolo"]]
    if not risultati:
        raise RuntimeError("nessuna notizia trovata: il sito del MIM potrebbe essere cambiato")
    return risultati


# --------------------------------------------------------------------------
# Gazzetta Ufficiale (Serie Generale)
# --------------------------------------------------------------------------

GU_FEED = "https://www.gazzettaufficiale.it/rss/SG"
GU_FILTRO = re.compile(
    r"istruzione e del merito|scuol|scolastic|istituzioni scolastiche|esami di stato",
    re.I,
)


def _titolo_gu(titolo: str) -> str:
    """'MINISTERO DELL'ISTRUZIONE E DEL MERITO - DECRETO 7 ottobre 2026'
    -> "Ministero dell'istruzione e del merito – Decreto 7 ottobre 2026"."""
    parti = []
    for parte in (p.strip() for p in titolo.split(" - ")):
        primo = parte.split(" ", 1)[0]
        if primo.isupper():  # parti in maiuscolo: le riportiamo in tondo
            parte = parte[:1] + parte[1:].lower()
        parti.append(parte)
    return " – ".join(parti)


def leggi_gu():
    feed = feedparser.parse(scarica(GU_FEED))
    risultati = []
    for voce in feed.entries:
        contenuto = ""
        if voce.get("content"):
            contenuto = voce.content[0].get("value", "")
        contenuto = re.sub(r"\(\w+\)\s*$", "", pulisci_testo(contenuto)).strip()
        if not GU_FILTRO.search(voce.title + " " + contenuto):
            continue
        risultati.append({
            "url": voce.link.replace("http://", "https://"),
            "titolo": _titolo_gu(voce.title),
            "abstract": accorcia(contenuto),
            "data": data_feed(voce),
            "fonte": "gu",
            "tipo": "atto",
            "categorie": [],
        })
    log.info("Gazzetta Ufficiale: %d atti pertinenti su %d", len(risultati), len(feed.entries))
    return risultati


# --------------------------------------------------------------------------
# Feed RSS generici (INDIRE e stampa specializzata)
# --------------------------------------------------------------------------

FEED_RSS = {
    "indire": {"url": ["https://www.indire.it/feed/"], "max": 40, "escludi": set()},
    "orizzontescuola": {
        "url": [f"https://www.orizzontescuola.it/feed/?paged={n}" for n in (1, 2, 3)],
        "max": 60,
        "escludi": {"corsi", "pubbliredazionale", "sponsorizzato"},
    },
    "tecnicadellascuola": {
        "url": ["https://www.tecnicadellascuola.it/feed"],
        "max": 60,
        "escludi": {"i lettori ci scrivono", "corsi", "pubbliredazionale"},
    },
}


def leggi_feed(id_fonte: str):
    config = FEED_RSS[id_fonte]
    risultati, visti, errori = [], set(), []
    for url in config["url"]:
        try:
            feed = feedparser.parse(scarica(url))
        except Exception as errore:
            log.warning("%s: pagina feed %s non disponibile: %s", id_fonte, url, errore)
            errori.append(errore)
            continue
        for voce in feed.entries:
            link = voce.get("link")
            if not link or link in visti:
                continue
            visti.add(link)
            categorie = [t.get("term", "") for t in voce.get("tags", []) if t.get("term")]
            if {c.lower() for c in categorie} & config["escludi"]:
                continue
            risultati.append({
                "url": link,
                "titolo": pulisci_testo(voce.get("title", "")),
                "abstract": accorcia(voce.get("summary", "")),
                "data": data_feed(voce),
                "fonte": id_fonte,
                "tipo": "notizia",
                "categorie": categorie,
            })
        time.sleep(1)
    if len(errori) == len(config["url"]):
        raise RuntimeError(f"feed non raggiungibile ({errori[0].__class__.__name__})")
    log.info("%s: %d voci", id_fonte, len(risultati))
    return risultati[: config["max"]]


LETTORI = {
    "mim": leggi_mim,
    "gu": leggi_gu,
    "indire": lambda: leggi_feed("indire"),
    "orizzontescuola": lambda: leggi_feed("orizzontescuola"),
    "tecnicadellascuola": lambda: leggi_feed("tecnicadellascuola"),
}
