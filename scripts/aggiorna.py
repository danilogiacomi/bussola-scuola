"""Raccoglie le notizie da tutte le fonti e aggiorna data/archivio.json.

Uso: python scripts/aggiorna.py

L'archivio è cumulativo: le notizie già raccolte restano anche quando escono
dai feed delle fonti, fino a GIORNI_ARCHIVIO giorni.
"""

import hashlib
import json
import logging
import os
import sys
import time
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from fonti import FONTI, LETTORI, abstract_mim  # noqa: E402
from sezioni import classifica  # noqa: E402

RADICE = Path(__file__).resolve().parent.parent
ARCHIVIO = RADICE / "data" / "archivio.json"
GIORNI_ARCHIVIO = 400
MAX_ABSTRACT_MIM_PER_GIRO = int(os.environ.get("MAX_ABSTRACT", "60"))
# La stampa specializzata pubblica molto: teniamo solo i temi di interesse.
SEZIONI_STAMPA = {"esami", "riforme", "studenti"}

log = logging.getLogger("aggiorna")


def id_notizia(url: str) -> str:
    return hashlib.sha1(url.strip().rstrip("/").encode()).hexdigest()[:12]


def carica_archivio():
    if ARCHIVIO.exists():
        return json.loads(ARCHIVIO.read_text(encoding="utf-8"))
    return {"aggiornato": None, "fonti": {}, "notizie": []}


def salva_archivio(archivio):
    ARCHIVIO.parent.mkdir(parents=True, exist_ok=True)
    testo = json.dumps(archivio, ensure_ascii=False, indent=1)
    ARCHIVIO.write_text(testo + "\n", encoding="utf-8")


def pertinente(notizia) -> bool:
    if FONTI[notizia["fonte"]]["ufficiale"]:
        return True
    return notizia["superiori"] or bool(set(notizia["sezioni"]) & SEZIONI_STAMPA)


def main():
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    archivio = carica_archivio()
    per_id = {n["id"]: n for n in archivio["notizie"]}
    oggi = date.today().isoformat()
    adesso = datetime.now(timezone.utc).isoformat(timespec="seconds")
    nuove = 0

    for id_fonte, lettore in LETTORI.items():
        stato = archivio["fonti"].setdefault(id_fonte, {})
        try:
            voci = lettore()
        except Exception as errore:
            log.error("Fonte %s non disponibile: %s", id_fonte, errore)
            stato.update({"esito": "errore", "messaggio": str(errore)[:200], "controllato": adesso})
            continue
        stato.update({"esito": "ok", "voci": len(voci), "controllato": adesso, "ultimo_ok": adesso})
        stato.pop("messaggio", None)

        for voce in voci:
            nid = id_notizia(voce["url"])
            esistente = per_id.get(nid)
            if esistente:
                # aggiorna il tipo (una notizia MIM può comparire anche in /normativa)
                if voce["tipo"] == "atto" and esistente["tipo"] != "atto":
                    esistente["tipo"] = "atto"
                if voce["abstract"] and not esistente.get("abstract"):
                    esistente["abstract"] = voce["abstract"]
                continue
            voce["id"] = nid
            voce["raccolto"] = oggi
            per_id[nid] = voce
            nuove += 1

    # Abstract delle pagine MIM (non presenti negli elenchi): solo per le voci nuove.
    mancanti = [n for n in per_id.values() if n["fonte"] == "mim" and not n.get("abstract")
                and not n.get("abstract_tentato")]
    mancanti.sort(key=lambda n: n["data"], reverse=True)
    for notizia in mancanti[:MAX_ABSTRACT_MIM_PER_GIRO]:
        try:
            notizia["abstract"] = abstract_mim(notizia["url"])
        except Exception as errore:
            log.warning("Abstract non disponibile per %s: %s", notizia["url"], errore)
        notizia["abstract_tentato"] = True
        time.sleep(0.5)

    # Classificazione (sempre ricalcolata: così le regole nuove valgono anche per l'archivio).
    limite = (date.today() - timedelta(days=GIORNI_ARCHIVIO)).isoformat()
    notizie = []
    for notizia in per_id.values():
        if notizia["data"] < limite:
            continue
        notizia["sezioni"], notizia["superiori"] = classifica(
            notizia["titolo"], notizia.get("abstract", ""), notizia.get("categorie", []), notizia["tipo"]
        )
        if pertinente(notizia):
            notizie.append(notizia)

    notizie.sort(key=lambda n: (n["data"], n["raccolto"], n["titolo"]), reverse=True)
    archivio["notizie"] = notizie
    archivio["aggiornato"] = adesso
    salva_archivio(archivio)
    log.info("Archivio: %d notizie (%d nuove)", len(notizie), nuove)

    errori = [f for f, s in archivio["fonti"].items() if s.get("esito") != "ok"]
    if len(errori) == len(LETTORI):
        log.error("Nessuna fonte raggiungibile")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
