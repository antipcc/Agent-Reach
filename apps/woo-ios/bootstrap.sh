#!/usr/bin/env bash
# Generates Woo.xcodeproj from project.yml and opens it.
#
# The project file is generated rather than committed: a declarative
# project.yml is reviewable and never conflicts, and XcodeGen has been
# exercised far more than any hand-written pbxproj.
set -euo pipefail

cd "$(dirname "$0")"

if ! command -v xcodegen >/dev/null 2>&1; then
  echo "XcodeGen is not installed. Install it with:"
  echo "  brew install xcodegen"
  echo
  echo "Or build the project by hand — see the fallback in README.md."
  exit 1
fi

xcodegen generate
echo "Generated Woo.xcodeproj"

if [[ "${1:-}" != "--no-open" ]]; then
  open Woo.xcodeproj
fi
