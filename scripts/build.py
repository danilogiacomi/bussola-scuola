"""Genera il sito statico in _site/ a partire da data/archivio.json e data/regole.json.

Uso: python scripts/build.py [cartella_output]
"""

import json
import os
import shutil
import sys
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from jinja2 import Environment, FileSystemLoader, select_autoescape

sys.path.insert(0, str(Path(__file__).parent))

from fonti import FONTI  # noqa: E402
from sezioni import tutte_le_sezioni  # noqa: E402

RADICE = Path(__file__).resolve().parent.parent
FUSO = ZoneInfo("Europe/Rome")
NOTIZIE_STATICHE = 60      # schede nell'HTML (visibili anche senza JavaScript)
NOTIZIE_JSON = 3000        # notizie pubblicate in data/notizie.json per la ricerca
IN_EVIDENZA = 6

SITO = {
    "nome": "Bussola Scuola",
    "sottotitolo": "Notizie dal Ministero e regole per la scuola superiore",
    "descrizione": "Le ultime notizie del Ministero dell'Istruzione e del Merito e le regole per la scuola superiore, raccolte da fonti ufficiali e aggiornate più volte al giorno.",
}
MENU = [
    {"id": "notizie", "titolo": "Notizie", "href": ""},
    {"id": "regole", "titolo": "Regole scuola superiore", "href": "regole.html"},
    {"id": "fonti", "titolo": "Fonti e metodo", "href": "fonti.html"},
]
MESI = ["gennaio", "febbraio", "marzo", "aprile", "maggio", "giugno", "luglio",
        "agosto", "settembre", "ottobre", "novembre", "dicembre"]


def data_it(valore: str) -> str:
    giorno = date.fromisoformat(valore[:10])
    return f"{giorno.day} {MESI[giorno.month - 1]} {giorno.year}"


def dataora_it(valore: str) -> str:
    momento = datetime.fromisoformat(valore).astimezone(FUSO)
    return f"{data_it(momento.date().isoformat())}, ore {momento:%H:%M}"


def leggi_json(percorso: Path, predefinito):
    if percorso.exists():
        return json.loads(percorso.read_text(encoding="utf-8"))
    return predefinito


def main():
    uscita = Path(sys.argv[1]) if len(sys.argv) > 1 else RADICE / "_site"
    archivio = leggi_json(RADICE / "data" / "archivio.json", {"notizie": [], "fonti": {}})
    regole = leggi_json(RADICE / "data" / "regole.json", {"temi": []})
    notizie = archivio["notizie"]

    sezioni = {s["id"]: s for s in tutte_le_sezioni()}
    elenco_sezioni = []
    for s in tutte_le_sezioni():
        conteggio = sum(1 for n in notizie if s["id"] in n["sezioni"])
        if conteggio:
            elenco_sezioni.append({**s, "conteggio": conteggio})

    ufficiali_superiori = [n for n in notizie if n["superiori"] and FONTI[n["fonte"]]["ufficiale"]]
    aggiornato = archivio.get("aggiornato") or datetime.now().astimezone().isoformat()

    env = Environment(
        loader=FileSystemLoader(RADICE / "templates"),
        autoescape=select_autoescape(["html"]),
        trim_blocks=True,
        lstrip_blocks=True,
    )
    env.filters["data_it"] = data_it
    env.filters["dataora_it"] = dataora_it

    comune = {
        "sito": SITO,
        "menu": MENU,
        # Percorso assoluto del sito (es. "/nome-repo/"); predefinito "./" = link relativi.
        "base": os.environ.get("SITE_BASE", "./"),
        "versione": datetime.now().strftime("%Y%m%d%H%M"),
        "fonti": FONTI,
        "sezioni": sezioni,
        "elenco_sezioni": elenco_sezioni,
        "aggiornato_iso": aggiornato,
        "aggiornato_testo": dataora_it(aggiornato),
    }

    if uscita.exists():
        shutil.rmtree(uscita)
    shutil.copytree(RADICE / "static", uscita / "assets")
    (uscita / "data").mkdir(parents=True)

    pagine = {
        "index.html": ("index.html", "notizie", {
            "in_evidenza": ufficiali_superiori[:IN_EVIDENZA],
            "ultime": notizie[:NOTIZIE_STATICHE],
            "config_js": {
                "dati": "data/notizie.json",
                "fonti": {k: {"breve": v["breve"], "ufficiale": v["ufficiale"]} for k, v in FONTI.items()},
                "sezioni": {k: v["titolo"] for k, v in sezioni.items()},
            },
        }),
        "regole.html": ("regole.html", "regole", {
            "regole": regole,
            "atti_superiori": ufficiali_superiori[:9],
        }),
        "fonti.html": ("fonti.html", "fonti", {"stato_fonti": archivio.get("fonti", {})}),
        "404.html": ("404.html", "", {}),
    }
    for nome_file, (template, pagina, contesto) in pagine.items():
        html = env.get_template(template).render(**comune, pagina=pagina, **contesto)
        (uscita / nome_file).write_text(html, encoding="utf-8")

    campi = ("url", "titolo", "abstract", "data", "fonte", "tipo", "sezioni", "superiori")
    pubblicate = [{k: n.get(k) for k in campi} for n in notizie[:NOTIZIE_JSON]]
    (uscita / "data" / "notizie.json").write_text(
        json.dumps(pubblicate, ensure_ascii=False, separators=(",", ":")), encoding="utf-8"
    )
    (uscita / ".nojekyll").write_text("")
    print(f"Sito generato in {uscita} ({len(notizie)} notizie, {len(regole.get('temi', []))} temi di regole)")


if __name__ == "__main__":
    main()
