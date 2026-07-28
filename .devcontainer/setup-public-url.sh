#!/bin/bash
# Detect codespace public URL and write to env file
set -e

# Try gh CLI first
CODESPACE_JSON=$(gh codespace view --json name 2>/dev/null || true)
if [ -z "$CODESPACE_JSON" ]; then
    # Fallback: use hostname
    HOST=$(hostname)
    # In Codespaces, hostname is like: codespaces-XXXX
    if [[ "$HOST" == codespaces-* ]]; then
        # We know the codespace name from the port URL pattern
        # Actually, let's use the CODESPACES=true env that IS set
        echo "PUBLIC_URL=" > /workspaces/pawwork-clone/.env
        echo "⚠️  Could not detect codespace URL. Set PUBLIC_URL manually."
        exit 0
    fi
fi

# Try to get the name from gh
CODESPACE_NAME=$(echo "$CODESPACE_JSON" | python3 -c "import json,sys; print(json.load(sys.stdin).get('name',''))" 2>/dev/null || echo "")

if [ -n "$CODESPACE_NAME" ]; then
    PUBLIC_URL="https://${CODESPACE_NAME}-8080.app.github.dev"
    echo "PUBLIC_URL=$PUBLIC_URL" > /workspaces/pawwork-clone/.env
    echo "✅ Detected URL: $PUBLIC_URL"
else
    echo "PUBLIC_URL=" > /workspaces/pawwork-clone/.env
    echo "⚠️  Could not detect codespace name"
fi
