#!/usr/bin/env bash
set -eu
cp -R "$(dirname "$0")/files/." .

if [ -x ./place-femto.sh ]; then ./place-femto.sh; rm ./place-femto.sh; fi
