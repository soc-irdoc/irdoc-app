#!/bin/bash -eu
# ClusterFuzzLite build script for the IRDoc backend's Python fuzz target(s).
#
# Deviates from https://google.github.io/clusterfuzzlite/build-integration/python-lang/'s
# literal PyInstaller --onefile template. History, for anyone revisiting this:
#
# 1. First attempt: a plain `python3 <harness>` wrapper referencing the
#    harness by its absolute path under $SRC. Built and ran fine locally,
#    but the real ClusterFuzzLite "Build check" step (run against a *copy*
#    of $OUT in an isolated scratch dir, without $SRC alongside it) failed
#    with "No such file or directory" for that absolute path -- $OUT is not
#    guaranteed to keep $SRC around into the check/run stage.
# 2. Second attempt: PyInstaller --onefile, per the doc's literal template.
#    Solved the self-containment problem, but broke on a different axis:
#    this harness's import chain (report_html_fuzzer -> incident_service ->
#    app.models -> app.core.database) reaches sqlalchemy's
#    create_async_engine(), which imports asyncpg -- a package with a
#    compiled C extension (asyncpg.protocol.protocol). PyInstaller's freeze
#    broke loading that extension ("SystemError: execution of module
#    asyncpg.protocol.protocol raised unreported exception"), verified
#    locally in an isolated container before ever pushing this.
#
# Landed on instead: make $OUT self-contained WITHOUT freezing anything --
# `pip install --target` the fuzz-only deps and copy the source tree the
# harness needs directly into $OUT as siblings of the wrapper script, then
# point PYTHONPATH at them relative to the wrapper's own location (so it
# doesn't matter whether the check/run stage keeps $SRC around, since
# nothing here references it). No C-extension freezing, no __file__-based
# template-path risk (verified locally: `Path(__file__).parent x4` inside
# `$OUT/fuzz_src/app/services/report_renderer/engine.py` correctly resolves
# to `$OUT/fuzz_src/templates`, since the copied tree preserves the same
# `app/.../engine.py` -> `../../../../templates` relative layout as the
# real backend/ directory).

PROJECT_DIR="$SRC/irdoc-app"
BACKEND_DIR="$PROJECT_DIR/backend"

# Fuzz-only deps, installed straight into $OUT so the check/run stage has
# them without needing $SRC or a prior `pip install` to still be in effect.
# Also bundles atheris itself (kept in sync with .clusterfuzzlite/
# Dockerfile's system-wide install by version) -- confirmed locally that
# the check/run stage is not guaranteed to be the same image this build
# step runs in (verified against gcr.io/oss-fuzz-base/base-runner, which
# has no atheris preinstalled), so relying on the build image's system
# install alone silently breaks downstream with "ModuleNotFoundError: No
# module named 'atheris'".
pip3 install --target "$OUT/fuzz_deps" atheris==3.0.0 -r "$BACKEND_DIR/fuzz/requirements.txt"

# The app source + templates the harness imports/renders, copied alongside
# the deps for the same self-containment reason. Not the full backend/ tree
# (see backend/fuzz/requirements.txt's own comment on why) -- just app/,
# templates/, and fuzz/ itself.
mkdir -p "$OUT/fuzz_src"
cp -r "$BACKEND_DIR/app" "$OUT/fuzz_src/app"
cp -r "$BACKEND_DIR/templates" "$OUT/fuzz_src/templates"
cp -r "$BACKEND_DIR/fuzz" "$OUT/fuzz_src/fuzz"

for fuzzer in $(find "$BACKEND_DIR/fuzz" -name '*_fuzzer.py'); do
  fuzzer_basename=$(basename -s .py "$fuzzer")

  # Execution wrapper placed in $OUT under the fuzzer's basename -- this is
  # what build_fuzzers/run_fuzzers actually invokes. No LD_PRELOAD/ASan
  # runtime here: this is a pure-Python target with no C/C++ extensions
  # (see note above). Resolves fuzz_src/fuzz_deps relative to its own
  # location ($this_dir), not $OUT or $SRC directly, since the check/run
  # stage may invoke this from a copied-elsewhere path.
  cat > "$OUT/$fuzzer_basename" <<WRAPPER
#!/bin/sh
# LLVMFuzzerTestOneInput for fuzzer detection. ClusterFuzzLite's build-check
# greps $OUT files for this exact literal string as a language-agnostic
# heuristic to recognize a valid fuzz target (documented in the upstream
# Python build.sh template even for non-PyInstaller, non-C targets like this
# one) -- without it present verbatim, "Build check" reports "No fuzz
# targets found" even though this wrapper is otherwise fully functional.
this_dir=\$(cd "\$(dirname "\$0")" && pwd)
export PYTHONPATH="\$this_dir/fuzz_src:\$this_dir/fuzz_deps:\${PYTHONPATH:-}"
exec python3 "\$this_dir/fuzz_src/fuzz/$fuzzer_basename.py" "\$@"
WRAPPER
  chmod +x "$OUT/$fuzzer_basename"
done
