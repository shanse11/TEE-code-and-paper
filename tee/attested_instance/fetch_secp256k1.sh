#!/usr/bin/env bash
# Fetches the pinned libsecp256k1 release into third_party/secp256k1.
set -euo pipefail
cd "$(dirname "$0")"
TAG=v0.6.0
if [ ! -d third_party/secp256k1 ]; then
  mkdir -p third_party
  git clone --depth 1 --branch "$TAG" https://github.com/bitcoin-core/secp256k1.git third_party/secp256k1
fi
git -C third_party/secp256k1 describe --tags
