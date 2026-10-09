# Fase 0 — Ricognizione (2026-10-09)

Stato: **aggiornato dopo ispezione di rete (2026-10-09)**; vedi sezione 'Esito ispezione' in fondo. Fonti: ricerche web e lettura di robots.txt.
Non ho ispezionato le chiamate di rete reali dei siti (nessun test live da questo ambiente) e **non conosco ancora l'indirizzo dell'utente**: la copertura è quindi non verificata.

## Tabella di fattibilità

| Insegna | Come espone i prezzi | Requisiti | Copertura | Fattibilità | Metodo proposto |
|---|---|---|---|---|---|
| Esselunga | Endpoint JSON interno (POST paginati su spesaonline.esselunga.it; un dataset pubblico mostra richieste con offset e page-size 15). Il repo `limi7break/esselunga-scrape` esiste (MIT) ma contiene solo un notebook e dei file HAR, non una documentazione dell'API. | Selezione indirizzo/servizio lato sessione; login probabilmente non necessario per il catalogo (da verificare). | Lombardia, Piemonte, Toscana, Veneto, Emilia-Romagna (+ Lazio parziale). **Da verificare per l'indirizzo.** | **Alta** (tecnica) / **Media** (legale) | `httpx` sull'API JSON, endpoint derivati dagli HAR e da DevTools. |
| Todis | Catalogo e prezzi visibili senza login (sito ReStore); la consegna dipende dall'indirizzo inserito. | Inserimento indirizzo; login forse solo per carrello/ordini. | Centro-sud, prevalente Roma; consegna in giornata lun-sab, 5,90 € sotto 95 €, 2,90 € sopra (testo parzialmente illeggibile, da confermare). **Da verificare.** | **Media** | Prima cercare l'API JSON dietro il sito (DevTools); Playwright con `storage_state` solo se necessario. |
| Gros | Due canali: sito proprio gros.it ("Gros Spesa Online", app Digitelematica) e, da aprile 2026, amazon.it/Gros (10.000+ prodotti, Roma città, consegna gratis sopra 99 €, 4,90 € tra 50 e 98,99 €, fonti stampa). Il catalogo gros.it non è leggibile con un semplice fetch (probabile rendering JS): serve ispezione di rete. | Da analizzare (indirizzo/CAP). | Roma, entro il GRA; **via Giovanni Re 105 (00134) probabilmente coperta, da verificare**. | **Media** (gros.it) / **Bassa** (via Amazon, rimandato con Amazon Fresh) | Ispezione di rete di gros.it per trovare un endpoint JSON; altrimenti Playwright. Se non c'è catalogo interrogabile: "non supportato". |
| Amazon Fresh | HTML renderizzato, catalogo dipendente dal CAP e dal partner (da maggio 2026 anche Cortilia in 30+ province). | Account Amazon, CAP. | Milano, Monza-Brianza, Roma, Torino, Bologna e aree limitrofe; altrove via Cortilia. **Da verificare per CAP.** | **Bassa** | Playwright con sessione persistente. Alto rischio di captcha e di blocco account. |

## Robots.txt e ToS

- **spesaonline.esselunga.it**: `User-agent: *` blocca `/drive`, `/ordini`, `/account`, `/area-utenti`, **`/ricerca`**, `/auth`, i parametri `state=`/`freevisit=` e i PDF. Il catalogo via API non è citato esplicitamente, ma la ricerca testuale è disallowed. Preferire la navigazione per categoria all'endpoint di ricerca. I ToS di Esselunga non sono stati letti (la pagina provata dà 404), quindi **va fatta una verifica manuale**.
- **todisacasa.it**: robots.txt non recuperato (la risposta non lo conteneva). Da verificare a mano, insieme ai "Termini e Condizioni" linkati nel footer.
- **amazon.it**: robots.txt non vieta `/fresh` né `/alm`; blocca carrello, sign-in, e bot LLM come GPTBot, CCBot, ClaudeBot. I ToS Amazon vietano in genere l'accesso automatizzato. **Rischio di sospensione dell'account**: consiglio un account dedicato.
- **gros.it**: robots.txt: tutto aperto, tranne `/p/`, `/search` e URL che finiscono in `front|back|other_N`. Evitare `/search`. ToS non letti.

## Assunzioni e limiti

- Le informazioni di copertura vengono da articoli e comunicati, non da test sull'indirizzo reale.
- Le tariffe di consegna Todis sono dedotte da un testo parziale.
- Nessuna API è stata chiamata: gli endpoint Esselunga vanno confermati in Fase 2.

## Decisioni dell'utente (2026-10-09)

- Indirizzo: via Giovanni Re 105, 00134 Roma (solo in `config/user.yaml`, non committato con valori reali). Servizio: consegna a domicilio. Costi di consegna: non noti (si usano i valori pubblicati dai siti, da confermare).
- Gros: da analizzare. Amazon Fresh: rimandato. Esselunga per prima, navigazione per categoria.
- Nota: Esselunga online non copre Roma in modo pieno; la copertura di 00134 va verificata prima di investire nel connettore. Todis e Gros sono invece i candidati naturali per Roma.

## (Superato) Cosa serviva dall'utente

1. Indirizzo, CAP e città (andranno in `config/user.yaml`, non nei log o nei report).
2. Consegna a domicilio o ritiro (uguale per tutti).
3. Costi di consegna e ordine minimo per insegna, se già noti.
4. Decisione su **Gros** (analizzarlo o escluderlo) e su **Amazon Fresh** (account dedicato? lo includiamo, dato rischio alto e fattibilità bassa?).
5. Conferma che posso procedere con Esselunga come primo connettore, usando la navigazione per categoria invece di `/ricerca`.

## Esito ispezione di rete (2026-10-09)

| Insegna | Fatto | Esito per via Giovanni Re 105, 00134 Roma |
|---|---|---|
| **Gros** | API JSON `GET www.gros.it/ebsn/api/products?q=<testo>&page_size=N` (piattaforma EBSN), senza login. `price` = listino, `priceDisplay` = prezzo effettivo con promo, `description` = formato, `shortDescr` = marca. Il listino non dipende dall'indirizzo. | **Funziona.** Connettore completo (`connectors/gros.py`) con test su fixture. La copertura dell'indirizzo (entro il GRA) NON e' verificata: l'API di verifica (`user-address/check`) fa parte del flusso sessione/ordine e non e' stata usata. |
| **Todis** | Sito ASP.NET con HTML server-side e microdata schema.org; prezzi per punto vendita (`/spesa-consegna-domicilio/<codice>/`). Copertura via `api-fe.restore.shopping/tenants/v2/coverage/checkaddress/<via citta'>?tenant=tod`. | La API di copertura restituisce `[]` per l'indirizzo (restituisce invece un punto vendita per Via del Corso, Piazza Venezia, Via Laurentina). **Indirizzo non risulta coperto.** Il connettore verifica la copertura e dichiara l'insegna non disponibile; il parsing del catalogo non e' implementato perche' senza copertura i prezzi non sarebbero quelli del tuo indirizzo. |
| **Esselunga** | SPA Angular con API JSON sotto `/commerce/resources/`. `onboarding/postcode/check` risponde `SUPPORTED` per 00134 (ma anche a intermittenza con reset di connessione), `onboarding/street/suggestions` elenca "Via Giovanni Re - Roma". | Nel flusso del sito "VERIFICA INDIRIZZO" (CAP 00134 + "Via Giovanni Re 105") compare **"Indirizzo non trovato o non coperto dal servizio"**. Il connettore dichiara l'insegna non disponibile; il catalogo non e' implementato. |

### Assunzioni

- La copertura Gros per 00134 non e' verificata; il connettore assume Roma = coperta.
- I flag `courier/furgoncino` delle suggestions Esselunga risultano `false` ovunque (anche a Milano): non affidabili per decidere la copertura.
- I prezzi Gros sono considerati identici per tutta Roma (un solo listino "Gros" nelle risposte).
- Il filtro marca/formato del matcher e' deterministico; i casi dubbi finiscono in `review/ambigui.csv`.

## Aggiornamento 2026-10-09 (verifiche manuali dell'utente)

- **Esselunga: coperta** (verificato a mano dall'utente; il mio primo test automatico era sbagliato perche' la via va scelta dai suggerimenti, senza civico). Connettore completo e funzionante, senza account: `onboarding/street/suggestions` -> `services/available` -> `GET onboarding/street/<id>` -> `POST search/facet` (header `x-page-path: supermercato`). Il sito resetta a volte la connessione: il client riprova con backoff. Nota robots.txt: le pagine `/ricerca` sono vietate, il connettore usa solo l'endpoint JSON del catalogo (stessa chiamata della home), una ricerca per voce.
- **Gros: copre tutta Roma** (verificato dall'utente sul sito). Connettore funzionante.
- **Todis: non consegna** all'indirizzo (verificato dall'utente). Disabilitato in `config/user.yaml` (`enabled: false`); resta solo il controllo di copertura.
- **Conad: consegna** (verificato dall'utente su spesaonline.conad.it, prima fascia oggi 17-19). Ispezione iniziale: sito Adobe Experience Manager, catalogo servito come HTML (la ricerca mostra "5422 risultati"), indirizzo inserito con autocompletamento Google Places (`googleInputEntrypageLine1` + civico in `...Line2`). robots.txt non disponibile (risposta di errore). **Connettore non ancora implementato**: serve completare il flusso indirizzo -> servizio "Spesa a casa" e individuare dove arrivano i dati dei prodotti. Probabilmente Playwright.

## Conad: esito (2026-10-09) — non supportato con questo metodo

- Flusso sul sito: indirizzo (Google Places) -> modale "Come vuoi fare la spesa?" -> "Spesa a casa / Seleziona" -> `POST /api/ecommerce/it-it.set-ecaccess.json` (imposta il punto vendita).
- Il passaggio `set-ecaccess` richiede un `protectionToken` generato dallo script di protezione del sito (`POST /api/common/protection.json?step=zero`, azione `entryaccess`). Con browser automatico la protezione risponde **403 `WEB:PROTECTION_ERROR` "FE BOT Blocked"**.
- Senza punto vendita impostato il catalogo non da' prezzi (`basePrice: 0.0`, ricerca con 0 risultati).
- I vincoli del progetto escludono l'aggiramento di protezioni anti-bot, quindi **il connettore Conad non viene implementato**. L'API pubblica `stores.json` (elenco punti vendita per coordinate) funziona ma non basta a ottenere i prezzi.
- Alternative possibili: volantino/offerte pubbliche Conad (solo promozioni, non il listino), un aggregatore (Everli, a pagamento o con ToS da verificare), oppure consultazione manuale.
