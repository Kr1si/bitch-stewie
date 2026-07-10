# Frontend image: Vite build served by nginx, which also proxies /api to the
# backend so the SPA and API share one origin (single SSH tunnel port).

FROM node:22-alpine AS build
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
# Empty string -> same-origin API calls (nginx proxies /api to the backend)
ENV VITE_API_BASE=
RUN npm run build

FROM nginx:alpine
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html
