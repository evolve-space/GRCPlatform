FROM node:20-alpine

WORKDIR /app

COPY package.json ./
RUN npm install

COPY . .

# Fase 10 (hardening): se probó "USER node" aquí (la imagen node:20-alpine ya
# lo incluye), pero se revirtió — docker-compose.yml monta node_modules como
# volumen anónimo para el hot-reload en desarrollo, y Docker lo recrea con
# propietario root en cada arranque, por delante del chown de esta imagen
# (EACCES real, comprobado). Este contenedor es exclusivamente el servidor
# de desarrollo de Vite (nunca la imagen servida en producción, que no usa
# bind mounts ni ejecuta como root — ver docs/DEPLOYMENT.md), así que se
# acepta correr como root aquí en vez de complicar el arranque con un
# entrypoint que reajuste permisos en cada inicio.

EXPOSE 5173

CMD ["npm", "run", "dev"]
