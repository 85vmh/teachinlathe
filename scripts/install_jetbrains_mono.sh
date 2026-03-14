#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
BUNDLE_DIR="${PROJECT_ROOT}/assets/fonts/JetBrainsMono"
USER_FONT_DIR="${HOME}/.local/share/fonts/JetBrainsMono"
TMP_DIR="$(mktemp -d)"

cleanup() {
    rm -rf "${TMP_DIR}"
}

trap cleanup EXIT

font_installed() {
    fc-match "JetBrains Mono" >/dev/null 2>&1
}

bundle_has_fonts() {
    find "${BUNDLE_DIR}" -maxdepth 1 \( -iname 'JetBrainsMono-*.ttf' -o -iname 'JetBrainsMono-*.otf' \) | grep -q .
}

download_bundle() {
    echo "JetBrains Mono not found in project cache. Downloading official release..."

    if ! command -v curl >/dev/null 2>&1; then
        echo "curl is required to download JetBrains Mono." >&2
        return 1
    fi

    if ! command -v python3 >/dev/null 2>&1; then
        echo "python3 is required to parse the GitHub release metadata." >&2
        return 1
    fi

    if ! command -v unzip >/dev/null 2>&1; then
        echo "unzip is required to extract the JetBrains Mono archive." >&2
        return 1
    fi

    local api_url="https://api.github.com/repos/JetBrains/JetBrainsMono/releases/latest"
    local release_json="${TMP_DIR}/release.json"
    local zip_url
    local zip_path="${TMP_DIR}/jetbrains-mono.zip"

    curl -fsSL "${api_url}" -o "${release_json}"

    zip_url="$(python3 - "${release_json}" <<'PY'
import json
import sys

with open(sys.argv[1], "r", encoding="utf-8") as fh:
    data = json.load(fh)

for asset in data.get("assets", []):
    url = asset.get("browser_download_url", "")
    if url.endswith(".zip") and "JetBrainsMono" in url:
        print(url)
        break
else:
    raise SystemExit("Could not find JetBrains Mono zip asset in the latest release.")
PY
)"

    mkdir -p "${BUNDLE_DIR}"
    curl -fsSL "${zip_url}" -o "${zip_path}"
    unzip -jo "${zip_path}" 'fonts/ttf/*.ttf' -d "${BUNDLE_DIR}" >/dev/null
}

install_fonts() {
    mkdir -p "${USER_FONT_DIR}"
    find "${BUNDLE_DIR}" -maxdepth 1 \( -iname 'JetBrainsMono-*.ttf' -o -iname 'JetBrainsMono-*.otf' \) -exec cp -f {} "${USER_FONT_DIR}/" \;
    fc-cache -f "${USER_FONT_DIR}"
}

if font_installed; then
    echo "JetBrains Mono is already installed."
    exit 0
fi

if ! bundle_has_fonts; then
    download_bundle
fi

if ! bundle_has_fonts; then
    echo "JetBrains Mono files are still missing from ${BUNDLE_DIR}." >&2
    exit 1
fi

install_fonts

if font_installed; then
    echo "JetBrains Mono installed successfully."
else
    echo "Installation finished, but fontconfig still does not report JetBrains Mono." >&2
    exit 1
fi
