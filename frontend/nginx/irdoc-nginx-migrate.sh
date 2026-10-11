#!/bin/sh
# irdoc-nginx-migrate.sh - bring an install's host nginx.conf up to date (#57).
#
# Usage: irdoc-nginx-migrate.sh /path/to/nginx.conf
#
# Shipped in the frontend image at /usr/local/bin/irdoc-nginx-migrate and run by
# both upgrade paths (docker/upgrade.sh and the installer wizard) through
# `docker compose run` with the install's docker/nginx/ directory mounted. It
# comes from the image being upgraded *to*, so it always matches the snippet
# that image ships.
#
# Before #57 the security headers (CSP etc.) were written into the host's
# bind-mounted nginx.conf at install time and never updated, so old installs
# kept an outdated CSP after upgrading. This script, in each server block:
#   - replaces the inline CSP, X-Frame-Options, X-Content-Type-Options,
#     Referrer-Policy and Permissions-Policy lines with one `include` of
#     /etc/nginx/snippets/irdoc-security-headers.conf (HSTS is kept);
#   - adds the include after `server_name` if the block had none of them
#     (blocks that only redirect with `return 301` are left alone).
# Everything else in the file (cert paths, extra locations, ...) is kept.
#
# A copy of the original is written next to it as nginx.conf.bak-<timestamp>.
# The file is rewritten in place (same inode), because it is bind-mounted into
# the running frontend container as a single file.
#
# Exit codes: 0 = updated, 10 = already up to date (nothing written), 1 = error.
# POSIX sh + awk only: it runs under busybox in the nginx:alpine image.
set -eu

SNIPPET=/etc/nginx/snippets/irdoc-security-headers.conf
conf=${1:?usage: irdoc-nginx-migrate.sh /path/to/nginx.conf}

[ -f "$conf" ] || { echo "irdoc-nginx-migrate: $conf not found" >&2; exit 1; }

if grep -q 'irdoc-security-headers\.conf' "$conf"; then
  echo "nginx.conf already includes the shared security headers - unchanged."
  exit 10
fi

tmp="$conf.tmp.$$"
trap 'rm -f "$tmp"' EXIT

awk -v snippet="$SNIPPET" '
  function is_header(line) {
    return line ~ /^[ \t]*add_header[ \t]+(Content-Security-Policy|X-Frame-Options|X-Content-Type-Options|Referrer-Policy|Permissions-Policy)[ \t]/
  }
  function indent_of(line) {
    match(line, /^[ \t]*/)
    return substr(line, 1, RLENGTH)
  }
  { lines[NR] = $0 }
  END {
    # Pass 1: find server blocks and what each one contains.
    block = 0
    for (i = 1; i <= NR; i++) {
      if (lines[i] ~ /^[ \t]*server[ \t]*\{/) block++
      blk[i] = block
      if (block == 0) continue
      if (is_header(lines[i])) {
        if (!(block in first_header)) first_header[block] = i
        drop[i] = 1
      }
      if (lines[i] ~ /^[ \t]*return[ \t]+30[1278]/) redirect[block] = 1
      if (lines[i] ~ /^[ \t]*server_name[ \t]/ && !(block in name_line)) name_line[block] = i
      if (lines[i] ~ /^[ \t]*server[ \t]*\{/) start_line[block] = i
    }
    # The comment IRDoc generated above the CSP explains directives that now
    # live in the snippet; drop it along with the headers it described.
    for (b in first_header) {
      j = first_header[b] - 1
      while (j > start_line[b] && lines[j] ~ /^[ \t]*#/ && !(lines[j] ~ /CSP relaxations/)) j--
      if (lines[j] ~ /^[ \t]*# CSP relaxations/)
        for (k = j; k < first_header[b]; k++) drop[k] = 1
    }
    # Pass 2: write the result.
    for (i = 1; i <= NR; i++) {
      b = blk[i]
      if (b in first_header && i == first_header[b]) {
        print indent_of(lines[i]) "include " snippet ";"
        continue
      }
      if (i in drop) continue
      print lines[i]
      if (b > 0 && !(b in first_header) && !(b in redirect)) {
        anchor = (b in name_line) ? name_line[b] : start_line[b]
        if (i == anchor) {
          ind = (anchor == start_line[b]) ? indent_of(lines[i]) "    " : indent_of(lines[i])
          print ind "include " snippet ";"
        }
      }
    }
  }
' "$conf" > "$tmp"

backup="$conf.bak-$(date +%Y%m%d-%H%M%S)"
cp "$conf" "$backup"
cat "$tmp" > "$conf"
echo "nginx.conf updated to include the shared security headers (backup: $(basename "$backup"))."
