#!/bin/bash -eu
# ClusterFuzzLite build script for the IRDoc backend's Python fuzz target(s).
#
# Follows https://google.github.io/clusterfuzzlite/build-integration/python-lang/
# with one deliberate simplification: the doc's own template wraps each
# `*_fuzzer.py` in a PyInstaller --onefile package plus a shell wrapper that
# LD_PRELOADs a sanitizer runtime. That LD_PRELOAD step is explicitly
# documented as unnecessary "if you are fuzzing python-only code and do not
# have native C/C++ extensions" (true here -- the target is Jinja2 + bleach,
# no C extensions), and the PyInstaller freeze step itself is documented as
# being about surviving *OSS-Fuzz's long-lived bots'* Python-version drift
# over time ("not necessarily required for reproducing issues... required
# to keep fuzzers working properly in OSS-Fuzz"), not a ClusterFuzzLite CI
# correctness requirement -- ClusterFuzzLite builds and runs in the same
# ephemeral container within one job, so there's no environment drift to
# survive. Given that, and that PyInstaller's --onefile mode changes the
# frozen module's __file__ layout (which this target's Jinja2
# FileSystemLoader depends on via backend/app/services/report_renderer/
# engine.py's _TEMPLATE_DIR = Path(__file__).parent.parent.parent.parent /
# "templates" -- getting --add-data's destination path wrong would silently
# turn every single fuzz iteration into a TemplateNotFound "crash" that has
# nothing to do with the code under test), a plain `python3 <harness>` is
# both simpler and less likely to produce exactly that kind of false
# finding. This is a deliberate deviation from the doc's literal template --
# see this task's report for the full reasoning, flagged there for
# confirmation on the first real ClusterFuzzLite CI run.

PROJECT_DIR="$SRC/irdoc-app"
BACKEND_DIR="$PROJECT_DIR/backend"

pip3 install -r "$BACKEND_DIR/fuzz/requirements.txt"

for fuzzer in $(find "$BACKEND_DIR/fuzz" -name '*_fuzzer.py'); do
  fuzzer_basename=$(basename -s .py "$fuzzer")

  # Execution wrapper placed in $OUT under the fuzzer's basename -- this is
  # what build_fuzzers/run_fuzzers actually invokes. No LD_PRELOAD/ASan
  # runtime here: this is a pure-Python target with no C/C++ extensions
  # (see note above).
  cat > "$OUT/$fuzzer_basename" <<WRAPPER
#!/bin/sh
# LLVMFuzzerTestOneInput for fuzzer detection. ClusterFuzzLite's build-check
# greps $OUT files for this exact literal string as a language-agnostic
# heuristic to recognize a valid fuzz target (documented in the upstream
# Python build.sh template even for non-PyInstaller, non-C targets like this
# one) -- without it present verbatim, "Build check" reports "No fuzz
# targets found" even though this wrapper is otherwise fully functional.
export PYTHONPATH="$BACKEND_DIR:\${PYTHONPATH:-}"
exec python3 "$fuzzer" "\$@"
WRAPPER
  chmod +x "$OUT/$fuzzer_basename"
done
