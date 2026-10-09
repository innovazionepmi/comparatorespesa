# Installazione su VPS con n8n in Docker

Architettura: n8n (Schedule) -> `POST http://spesa:8080/run` -> container `spesa` esegue la pipeline
e risponde con un JSON (`status`, `summary`, `report_md`, `failures`) -> n8n inoltra il riepilogo
su Telegram e manda un avviso se `status` non e' `ok` o se la chiamata fallisce.
Il container `spesa` non pubblica porte: lo raggiunge solo n8n, sulla stessa rete Docker.

## 1. Sul VPS

```bash
git clone https://github.com/innovazionepmi/comparatorespesa.git && cd comparatorespesa
git checkout claude/eloquent-goodall-qkg3wy          # finche' non viene unito in main
cp config/user.example.yaml config/user.yaml          # poi compila indirizzo e costi di consegna
docker network ls                                     # trova la rete usata da n8n (es. n8n_default)
export SPESA_TOKEN=$(openssl rand -hex 24)            # segreto condiviso con n8n: annotalo
export N8N_NETWORK=<nome rete di n8n>
docker compose -f deploy/docker-compose.spesa.yml up -d --build
docker exec <container-n8n> wget -qO- http://spesa:8080/health    # deve rispondere {"ok": true}
```

`config/user.yaml` (indirizzo di casa) resta solo sul VPS: e' ignorato da git e montato in sola lettura.
Storico prezzi, report e casi ambigui stanno nei volumi Docker `spesa-data` e `spesa-review`.

## 2. In n8n

1. Crea una credenziale **Header Auth** con nome `X-Token` e valore uguale a `SPESA_TOKEN`.
2. Workflow: *Schedule Trigger* (una volta al giorno) -> *HTTP Request* `POST http://spesa:8080/run`
   (credenziale sopra, timeout 600000 ms, "Never error" attivo per leggere anche gli esiti 4xx/5xx)
   -> *If* `status == "ok"` -> *Telegram* (campo `summary`); ramo falso -> *Telegram* con l'avviso
   (`failures`, oppure "run non riuscita" se manca la risposta).
3. Heartbeat: l'avviso sul ramo di errore copre i fallimenti; per coprire anche "n8n spento",
   usa un monitor esterno (es. Healthchecks.io) chiamato a fine run riuscita.

## Note

- Una run dura in genere meno di 2-3 minuti (ritardi casuali di 2-6 s tra richieste, per cortesia verso i siti).
- Una sola run alla volta: una seconda chiamata mentre e' in corso riceve `409`.
- Per aggiornare: `git pull && docker compose -f deploy/docker-compose.spesa.yml up -d --build`.
