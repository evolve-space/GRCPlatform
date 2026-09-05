# Imagen de producción del frontend + reverse proxy, en una sola imagen
# nginx: sirve los assets estáticos ya compilados de React y hace de
# reverse proxy hacia el backend. Ver docs/DEPLOYMENT.md.
#
# El contexto de build de esta imagen es la RAÍZ del repositorio (no
# nginx/), porque necesita el código fuente de frontend/ para compilarlo.

FROM node:20-alpine AS frontend-build

WORKDIR /app

COPY frontend/package.json ./
RUN npm install

COPY frontend/ .

# En producción la SPA se sirve desde el mismo origen que la API (a través
# de este mismo nginx, que hace de proxy hacia el backend bajo /api/v1/...),
# así que basta con una URL vacía: cada llamada del frontend ya incluye el
# prefijo completo "/api/v1/..." (ver frontend/src/lib/api.ts), y con
# baseURL="" se resuelve relativa al origen actual — sin necesitar fijar un
# dominio en tiempo de build.
ENV VITE_API_URL=

RUN npm run build

FROM nginx:1.27-alpine

COPY --from=frontend-build /app/dist /usr/share/nginx/html
COPY nginx/nginx.conf.template /etc/nginx/templates/default.conf.template

EXPOSE 80 443
