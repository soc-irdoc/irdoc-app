#!/bin/sh
# 90-irdoc-select-conf.sh - pick the nginx config the frontend serves (#114, #131).
#
# Shipped in /docker-entrypoint.d/, which the stock nginx image entrypoint runs
# before starting nginx. It installs one of these as conf.d/default.conf:
#   - /etc/nginx/irdoc-local/nginx.conf: the install's own config, from the
#     docker/nginx/local/ directory that docker-compose.prod.yml mounts
#     (HTTPS, custom certs, ...). It is git-ignored, so `git pull` never
#     conflicts with it.
#   - /etc/nginx/irdoc/default.conf otherwise: the default shipped in this
#     image, which always matches the snippet the image ships.
#
# The config is copied at every container start, so a changed local file
# takes effect on `docker compose restart frontend`.
#
# POSIX sh only: it runs under busybox in the nginx:alpine image.
set -eu

# Overridable for installer/tests/test_nginx_migrate.py only.
LOCAL=${IRDOC_NGINX_LOCAL:-/etc/nginx/irdoc-local/nginx.conf}
DEFAULT=${IRDOC_NGINX_DEFAULT:-/etc/nginx/irdoc/default.conf}
TARGET=${IRDOC_NGINX_TARGET:-/etc/nginx/conf.d/default.conf}

# An old docker-compose.prod.yml bind-mounts a file over the target itself.
# Leave that alone: the copy would fail on the read-only mount.
if grep -q " ${TARGET} " /proc/mounts 2>/dev/null; then
  echo "$0: ${TARGET} is bind-mounted, using it as is"
  exit 0
fi

if [ -f "$LOCAL" ]; then
  src=$LOCAL
else
  src=$DEFAULT
fi
cp "$src" "$TARGET"
echo "$0: using ${src}"
