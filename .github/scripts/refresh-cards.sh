#!/usr/bin/env bash
# Replaces a card only when the download is a real one, so a host that is down
# or answers with an error card leaves the last good copy in place.
set -uo pipefail
stale=0
tmp=$(mktemp)
while IFS=$'\t' read -r name marker url; do
  ok=0
  for attempt in 1 2 3 4; do
    code=$(curl -sS -L --max-time 60 -o "$tmp" -w '%{http_code}' "$url" || echo 000)
    if [ "$code" = 200 ] && grep -q '<svg' "$tmp" && grep -qF "$marker" "$tmp"; then
      cp "$tmp" "assets/cards/$name.svg"
      ok=1
      echo "$name: refreshed"
      break
    fi
    echo "$name: attempt $attempt got HTTP $code"
    sleep 20
  done
  if [ "$ok" = 0 ]; then
    echo "::warning::$name kept its last good copy"
    stale=$((stale + 1))
  fi
done < .github/scripts/cards.tsv
rm -f "$tmp"
echo "$stale card(s) not refreshed"
