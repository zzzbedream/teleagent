#!/bin/sh
# Inyecta las variables de entorno de Railway en config.js (leído por el navegador).
set -e
envsubst '${BACKEND_URL} ${DISCORD_INVITE_URL} ${GITHUB_URL} ${CONTRACT_ADDRESS}' \
  < /usr/share/nginx/html/config.template.js > /usr/share/nginx/html/config.js
