FROM node:20-alpine@sha256:fb4cd12c85ee03686f6af5362a0b0d56d50c58a04632e6c0fb8363f609372293 AS builder
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM nginx:alpine@sha256:72ba65eb42c10344912a84ff42408db7d34f2feb642204570ab8fc5ffd29f1d3
# `apk upgrade` picks up Alpine package-index security patches (e.g.
# libuuid) that land between base-image rebuilds.
RUN apk update && apk upgrade --no-cache
COPY --from=builder /app/dist /usr/share/nginx/html
# The default config lives in the image, so it always matches the snippet
# below (#131). At start-up 90-irdoc-select-conf.sh installs the install's own
# docker/nginx/local/nginx.conf instead when there is one (#114).
COPY nginx/default.conf /etc/nginx/irdoc/default.conf
COPY nginx/default.conf /etc/nginx/conf.d/default.conf
COPY --chmod=755 nginx/90-irdoc-select-conf.sh /docker-entrypoint.d/90-irdoc-select-conf.sh
# Security headers live in the image so upgrades update them; the upgrade
# paths run irdoc-nginx-migrate to switch an old local nginx.conf over (#57).
COPY nginx/irdoc-security-headers.conf /etc/nginx/snippets/irdoc-security-headers.conf
COPY --chmod=755 nginx/irdoc-nginx-migrate.sh /usr/local/bin/irdoc-nginx-migrate
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
