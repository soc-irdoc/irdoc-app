# ClusterFuzzLite build image for the IRDoc backend's Python fuzz target(s).
#
# Base image and the "copy the already-checked-out repo in, don't git clone
# it yourself" pattern follow the current ClusterFuzzLite Python guidance:
# https://google.github.io/clusterfuzzlite/build-integration/python-lang/
#
# Pinned by digest (Scorecard Pinned-Dependencies); refresh it now and then with
#   docker buildx imagetools inspect gcr.io/oss-fuzz-base/base-builder-python
# Its Python (3.11) is the one the hashed requirement files here are locked for.
FROM gcr.io/oss-fuzz-base/base-builder-python@sha256:21f6fab17ace4dc76e1c56de91ee95d3d03da021df94b41056ba036f6c6f55e9

# Atheris (the libFuzzer-based Python fuzzing engine) is expected to already
# be present on base-builder-python, but install it explicitly rather than
# depend on whatever happens to be baked into the base image at any given
# time.
# Hash-pinned: requirements-atheris.txt, locked from requirements-atheris.in.
COPY .clusterfuzzlite/requirements-atheris.txt /tmp/
RUN pip3 install --require-hashes -r /tmp/requirements-atheris.txt

# app.core.config.Settings raises at import time if SECRET_KEY is unset or
# shorter than 32 chars (see backend/app/core/config.py's
# require_real_secret validator). The fuzz target's import chain reaches
# that module lazily via the sanitize_html Jinja filter -> _sanitize_html.
# This is not a production secret and grants no capability inside the fuzz
# container -- nothing here authenticates anything -- it only needs to
# exist and be long enough to satisfy that validator so the harness doesn't
# fail on an unrelated startup check the very first time
# executive_summary/ai_executive_summary is non-empty.
ENV SECRET_KEY="fuzzing-harness-only-placeholder-not-a-real-secret-000000"

COPY . $SRC/irdoc-app
WORKDIR $SRC/irdoc-app
COPY ./.clusterfuzzlite/build.sh $SRC/
