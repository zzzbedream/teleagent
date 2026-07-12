# 🚂 Despliegue en Railway — TeleAgent

Guía paso a paso para dejar TeleAgent **funcionando 24/7 sin depender de tu PC**.
Todo se aloja en Railway: los 3 servicios Python, PostgreSQL, ChromaDB y la landing.

> **Antes de empezar necesitas:**
> - El repo ya publicado en GitHub (`zzzbedream/teleagent`).
> - Cuenta en [railway.app](https://railway.app) (login con GitHub).
> - Tu `DISCORD_TOKEN`, `DEEPSEEK_API_KEY` y la URL de invitación del bot.
> - El contrato ya está desplegado en Fuji: `0x78cce8C167583bf358B3EA1c9C409e13A7Da691a`.

---

## Arquitectura de servicios en Railway

Vas a crear **6 servicios** dentro de un mismo proyecto de Railway, todos desde el mismo repo:

| # | Servicio | Tipo | Dockerfile Path | Puerto público |
|---|----------|------|-----------------|----------------|
| 1 | **postgres** | Base de datos (plugin) | — | no |
| 2 | **chromadb** | Docker Image `chromadb/chroma:latest` | — | no |
| 3 | **backend** | Dockerfile del repo | `backend/Dockerfile` | sí |
| 4 | **bot** | Dockerfile del repo | `bot/Dockerfile` | no |
| 5 | **indexer** | Dockerfile del repo | `indexer/Dockerfile` | no |
| 6 | **landing** | Dockerfile del repo | `frontend/Dockerfile` | sí |

En los 4 servicios que salen del repo, deja **Root Directory = `/`** (la raíz) y solo cambia el **Dockerfile Path**. El contexto de build es la raíz del repo (así comparten el módulo `database/`).

> 🛑 **PASO OBLIGATORIO EN CADA SERVICIO DEL REPO — no lo saltes:**
> Railway por defecto usa su autodetector (**Railpack**) y **fallará** con un error tipo
> *"Railpack could not determine how to build the app"*. Tienes que decirle que use tu Dockerfile:
>
> Servicio → **Settings** → **Build** → campo **Dockerfile Path** → escribe la ruta
> (`backend/Dockerfile`, `bot/Dockerfile`, `indexer/Dockerfile` o `frontend/Dockerfile`) → **Redeploy**.
>
> Con eso el builder cambia de Railpack a Docker. **Root Directory** queda vacío / en `/`.

---

## Paso 1 — Crear el proyecto y la base de datos

1. En Railway: **New Project** → **Deploy from GitHub repo** → elige `zzzbedream/teleagent`.
   - Railway intentará detectar un servicio. Si crea uno automático, lo configuramos como **backend** en el Paso 3 (o bórralo y créalos manualmente).
2. Dentro del proyecto: **+ New** → **Database** → **Add PostgreSQL**.
   - Railway crea el servicio `Postgres` y expone variables (`DATABASE_URL`, `PGHOST`, etc.).

## Paso 2 — Añadir ChromaDB

1. **+ New** → **Empty Service** (o **Docker Image**) → imagen: `chromadb/chroma:latest`.
2. Renómbralo a **chromadb**.
3. En **Settings → Networking**: no necesita dominio público (lo consume el backend por red privada).
4. En **Settings → Volumes**: añade un volumen montado en `/chroma/chroma` (para que el corpus persista).
5. Este servicio escucha en el puerto **8000** internamente.

## Paso 3 — Servicio backend (RAG)

1. **+ New** → **GitHub Repo** → `zzzbedream/teleagent` (o usa el servicio auto-creado).
2. **Settings → Build**:
   - **Dockerfile Path**: `backend/Dockerfile`
   - **Root Directory**: `/`
3. **Settings → Networking**: **Generate Domain** (esto te da la URL pública, ej. `https://backend-production-xxxx.up.railway.app`). Anótala.
4. **Variables** (pestaña Variables del servicio):

   ```
   DEEPSEEK_API_KEY = tu_api_key_de_deepseek
   DATABASE_URL     = ${{Postgres.DATABASE_URL}}
   CHROMA_HOST      = chromadb.railway.internal
   CHROMA_PORT      = 8000
   ALLOWED_ORIGINS  = *
   ```

   > `${{Postgres.DATABASE_URL}}` es una **referencia** a la variable del servicio Postgres (Railway la resuelve sola; el código la convierte a asyncpg automáticamente).
   > `chromadb.railway.internal` es el hostname de red privada del servicio chromadb (ajústalo si le pusiste otro nombre).

5. Deja que despliegue. El backend crea las tablas de la base de datos **solo** al arrancar.

> ⚠️ **Memoria:** el backend carga un modelo de embeddings (torch). Necesita un plan con **≥ 1 GB de RAM** (idealmente 2 GB). En el plan gratuito puede quedarse corto; si ves que se reinicia por OOM, sube el plan del servicio backend.

## Paso 4 — Sembrar el corpus (una sola vez)

ChromaDB arranca vacío. Hay que cargar la documentación oficial **una vez**:

1. Ve al servicio **backend** → pestaña de terminal/consola (o usa `railway run` desde tu PC con la CLI).
2. Ejecuta:

   ```bash
   python scripts/fetch_repos.py && python -m app.ingest
   ```

   Esto clona ACPs + Builders Hub + Teleporter y los indexa en ChromaDB. Puede tardar varios minutos.

   > Alternativa desde tu PC (sin la consola de Railway): instala la [CLI de Railway](https://docs.railway.app/guides/cli), corre `railway link`, luego `railway run --service backend python scripts/fetch_repos.py` y `railway run --service backend python -m app.ingest`.

## Paso 5 — Servicio bot (Discord)

1. **+ New** → **GitHub Repo** → mismo repo.
2. **Settings → Build → Dockerfile Path**: `bot/Dockerfile`, Root Directory `/`.
3. **Variables**:

   ```
   DISCORD_TOKEN = tu_token_del_bot
   DATABASE_URL  = ${{Postgres.DATABASE_URL}}
   FASTAPI_URL   = https://TU-BACKEND.up.railway.app/query
   ```

   > `FASTAPI_URL` = la URL pública del backend del Paso 3, **con `/query` al final**.

## Paso 6 — Servicio indexer (eventos on-chain)

1. **+ New** → **GitHub Repo** → mismo repo.
2. **Settings → Build → Dockerfile Path**: `indexer/Dockerfile`, Root Directory `/`.
3. **Variables**:

   ```
   WSS_URL          = wss://api.avax-test.network/ext/bc/C/ws
   DATABASE_URL     = ${{Postgres.DATABASE_URL}}
   CONTRACT_ADDRESS = 0x78cce8C167583bf358B3EA1c9C409e13A7Da691a
   ```

## Paso 7 — Servicio landing (marketing + demo)

1. **+ New** → **GitHub Repo** → mismo repo.
2. **Settings → Build → Dockerfile Path**: `frontend/Dockerfile`, Root Directory `/`.
3. **Settings → Networking**: **Generate Domain** (esta es la URL que compartes con los jueces).
4. **Variables**:

   ```
   BACKEND_URL       = https://TU-BACKEND.up.railway.app
   DISCORD_INVITE_URL = https://discord.com/oauth2/authorize?client_id=...&scope=bot+applications.commands&permissions=2048
   GITHUB_URL        = https://github.com/zzzbedream/teleagent
   CONTRACT_ADDRESS  = 0x78cce8C167583bf358B3EA1c9C409e13A7Da691a
   ```

   > `BACKEND_URL` **sin** `/query` (el JS lo añade). La demo de la landing llama a este backend.
   > Una vez tengas la URL de la landing, vuelve al **backend** y cambia `ALLOWED_ORIGINS` de `*` a esa URL exacta (más seguro).

---

## ✅ Prueba de producción (checklist final)

1. Abre la **URL de la landing** → debe cargar, y la caja de demo debe responder una pregunta (esto valida landing + backend + DeepSeek + ChromaDB).
2. En **Discord**, con el bot invitado a tu servidor: `/link_wallet 0xTuWallet`.
3. Envía 0.1 AVAX al contrato en Fuji (desde tu wallet o con `cast send`).
4. Mira los **logs del indexer** en Railway → debe aparecer `Credited ... wei`.
5. En Discord: `/ask ¿Qué cambió con la actualización Etna?` → respuesta con fuentes y saldo descontado.

Si los 5 pasos pasan: **está listo para el grant**. 🎉

---

## Notas y solución de problemas

- **Error `Railpack could not determine how to build the app`:** ese servicio no tiene el **Dockerfile Path** configurado. Ve a Settings → Build → Dockerfile Path y pon la ruta correcta (`backend/Dockerfile`, etc.). Es el error #1 más común.
- **¿Cuándo se crea la base de datos?** El **servidor** PostgreSQL lo creas tú al añadir el plugin (Paso 1, antes de todo). Las **tablas** (`users`) se crean **solas** cuando el backend arranca por primera vez (no hay paso manual en producción). Orden: Postgres → backend deploya → tablas listas → bot/indexer las usan.
- **La demo de la landing dice "backend no configurado":** falta `BACKEND_URL` en el servicio landing.
- **CORS bloqueado en el navegador:** pon la URL de la landing en `ALLOWED_ORIGINS` del backend.
- **El indexer no acredita:** revisa que `CONTRACT_ADDRESS` esté bien y que la wallet esté vinculada con `/link_wallet` **antes** de pagar.
- **Backend se reinicia (OOM):** sube la RAM del servicio backend (el modelo de embeddings pesa).
- **El bot no muestra comandos:** revisa `DISCORD_TOKEN` y que el bot fue invitado con el scope `applications.commands`.
- **Red privada:** los hostnames internos son `<nombre-del-servicio>.railway.internal`. Ajusta `CHROMA_HOST` si nombraste distinto el servicio.
