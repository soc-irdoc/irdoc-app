#!/bin/bash -eu
# ClusterFuzzLite build script for the IRDoc backend's Python fuzz target(s).
#
# History, for anyone revisiting this -- three prior approaches were tried
# and rejected, each verified against the real check/run infrastructure
# before being replaced (not guessed at from docs alone):
#
# 1. A plain `python3 <harness>` wrapper referencing the harness by its
#    absolute path under $SRC. Built and ran fine locally, but the real
#    "Build check" step runs against a *copy* of $OUT in an isolated
#    scratch dir without $SRC alongside it -- confirmed via real CI logs
#    ("python3: can't open file '/src/irdoc-app/backend/fuzz/
#    report_html_fuzzer.py'").
# 2. Made $OUT self-contained (pip install --target + cp -r of app/
#    templates/fuzz, no freezing). Fixed the above, but oss-fuzz's
#    bad_build_check (read directly from base-runner's own source) does
#    `file "${FUZZER}.pkg"` for FUZZING_LANGUAGE=python specifically --
#    it always expects a real compiled binary at that exact suffixed path,
#    regardless of self-containment. A shell-script wrapper can never
#    satisfy that check on its own.
# 3. PyInstaller --onefile with the doc's literal naming, no `.pkg`
#    suffix: fixes the architecture check but two more issues turned up,
#    both confirmed locally before landing here: this harness's import
#    chain (report_html_fuzzer -> incident_service -> app.models ->
#    app.core.database) reaches sqlalchemy's create_async_engine(), which
#    imports asyncpg's compiled C extension -- PyInstaller's freeze broke
#    loading it until `--collect-all asyncpg` was added. And
#    bad_build_check's check_mixed_sanitizers (which flags "does not seem
#    to be compiled with ASan") turned out to unconditionally `return 0`
#    for FUZZING_LANGUAGE=python -- i.e. moot for us either way, verified
#    by reading base-runner's actual bad_build_check script rather than
#    assumed.
#
# Landed on: PyInstaller --onefile, output named "<basename>.pkg" (the
# exact suffix oss-fuzz's check_architecture appends for
# FUZZING_LANGUAGE=python before running `file` on it), plus a thin
# `$OUT/<basename>` wrapper that just execs the .pkg -- this is what
# run_fuzzer actually invokes (confirmed by reading run_fuzzer's source:
# `$OUT/$FUZZER -- $FUZZER_ARGS $*`, no `.pkg` suffix there). No
# LD_PRELOAD/ASan runtime in the wrapper: per check_mixed_sanitizers
# above, that check is skipped entirely for Python, so it would add risk
# (a wrong sanitizer_with_fuzzer.so path) for zero benefit.
#
# All three of the fixes above (self-containment via PyInstaller's own
# bundling, --collect-all asyncpg, and the .pkg naming) were verified
# end-to-end against $OUT copied into a fresh gcr.io/oss-fuzz-base/
# base-runner container that never had /src or this repo's own
# Dockerfile -- including the literal bad_build_check invocation with
# FUZZING_LANGUAGE=python set, not just a "looks right" build.

PROJECT_DIR="$SRC/irdoc-app"
BACKEND_DIR="$PROJECT_DIR/backend"

pip3 install -q -r "$BACKEND_DIR/fuzz/requirements.txt"

for fuzzer in $(find "$BACKEND_DIR/fuzz" -name '*_fuzzer.py'); do
  fuzzer_basename=$(basename -s .py "$fuzzer")

  # --add-data lands backend/templates at the frozen module tree's root
  # (verified locally: engine.py's _TEMPLATE_DIR =
  # Path(__file__).parent.parent.parent.parent / "templates" resolves to
  # exactly that root under PyInstaller's onefile extraction, since
  # --paths backend makes "app" -- not "backend/app" -- the top-level
  # frozen package). --collect-all asyncpg is required (see history
  # above) for its compiled C extension to survive freezing.
  pyinstaller --distpath "$OUT" --onefile --name "${fuzzer_basename}.pkg" \
    --paths "$BACKEND_DIR" \
    --add-data "$BACKEND_DIR/templates:templates" \
    --collect-all asyncpg \
    "$fuzzer"

  # Thin wrapper at $OUT/<basename> (no .pkg suffix) -- this is the path
  # run_fuzzer/check_engine/check_startup_crash actually invoke.
  # check_architecture separately looks for $OUT/<basename>.pkg (the real
  # PyInstaller binary above) to verify it, but never executes it
  # directly itself.
  cat > "$OUT/$fuzzer_basename" <<WRAPPER
#!/bin/sh
# LLVMFuzzerTestOneInput for fuzzer detection.
this_dir=\$(cd "\$(dirname "\$0")" && pwd)
exec "\$this_dir/${fuzzer_basename}.pkg" "\$@"
WRAPPER
  chmod +x "$OUT/$fuzzer_basename"
done
