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

if [[ ! -f Local.xcconfig ]]; then
  cat <<'NOTE'

⚠️  No Local.xcconfig — this project will not install on a device.

    cp Local.xcconfig.example Local.xcconfig
    # then edit it: your own bundle id, and your Team ID from
    # Xcode → Settings → Accounts

    Set them there rather than in Xcode's Signing pane: this script
    regenerates the project, and anything set in the pane is lost.
NOTE
fi

if [[ "${1:-}" != "--no-open" ]]; then
  open Woo.xcodeproj
fi
