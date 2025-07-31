# workers-api (staging)

**Flujo de trabajo**
- Edita en VS Code → `git add/commit/push` (rama `staging`).
- cPanel → Git Version Control → **Deploy HEAD Commit**.
- cPanel → Setup Python App → **Restart** (si cambian dependencias).

**Endpoints**
- `GET /` → `{"ok": true, "up": true, "build": "<sha>"}`
- `GET /health` → estado + `build`
- `GET /openapi.yml` → especificación para conectar desde GPT (Actions)
- `POST /v1/command` → `{ action, args? }` (header `X-Api-Key` requerido)

**Requisitos**
- Python 3.7 (hosting)
- Flask==2.2.5 / Werkzeug==2.2.3

**Despliegue**
- `.cpanel.yml` preserva/reescribe `.htaccess` y fuerza restart.
- El `requirements.txt` se lee desde el repo (no se copia al docroot).

**Seguridad**
- Cambia la variable `API_KEY` en cPanel (App → Environment variables).
