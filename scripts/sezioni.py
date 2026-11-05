"""Classificazione delle notizie in sezioni tematiche tramite parole chiave.

Ogni notizia può appartenere a più sezioni. Le parole chiave sono confrontate
con titolo, abstract e categorie della notizia, in minuscolo e senza accenti.
"""

import re
import unicodedata

# L'ordine conta: è anche l'ordine in cui le sezioni compaiono nel sito.
SEZIONI = [
    {
        "id": "esami",
        "titolo": "Maturità ed esami",
        "descrizione": "Esame di Stato, prove, commissioni, esami integrativi e di idoneità.",
        "parole": [
            "maturita", "esame di stato", "esami di stato", "maturandi",
            "seconda prova", "prima prova", "colloquio", "commissari",
            "commissioni d'esame", "esami integrativi", "esami di idoneita",
            "prove d'esame", "sessione suppletiva", "invalsi",
        ],
    },
    {
        "id": "norme",
        "titolo": "Atti ufficiali",
        "descrizione": "Decreti, ordinanze, note e circolari del Ministero e atti in Gazzetta Ufficiale.",
        # Sezione assegnata solo agli atti (tipo "atto"), non per parole chiave.
        "parole": [],
    },
    {
        "id": "riforme",
        "titolo": "Riforme e ordinamenti",
        "descrizione": "Riforme di licei, tecnici e professionali, valutazione, condotta, curricoli.",
        "parole": [
            "riforma", "istituti tecnici", "istituti professionali",
            "4+2", "filiera tecnologico", "indicazioni nazionali",
            "linee guida", "voto in condotta", "condotta", "valutazione",
            "smartphone", "cellulare", "educazione civica", "curricol",
            "passaggi di indirizzo", "ordinamento", "quadri orari",
        ],
    },
    {
        "id": "studenti",
        "titolo": "Studenti e famiglie",
        "descrizione": "Iscrizioni, orientamento, benessere, diritto allo studio, scuola-lavoro.",
        "parole": [
            "studenti", "studentesse", "famiglie", "genitori", "iscrizioni",
            "orientamento", "benessere", "consulte", "bullismo",
            "diritto allo studio", "borse di studio", "carta dello studente",
            "pcto", "scuola-lavoro", "scuola lavoro", "alunni",
        ],
    },
    {
        "id": "personale",
        "titolo": "Docenti e personale",
        "descrizione": "Concorsi, supplenze, graduatorie, mobilità, contratto e scioperi.",
        "parole": [
            "docenti", "insegnanti", "personale ata", " ata ", "dsga",
            "concorso", "concorsi", "supplenze", "gps", "graduatorie",
            "mobilita", "immissioni in ruolo", "ruoli", "dirigenti scolastici",
            "contratto", "ccnl", "sciopero", "stipendi", "reclutamento",
            "formazione docenti", "abilitazione",
        ],
    },
    {
        "id": "innovazione",
        "titolo": "Digitale e innovazione",
        "descrizione": "Intelligenza artificiale, PNRR, competenze digitali e STEM.",
        "parole": [
            "intelligenza artificiale", " ia ", "digitale", "digitali", "pnrr",
            "stem", "innovazione", "laboratori", "tecnologi",
        ],
    },
    {
        "id": "inclusione",
        "titolo": "Inclusione",
        "descrizione": "Disabilità, sostegno, DSA e BES, dispersione scolastica.",
        "parole": [
            "inclusione", "disabilita", "sostegno", "dsa", "bes",
            "dispersione", "minorazione", "istruzione ospedaliera",
            "stranieri", "fragilita",
        ],
    },
]

SEZIONE_ALTRO = {
    "id": "altro",
    "titolo": "Altre notizie",
    "descrizione": "Notizie che non rientrano nelle altre sezioni.",
}

# Indicatori che una notizia riguarda la scuola secondaria di secondo grado.
PAROLE_SUPERIORI = [
    "secondaria di secondo grado", "secondarie di secondo grado",
    "scuola superiore", "scuole superiori", "superiori", "liceo", "licei",
    "istituti tecnici", "istituto tecnico", "istituti professionali",
    "istituto professionale", "maturita", "esame di stato", "esami di stato",
    "maturandi", "pcto", "scuola-lavoro", "scuola lavoro", "4+2",
    "filiera tecnologico", "its academy", "quinto anno", "triennio",
    "esami integrativi", "passaggi di indirizzo", "grado 13",
]


def normalizza(testo: str) -> str:
    """Minuscolo, senza accenti e con spazi ai bordi per i confronti a parola."""
    testo = unicodedata.normalize("NFKD", testo or "")
    testo = "".join(c for c in testo if not unicodedata.combining(c))
    testo = testo.lower().replace("’", "'")
    testo = re.sub(r"\s+", " ", testo)
    return f" {testo} "


def classifica(titolo: str, abstract: str = "", categorie=(), tipo: str = "notizia"):
    """Restituisce (lista id sezioni, riguarda_superiori)."""
    testo = normalizza(" ".join([titolo, abstract, " ".join(categorie)]))
    sezioni = []
    for sezione in SEZIONI:
        if sezione["id"] == "norme":
            if tipo == "atto":
                sezioni.append("norme")
            continue
        if any(parola in testo for parola in sezione["parole"]):
            sezioni.append(sezione["id"])
    if not sezioni:
        sezioni.append(SEZIONE_ALTRO["id"])
    superiori = any(parola in testo for parola in PAROLE_SUPERIORI)
    return sezioni, superiori


def tutte_le_sezioni():
    return SEZIONI + [SEZIONE_ALTRO]
