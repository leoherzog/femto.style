#!/usr/bin/env bash
# Installs femto into node_modules: from FEMTO_DIR (a femto checkout) when set, otherwise from npm, and
# from GitHub if npm fails. `claude plugin eval` passes a scaffold none of the shell's variables but PATH,
# so FEMTO_DIR takes effect only when this script is run by hand.
set -eu
if [ -n "${FEMTO_DIR:-}" ]; then
  mkdir -p node_modules/@leoherzog/femto
  cp -R "$FEMTO_DIR"/package.json "$FEMTO_DIR"/README.md "$FEMTO_DIR"/LICENSE.md "$FEMTO_DIR"/css "$FEMTO_DIR"/dist node_modules/@leoherzog/femto/
elif ! npm install --no-save --ignore-scripts @leoherzog/femto@3.0.0-beta.1; then
  npm install --no-save --ignore-scripts github:leoherzog/femto
fi
