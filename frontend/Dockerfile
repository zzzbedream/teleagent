# Landing de marketing (nginx estático). Build context = repo root.
FROM nginx:alpine

# Defaults; Railway los sobreescribe en tiempo de ejecución.
ENV PORT=80 \
    BACKEND_URL="" \
    DISCORD_INVITE_URL="" \
    GITHUB_URL="" \
    CONTRACT_ADDRESS=""

# default.conf.template -> /etc/nginx/conf.d/default.conf (envsubst de ${PORT} al arrancar)
COPY frontend/default.conf.template /etc/nginx/templates/default.conf.template

COPY frontend/public/ /usr/share/nginx/html/

# Genera config.js desde el template con las envs, antes de arrancar nginx.
COPY frontend/inject-config.sh /docker-entrypoint.d/40-inject-config.sh
RUN chmod +x /docker-entrypoint.d/40-inject-config.sh
