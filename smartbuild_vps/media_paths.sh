#!/usr/bin/env bash

export SMARTBUILD_ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export SMARTBUILD_MODEL_PATH="${SMARTBUILD_ROOT_DIR}/../model/best.pt"
export SMARTBUILD_UPLOAD_DIR="${SMARTBUILD_ROOT_DIR}/uploads"
export SMARTBUILD_ANNOTATED_DIR="${SMARTBUILD_UPLOAD_DIR}/annotated"
export SMARTBUILD_TIMELAPSE_PATH="${SMARTBUILD_UPLOAD_DIR}/timelapse.mp4"
export SMARTBUILD_FRAMES_DIR="${SMARTBUILD_ROOT_DIR}/../edge_sim/timelaps"
export LIVE_PATH="${SMARTBUILD_ROOT_DIR}/../edge_sim/live/camera.mp4"