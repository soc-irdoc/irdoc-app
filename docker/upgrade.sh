#!/bin/bash
# upgrade.sh — Zero-downtime IRDoc upgrade (published images from GHCR)
# Usage: bash upgrade.sh [version]
# Example: bash upgrade.sh 0.1.4-alpha
#          bash upgrade.sh          (upgrades to latest)
#
# Only for installs started with docker-compose.prod.yml (the installer wizard
# and the production guide both do this). An install started with plain
# `docker compose up` (docker-compose.yml) builds from the source checkout:
# it serves on port 3000 and keeps files in the repo-root storage/ directory.
# Upgrading that with this script would silently move it to a different
# stack (ports 80/443, docker/storage/) — so the script refuses (#82).
set -e

VERSION=${1:-latest}
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
COMPOSE_FILE="${SCRIPT_DIR}/docker-compose.prod.yml"
NGINX_DIR="${SCRIPT_DIR}/nginx"
LOCAL_NGINX_DIR="${NGINX_DIR}/local"
ENV_FILE="${SCRIPT_DIR}/.env"

# sha256 (LF line endings) of every docker/nginx/nginx.conf IRDoc shipped. A
# file matching one of them was never edited on this server. Keep in step with
# SHIPPED_NGINX_CONF_SHA256 in installer/core/nginx.py.
SHIPPED_NGINX_SHA256="f35bd18cfb20b0bb701f8d822d80dbdfa3b9869dc9a0623c5b296b3b5c3b7d78 3302bf4ddf1e61feccdac26b8a0c8622e9e0d9a11b8481fcbb2d1dceb151105f 832a486050493f5c927c68bdcf2dbc9cff4168e69bf9ee34558da1a03ce1df63"

sha256_of() {
  if command -v sha256sum >/dev/null 2>&1; then
    tr -d '\r' < "$1" | sha256sum | cut -c1-64
  else
    tr -d '\r' < "$1" | shasum -a 256 | cut -c1-64
  fi
}

# Before 0.1.8 the live nginx config was the tracked docker/nginx/nginx.conf,
# so any server-side edit (HTTPS, cert paths) made `git pull` fail (#114). It
# now lives in the git-ignored nginx/local/. Move an edited tracked file there
# and put the tracked one back, so the next pull is clean.
adopt_edited_nginx_conf() {
  local tracked="${NGINX_DIR}/nginx.conf"
  mkdir -p "${LOCAL_NGINX_DIR}"
  [ -f "${LOCAL_NGINX_DIR}/nginx.conf" ] && return 1
  [ -f "${tracked}" ] || return 1
  case " ${SHIPPED_NGINX_SHA256} " in
    *" $(sha256_of "${tracked}") "*) return 1 ;;
  esac
  cp -p "${tracked}" "${LOCAL_NGINX_DIR}/nginx.conf"
  echo "Moved your edited nginx/nginx.conf to nginx/local/nginx.conf."
  if git -C "${SCRIPT_DIR}" ls-files --error-unmatch nginx/nginx.conf >/dev/null 2>&1; then
    git -C "${SCRIPT_DIR}" checkout -- nginx/nginx.conf
    echo "Restored the tracked nginx/nginx.conf, so git pull no longer conflicts with it."
  fi
  return 0
}

echo "=== IRDoc Upgrade ==="
echo "Target version: ${VERSION}"
echo ""

# ── Which compose file is the running install using? ─────────────────────────
running_files=$(docker inspect irdoc-backend \
  --format '{{ index .Config.Labels "com.docker.compose.project.config_files" }}' 2>/dev/null || true)
if [ -n "${running_files}" ] && [[ "${running_files}" != *docker-compose.prod.yml* ]]; then
  cat >&2 <<EOF
This IRDoc install was started from source with:
  ${running_files}

upgrade.sh only upgrades installs that run the published images
(docker-compose.prod.yml). Nothing has been changed.

To update a source install, from the directory you cloned:
  git pull
  cd docker && docker compose up -d --build

If you downloaded a ZIP instead of cloning, switch to a git clone (or the
installer wizard) so updates are possible — see
https://docs.irdoc.io/installation/upgrading
EOF
  exit 1
fi

# A pinned VERSION in docker/.env that lags behind the upgrade makes every
# later plain `docker compose up -d` (demo-restore.sh, reboots with recreate)
# go back to the old image. Keep it in step with what we upgrade to.
if [ -f "${ENV_FILE}" ] && grep -q '^VERSION=' "${ENV_FILE}"; then
  current=$(grep '^VERSION=' "${ENV_FILE}" | tail -n 1 | cut -d= -f2-)
  if [ "${current}" != "${VERSION}" ]; then
    sed -i.bak "s/^VERSION=.*/VERSION=${VERSION}/" "${ENV_FILE}" && rm -f "${ENV_FILE}.bak"
    echo "docker/.env: VERSION ${current} -> ${VERSION}"
  fi
fi
# The config files come from this checkout and the images from VERSION: they
# must be the same release (#131).
repo_version=$(tr -d '[:space:]' < "${SCRIPT_DIR}/../VERSION" 2>/dev/null || true)
if [ -n "${repo_version}" ] && [ "${VERSION}" != "latest" ] && [ "${VERSION}" != "${repo_version}" ]; then
  echo "WARNING: this checkout is ${repo_version} but you are upgrading to ${VERSION}." >&2
  echo "         Run 'git pull' (or check out v${VERSION}) first so config files match the images." >&2
fi

echo "[1/5] Pulling images..."
VERSION=${VERSION} docker compose -f "${COMPOSE_FILE}" pull

echo "[2/5] Running database migrations..."
VERSION=${VERSION} docker compose -f "${COMPOSE_FILE}" run --rm backend alembic upgrade head

# The install's own nginx config is nginx/local/nginx.conf (#114); without
# one the frontend image serves its built-in default and there is nothing to
# update. Installs from before #57 have the security headers (CSP etc.)
# written into that file, where upgrades never changed them. The new frontend
# image ships them as a snippet plus a script that switches the old file over
# (keeping a nginx.conf.bak-<timestamp> copy). Best effort: if the image can't
# do it, the existing config keeps working.
echo "[3/5] Updating nginx config..."
nginx_changed=false
nginx_patched=false
if adopt_edited_nginx_conf; then
  nginx_changed=true
fi
if [ -f "${LOCAL_NGINX_DIR}/nginx.conf" ]; then
  # Git Bash on Windows: MSYS must not rewrite /irdoc-nginx/... into a Windows
  # path, so hand docker C:/... host paths ourselves. No-ops on Linux.
  host_dir=$(cd "${SCRIPT_DIR}" && pwd -W 2>/dev/null) || host_dir=${SCRIPT_DIR}
  set +e
  MSYS_NO_PATHCONV=1 VERSION=${VERSION} docker compose -f "${host_dir}/docker-compose.prod.yml" \
    run --rm --no-deps -v "${host_dir}/nginx/local:/irdoc-nginx" --user "$(id -u):$(id -g)" \
    --entrypoint irdoc-nginx-migrate frontend /irdoc-nginx/nginx.conf
  rc=$?
  set -e
  case ${rc} in
    0) nginx_patched=true; nginx_changed=true ;;
    10) ;;
    *) echo "nginx/local/nginx.conf not updated (this image can't do it); keeping the existing config." ;;
  esac
else
  echo "No nginx/local/nginx.conf: the image's default config is used."
fi

echo "[4/5] Restarting services..."
VERSION=${VERSION} docker compose -f "${COMPOSE_FILE}" up -d --remove-orphans

echo "[5/5] Verifying deployment..."
if [ "${nginx_changed}" = true ]; then
  # The frontend copies its config at start-up, and `up -d` only recreates it
  # when the image changed, so restart it to pick up the local file.
  VERSION=${VERSION} docker compose -f "${COMPOSE_FILE}" restart frontend
  nginx_ok=false
  for _ in $(seq 1 10); do
    if VERSION=${VERSION} docker compose -f "${COMPOSE_FILE}" exec -T frontend nginx -t >/dev/null 2>&1; then
      nginx_ok=true
      break
    fi
    sleep 1
  done
  if [ "${nginx_ok}" != true ] && [ "${nginx_patched}" = true ]; then
    backup=$(ls -1 "${LOCAL_NGINX_DIR}"/nginx.conf.bak-* | tail -n 1)
    cp "${backup}" "${LOCAL_NGINX_DIR}/nginx.conf"
    echo "Updated nginx/local/nginx.conf was rejected by nginx; restored $(basename "${backup}")." >&2
    VERSION=${VERSION} docker compose -f "${COMPOSE_FILE}" restart frontend
  elif [ "${nginx_ok}" != true ]; then
    echo "WARNING: nginx rejects nginx/local/nginx.conf. Check: docker compose -f docker-compose.prod.yml logs frontend" >&2
  fi
fi
healthy=false
for _ in $(seq 1 30); do
  if VERSION=${VERSION} docker compose -f "${COMPOSE_FILE}" exec -T backend \
      curl -sf http://localhost:8000/api/health >/dev/null 2>&1; then
    healthy=true
    break
  fi
  sleep 2
done
if [ "${healthy}" != true ]; then
  echo "Backend did not become healthy within 60s. Check: docker compose -f docker-compose.prod.yml logs backend" >&2
  exit 1
fi
VERSION=${VERSION} docker compose -f "${COMPOSE_FILE}" exec -T backend \
  python -c "from app import __version__; print(f'Running version: {__version__}')"

echo ""
echo "Upgrade complete."
