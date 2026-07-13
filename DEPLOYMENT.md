# 🚂 Despliegue en Railway — TeleAgent

Guía para dejar TeleAgent **funcionando 24/7 sin depender de tu PC**. Son **5 servicios**.
El backend es liviano (embeddings ONNX, sin PyTorch) y trae **ChromaDB embebido** en un volumen,
así que no hay un servicio de base vectorial aparte.

Despliegue en **dos fases**: primero **el cerebro** (backend + Postgres, y se verifica que tiene
conocimiento), y solo entonces **las caras** (landing, bot, indexer).

> **Por qué el cerebro primero:** el conocimiento del bot NO viene pre-cargado. Es documentación
> oficial (ACPs + Builders Hub + Teleporter, ~320+ docs) que se descarga y se convierte en
> embeddings dentro de ChromaDB en un paso único (el "seed"). Antes de sembrar, el cerebro está
> vacío y el bot responde "no tengo información" a todo.

**Datos que reusarás:**
- Repo: `zzzbedream/teleagent`
- Contrato Fuji: `0x78cce8C167583bf358B3EA1c9C409e13A7Da691a`
- Necesitas: `DEEPSEEK_API_KEY`, `DISCORD_TOKEN`, y el `DISCORD_INVITE_URL` (Fase B).
- La URL pública del backend (se genera en A2; se reusa en landing y bot).

> 🛑 **Cada servicio que sale del repo** necesita, en **Settings → Config-as-code → Railway
> Config File**, la ruta a su `railway.json` (`backend/railway.json`, etc.). Sin eso Railway usa
> Railpack y falla. **Root Directory** vacío / en `/`.

---

## Reset (empezar limpio)
Proyecto viejo → **Settings → Danger → Delete Project**. Luego **New Project → Empty Project**.

---

# FASE A — El cerebro (desplegar y VERIFICAR)

## A1. PostgreSQL
En el proyecto: **`Ctrl`+`K`** → `Postgres` → **Add PostgreSQL**. Sin más config.

## A2. Backend (RAG + ChromaDB embebido)
1. **`+ New` → GitHub Repo** → `teleagent`.
2. **Settings → Config-as-code → Railway Config File** = `backend/railway.json`.
3. **Settings → Volumes → Add Volume**, punto de montaje **`/data`** (aquí persiste el cerebro).
4. **Networking → Generate Domain** → **copia la URL**.
5. **Variables:**
   ```
   DEEPSEEK_API_KEY = tu_api_key_de_deepseek
   DATABASE_URL     = ${{Postgres.DATABASE_URL}}
   CHROMA_PATH      = /data/chroma
   ALLOWED_ORIGINS  = *
   ```
6. Verifica que arranca: `https://TU-BACKEND.up.railway.app/health` → `{"status":"ok","documents":0}`
   (0 es correcto por ahora: aún no sembramos.)

## A3. Sembrar el corpus (una sola vez)
En el servicio **backend** → Terminal/Shell (o CLI de Railway con `railway run`):
```
python scripts/fetch_repos.py && python -m app.ingest
```
Descarga la documentación oficial y la indexa en el volumen. Tarda varios minutos.

## A4. Reiniciar el backend
Railway → servicio backend → **⋮ → Restart**. Así abre el cerebro recién sembrado con estado limpio.

## A5. 🚦 Filtro de verificación (NO sigas si falla)
- `https://TU-BACKEND.up.railway.app/health` → **`"documents": ~320`** (no `0`).
  - `documents: 0` → el seed no cargó; repite A3 y revisa sus logs.
- **Solo si `documents` > 0, pasa a la Fase B.**

---

# FASE B — Las caras (solo tras pasar A5)

## B0. Link de invitación del bot (Discord Developer Portal)
App → **OAuth2 → URL Generator** → scopes **`bot`** + **`applications.commands`**; permisos
**Send Messages** + **Use Slash Commands**. Copia la URL → `DISCORD_INVITE_URL`. Invita el bot a tu server.

## B1. Landing (marketing + demo)
1. **Railway Config File** = `frontend/railway.json`. **Generate Domain** → URL para los jueces.
2. **Variables:**
   ```
   BACKEND_URL        = https://TU-BACKEND.up.railway.app      (SIN /query ni /health)
   DISCORD_INVITE_URL = (el link de B0)
   GITHUB_URL         = https://github.com/zzzbedream/teleagent
   CONTRACT_ADDRESS   = 0x78cce8C167583bf358B3EA1c9C409e13A7Da691a
   ```
3. (Recomendado) En el backend, cambia `ALLOWED_ORIGINS = *` por la URL de la landing.

## B2. Bot (Discord)
1. **Railway Config File** = `bot/railway.json`. Sin dominio.
2. **Variables:**
   ```
   DISCORD_TOKEN = tu_token_del_bot
   DATABASE_URL  = ${{Postgres.DATABASE_URL}}
   FASTAPI_URL   = https://TU-BACKEND.up.railway.app/query     (CON /query)
   ```

## B3. Indexer (eventos on-chain)
1. **Railway Config File** = `indexer/railway.json`. Sin dominio.
2. **Variables:**
   ```
   WSS_URL          = wss://api.avax-test.network/ext/bc/C/ws
   DATABASE_URL     = ${{Postgres.DATABASE_URL}}
   CONTRACT_ADDRESS = 0x78cce8C167583bf358B3EA1c9C409e13A7Da691a
   ```

---

## ✅ Verificación end-to-end final
1. Abre la **URL de la landing** → carga y la demo responde una pregunta.
2. En **Discord**: `/link_wallet 0xTuWallet`.
3. Envía 0.1 AVAX al contrato en Fuji.
4. Logs del **indexer** → `Credited ... wei`.
5. En Discord: `/ask ...` → respuesta con fuentes y saldo descontado.

## Tabla resumen

| Fase | Servicio | Railway Config File | Dominio | Volumen | Variables clave |
|---|---|---|---|---|---|
| A1 | Postgres | — (plugin) | no | — | — |
| A2 | backend | `backend/railway.json` | **sí** | **`/data`** | DEEPSEEK_API_KEY, DATABASE_URL, CHROMA_PATH, ALLOWED_ORIGINS |
| A3-A5 | (seed + restart + verificar) | — | — | — | `/health` → documents > 0 |
| B1 | landing | `frontend/railway.json` | **sí** | — | BACKEND_URL, DISCORD_INVITE_URL, GITHUB_URL, CONTRACT_ADDRESS |
| B2 | bot | `bot/railway.json` | no | — | DISCORD_TOKEN, DATABASE_URL, FASTAPI_URL |
| B3 | indexer | `indexer/railway.json` | no | — | WSS_URL, DATABASE_URL, CONTRACT_ADDRESS |

## Solución de problemas
- **`Railpack could not determine how to build`:** falta el Railway Config File del servicio.
- **"Application failed to respond":** el backend se cayó al arrancar. Con la imagen liviana (sin
  torch) ya no debería pasar por memoria; si ocurre, mira los Deploy Logs del backend.
- **`{"detail":"Not Found"}` en `/`:** normal en el backend. Usa `/health`.
- **`/health` da `documents: 0`:** el corpus no se sembró (repite A3 + A4).
- **La demo de la landing no responde:** falta `BACKEND_URL`, o CORS (pon la URL de la landing en `ALLOWED_ORIGINS`).
- **El bot no muestra comandos:** revisa `DISCORD_TOKEN` y que se invitó con `applications.commands`.
