/* Bussola Scuola: ricerca e filtri sull'archivio delle notizie.
   Senza JavaScript la pagina mostra comunque le notizie più recenti. */
(function () {
  "use strict";

  var CONFIG = window.BUSSOLA || {};
  var PER_PAGINA = 30;
  var MESI = ["gennaio", "febbraio", "marzo", "aprile", "maggio", "giugno", "luglio",
    "agosto", "settembre", "ottobre", "novembre", "dicembre"];

  var modulo = document.getElementById("filtri");
  var elenco = document.getElementById("elenco-notizie");
  var conteggio = document.getElementById("conteggio");
  var altre = document.getElementById("mostra-altre");
  var sezioneNotizie = document.getElementById("notizie");
  if (!modulo || !elenco || !window.fetch) return;

  var campi = {
    q: document.getElementById("filtro-testo"),
    sezione: document.getElementById("filtro-sezione"),
    fonte: document.getElementById("filtro-fonte"),
    superiori: document.getElementById("filtro-superiori"),
    ufficiali: document.getElementById("filtro-ufficiali")
  };
  var linkSezioni = document.querySelectorAll(".elenco-sezioni a[data-sezione]");

  var notizie = [];
  var filtrate = [];
  var mostrate = 0;
  var attesaRicerca = null;

  function normalizza(testo) {
    return (testo || "").normalize("NFD").replace(/[̀-ͯ]/g, "")
      .toLowerCase().replace(/[’']/g, " ");
  }

  function dataItaliana(iso) {
    var p = iso.split("-");
    return parseInt(p[2], 10) + " " + MESI[parseInt(p[1], 10) - 1] + " " + p[0];
  }

  function crea(tag, classe, testo) {
    var el = document.createElement(tag);
    if (classe) el.className = classe;
    if (testo) el.textContent = testo;
    return el;
  }

  function scheda(n) {
    var fonte = CONFIG.fonti[n.fonte] || { breve: n.fonte, ufficiale: false };
    var articolo = crea("article", "scheda" + (fonte.ufficiale ? " scheda-ufficiale" : ""));

    var meta = crea("p", "scheda-meta");
    var etichetta = crea("span", "etichetta-fonte" + (fonte.ufficiale ? " ufficiale" : ""), fonte.breve);
    if (fonte.ufficiale) etichetta.appendChild(crea("span", "sr-only", " (fonte ufficiale)"));
    var tempo = crea("time", null, dataItaliana(n.data));
    tempo.setAttribute("datetime", n.data);
    meta.appendChild(etichetta);
    meta.appendChild(document.createTextNode(" "));
    meta.appendChild(tempo);
    articolo.appendChild(meta);

    var titolo = crea("h3", "scheda-titolo");
    var link = crea("a", null, n.titolo);
    link.href = n.url;
    link.rel = "noopener";
    link.appendChild(crea("span", "sr-only", " (apre il sito " + fonte.breve + ")"));
    titolo.appendChild(link);
    articolo.appendChild(titolo);

    if (n.abstract) articolo.appendChild(crea("p", "scheda-abstract", n.abstract));

    var tag = crea("ul", "scheda-tag");
    tag.setAttribute("aria-label", "Sezioni");
    if (n.superiori) tag.appendChild(crea("li", "tag-superiori", "Scuola superiore"));
    n.sezioni.forEach(function (s) { tag.appendChild(crea("li", null, CONFIG.sezioni[s] || s)); });
    articolo.appendChild(tag);
    return articolo;
  }

  function leggiFiltri() {
    return {
      q: campi.q.value.trim(),
      sezione: campi.sezione.value,
      fonte: campi.fonte.value,
      superiori: campi.superiori.checked,
      ufficiali: campi.ufficiali.checked
    };
  }

  function applicaFiltri() {
    var f = leggiFiltri();
    var parole = normalizza(f.q).split(/\s+/).filter(Boolean);
    filtrate = notizie.filter(function (n) {
      if (f.sezione && n.sezioni.indexOf(f.sezione) === -1) return false;
      if (f.fonte && n.fonte !== f.fonte) return false;
      if (f.superiori && !n.superiori) return false;
      if (f.ufficiali && !(CONFIG.fonti[n.fonte] || {}).ufficiale) return false;
      for (var i = 0; i < parole.length; i++) {
        if (n._testo.indexOf(parole[i]) === -1) return false;
      }
      return true;
    });
    elenco.textContent = "";
    mostrate = 0;
    mostraAltre(false);
    aggiornaConteggio(f);
    aggiornaUrl(f);
    aggiornaSezioniAttive(f.sezione);
  }

  function mostraAltre(spostaFuoco) {
    var inizio = mostrate;
    var fine = Math.min(filtrate.length, mostrate + PER_PAGINA);
    var frammento = document.createDocumentFragment();
    for (var i = inizio; i < fine; i++) frammento.appendChild(scheda(filtrate[i]));
    elenco.appendChild(frammento);
    mostrate = fine;

    if (!filtrate.length) {
      elenco.appendChild(crea("p", "vuoto", "Nessuna notizia corrisponde ai filtri scelti. Prova a togliere qualche filtro."));
    }
    altre.hidden = mostrate >= filtrate.length;
    if (!altre.hidden) {
      altre.textContent = "Mostra altre notizie (" + (filtrate.length - mostrate) + " rimanenti)";
    }
    if (spostaFuoco && elenco.children[inizio]) {
      var primoLink = elenco.children[inizio].querySelector("a");
      if (primoLink) primoLink.focus();
    }
  }

  function aggiornaConteggio(f) {
    var totale = filtrate.length;
    var filtrato = f.q || f.sezione || f.fonte || f.superiori || f.ufficiali;
    var testo;
    if (!filtrato) testo = totale + " notizie in archivio, dalla più recente.";
    else if (totale === 1) testo = "1 notizia trovata.";
    else testo = totale + " notizie trovate.";
    conteggio.textContent = testo;
  }

  function aggiornaUrl(f) {
    var parametri = new URLSearchParams();
    if (f.q) parametri.set("q", f.q);
    if (f.sezione) parametri.set("sezione", f.sezione);
    if (f.fonte) parametri.set("fonte", f.fonte);
    if (f.superiori) parametri.set("superiori", "1");
    if (f.ufficiali) parametri.set("ufficiali", "1");
    var query = parametri.toString();
    var nuovo = location.pathname + (query ? "?" + query : "") + location.hash;
    history.replaceState(null, "", nuovo);
  }

  function aggiornaSezioniAttive(sezione) {
    Array.prototype.forEach.call(linkSezioni, function (a) {
      if (a.getAttribute("data-sezione") === sezione) a.setAttribute("aria-current", "true");
      else a.removeAttribute("aria-current");
    });
  }

  function impostaDaUrl() {
    var p = new URLSearchParams(location.search);
    campi.q.value = p.get("q") || "";
    if (p.get("sezione")) campi.sezione.value = p.get("sezione");
    if (p.get("fonte")) campi.fonte.value = p.get("fonte");
    campi.superiori.checked = p.get("superiori") === "1";
    campi.ufficiali.checked = p.get("ufficiali") === "1";
  }

  function vaiAlleNotizie() {
    sezioneNotizie.scrollIntoView({ block: "start" });
    sezioneNotizie.focus({ preventScroll: true });
  }

  // Eventi
  campi.q.addEventListener("input", function () {
    clearTimeout(attesaRicerca);
    attesaRicerca = setTimeout(applicaFiltri, 250);
  });
  [campi.sezione, campi.fonte, campi.superiori, campi.ufficiali].forEach(function (c) {
    c.addEventListener("change", applicaFiltri);
  });
  modulo.addEventListener("submit", function (e) { e.preventDefault(); applicaFiltri(); });
  modulo.addEventListener("reset", function () { setTimeout(applicaFiltri, 0); });
  altre.addEventListener("click", function () { mostraAltre(true); });

  Array.prototype.forEach.call(linkSezioni, function (a) {
    a.addEventListener("click", function (e) {
      if (!notizie.length) return; // dati non caricati: segue il link normale
      e.preventDefault();
      campi.sezione.value = a.getAttribute("data-sezione");
      applicaFiltri();
      vaiAlleNotizie();
    });
  });

  // Avvio
  modulo.hidden = false;
  impostaDaUrl();
  fetch(CONFIG.dati, { cache: "no-cache" })
    .then(function (r) {
      if (!r.ok) throw new Error("HTTP " + r.status);
      return r.json();
    })
    .then(function (dati) {
      notizie = dati.map(function (n) {
        n._testo = normalizza(n.titolo + " " + (n.abstract || ""));
        return n;
      });
      applicaFiltri();
      if (location.search && location.hash === "#notizie") vaiAlleNotizie();
    })
    .catch(function () {
      modulo.hidden = true;
      conteggio.textContent = "Non è stato possibile caricare l'archivio completo: qui sotto trovi le notizie più recenti.";
    });
})();
