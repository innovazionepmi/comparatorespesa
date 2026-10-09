# Fase 0 — Ricognizione (2026-10-09)

Stato: **bozza da confermare**. Fonti: ricerche web e lettura di robots.txt.
Non ho ispezionato le chiamate di rete reali dei siti (nessun test live da questo ambiente) e **non conosco ancora l'indirizzo dell'utente**: la copertura è quindi non verificata.

## Tabella di fattibilità

| Insegna | Come espone i prezzi | Requisiti | Copertura | Fattibilità | Metodo proposto |
|---|---|---|---|---|---|
| Esselunga | Endpoint JSON interno (POST paginati su spesaonline.esselunga.it; un dataset pubblico mostra richieste con offset e page-size 15). Il repo `limi7break/esselunga-scrape` esiste (MIT) ma contiene solo un notebook e dei file HAR, non una documentazione dell'API. | Selezione indirizzo/servizio lato sessione; login probabilmente non necessario per il catalogo (da verificare). | Lombardia, Piemonte, Toscana, Veneto, Emilia-Romagna (+ Lazio parziale). **Da verificare per l'indirizzo.** | **Alta** (tecnica) / **Media** (legale) | `httpx` sull'API JSON, endpoint derivati dagli HAR e da DevTools. |
| Todis | Catalogo e prezzi visibili senza login (sito ReStore); la consegna dipende dall'indirizzo inserito. | Inserimento indirizzo; login forse solo per carrello/ordini. | Centro-sud, prevalente Roma; consegna in giornata lun-sab, 5,90 € sotto 95 €, 2,90 € sopra (testo parzialmente illeggibile, da confermare). **Da verificare.** | **Media** | Prima cercare l'API JSON dietro il sito (DevTools); Playwright con `storage_state` solo se necessario. |
| Gros | Esiste "Gros Spesa Online" (app di Digitelematica; acquisti su gros.it), servizio di Gros Maestri del Fresco. | Da analizzare. | Entro il GRA di Roma. | **Media-Bassa** (non ispezionato) | Da analizzare dopo la tua conferma. Se non c'è catalogo interrogabile: "non supportato". |
| Amazon Fresh | HTML renderizzato, catalogo dipendente dal CAP e dal partner (da maggio 2026 anche Cortilia in 30+ province). | Account Amazon, CAP. | Milano, Monza-Brianza, Roma, Torino, Bologna e aree limitrofe; altrove via Cortilia. **Da verificare per CAP.** | **Bassa** | Playwright con sessione persistente. Alto rischio di captcha e di blocco account. |

## Robots.txt e ToS

- **spesaonline.esselunga.it**: `User-agent: *` blocca `/drive`, `/ordini`, `/account`, `/area-utenti`, **`/ricerca`**, `/auth`, i parametri `state=`/`freevisit=` e i PDF. Il catalogo via API non è citato esplicitamente, ma la ricerca testuale è disallowed. Preferire la navigazione per categoria all'endpoint di ricerca. I ToS di Esselunga non sono stati letti (la pagina provata dà 404), quindi **va fatta una verifica manuale**.
- **todisacasa.it**: robots.txt non recuperato (la risposta non lo conteneva). Da verificare a mano, insieme ai "Termini e Condizioni" linkati nel footer.
- **amazon.it**: robots.txt non vieta `/fresh` né `/alm`; blocca carrello, sign-in, e bot LLM come GPTBot, CCBot, ClaudeBot. I ToS Amazon vietano in genere l'accesso automatizzato. **Rischio di sospensione dell'account**: consiglio un account dedicato.
- **gros.it**: non letto.

## Assunzioni e limiti

- Le informazioni di copertura vengono da articoli e comunicati, non da test sull'indirizzo reale.
- Le tariffe di consegna Todis sono dedotte da un testo parziale.
- Nessuna API è stata chiamata: gli endpoint Esselunga vanno confermati in Fase 2.

## Cosa mi serve da te per procedere

1. Indirizzo, CAP e città (andranno in `config/user.yaml`, non nei log o nei report).
2. Consegna a domicilio o ritiro (uguale per tutti).
3. Costi di consegna e ordine minimo per insegna, se già noti.
4. Decisione su **Gros** (analizzarlo o escluderlo) e su **Amazon Fresh** (account dedicato? lo includiamo, dato rischio alto e fattibilità bassa?).
5. Conferma che posso procedere con Esselunga come primo connettore, usando la navigazione per categoria invece di `/ricerca`.
