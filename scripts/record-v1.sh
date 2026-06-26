#!/usr/bin/env bash
# Run the v1.0 Playwright recording against production and save the video.
# Usage:
#   BASE_URL=https://tanqitflow.yourdomain.ma \
#   E2E_ADMIN_EMAIL=admin@onee.ma \
#   E2E_ADMIN_PASS=YourPassword \
#   ./scripts/record-v1.sh

set -euo pipefail

DATE=$(date +%Y-%m-%d)
OUTPUT=".recordings/v1.0-${DATE}-full.webm"

echo "Recording v1.0 flows against ${BASE_URL:-http://localhost:5173}"

cd frontend

# Run the recording spec
npx playwright test v1-recording.spec.ts \
  --project=chromium \
  --reporter=list

# Find the most recent video file and copy it to .recordings/
VIDEO=$(find tests/e2e/artifacts -name "*.webm" -newer package.json | sort -r | head -1)

if [ -z "$VIDEO" ]; then
  echo "ERROR: No video file found in tests/e2e/artifacts/"
  exit 1
fi

cd ..
cp "$frontend/$VIDEO" 2>/dev/null || cp "frontend/$VIDEO" "$OUTPUT"
echo "✓ Recording saved: $OUTPUT"
