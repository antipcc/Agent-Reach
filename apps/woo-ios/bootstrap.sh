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

# --- Signing -----------------------------------------------------------------
# Regenerating the project wipes anything set in Xcode's Signing pane, and
# regenerating is what this script does. Signing therefore lives in
# Local.xcconfig, which the project only references — written once, kept for
# good. Both values can be discovered, so nobody has to go hunting for them.
if [[ ! -f Local.xcconfig ]]; then
  team="$(security find-identity -v -p codesigning 2>/dev/null \
          | grep -oE '\([A-Z0-9]{10}\)' | head -1 | tr -d '()' || true)"
  # The default bundle id is registered to nobody, so device builds need one
  # under an identifier the developer actually controls.
  bundle="com.$(id -un | tr '[:upper:]' '[:lower:]' | tr -cd 'a-z0-9').woo"

  {
    echo "// Written by bootstrap.sh, gitignored — this file is yours alone."
    echo "// Delete it and re-run the script to have it worked out again."
    echo "PRODUCT_BUNDLE_IDENTIFIER = ${bundle}"
    if [[ -n "${team}" ]]; then
      echo "DEVELOPMENT_TEAM = ${team}"
    else
      echo "DEVELOPMENT_TEAM ="
    fi
  } > Local.xcconfig

  if [[ -n "${team}" ]]; then
    echo "✓ Signing set up: ${bundle}, team ${team}"
  else
    echo "⚠️  No signing identity found on this Mac."
    echo "   Sign in at Xcode → Settings → Accounts, then:"
    echo "     rm Local.xcconfig && ./bootstrap.sh"
  fi
else
  echo "✓ Signing already set up (Local.xcconfig)"
fi

xcodegen generate
echo "Generated Woo.xcodeproj"

if [[ "${1:-}" != "--no-open" ]]; then
  open Woo.xcodeproj
fi
