# === Stage 1 : build Angular ===
FROM node:20-alpine AS build

WORKDIR /app

# Cache layers de deps
COPY package*.json ./
RUN npm ci --legacy-peer-deps

# Code source + build prod (déclenche fileReplacements vers environment.production.ts)
COPY . .
RUN npm run build -- --configuration production

# === Stage 2 : nginx sert UNIQUEMENT les statics ===
# Le proxy /api est géré en amont par Caddy (VPS) ou par CORS (local dev).
FROM nginx:alpine

# Copie le bundle Angular (Angular 17+ : dist/<project>/browser/)
COPY --from=build /app/dist/frontend/browser /usr/share/nginx/html

# Config nginx (SPA fallback + cache assets)
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
