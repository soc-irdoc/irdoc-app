# ClusterFuzzLite build image for the IRDoc backend's Python fuzz target(s).
#
# Base image and the "copy the already-checked-out repo in, don't git clone
# it yourself" pattern follow the current ClusterFuzzLite Python guidance:
# https://google.github.io/clusterfuzzlite/build-integration/python-lang/
FROM gcr.io/oss-fuzz-base/base-builder-python

# Atheris (the libFuzzer-based Python fuzzing engine) is expected to already
# be present on base-builder-python, but install it explicitly rather than
# depend on whatever happens to be baked into the base image at any given
# time.
RUN pip3 install atheris==3.0.0

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
