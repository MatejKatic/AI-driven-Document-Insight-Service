#!/bin/bash
# Make all required scripts executable

echo "🔧 Making scripts executable..."

if [ -f docker-entrypoint.sh ]; then
    chmod +x docker-entrypoint.sh
    echo "✅ Made docker-entrypoint.sh executable"
else
    echo "❌ docker-entrypoint.sh not found!"
fi

if [ -f run_services.sh ]; then
    chmod +x run_services.sh
    echo "✅ Made run_services.sh executable"
else
    echo "❌ run_services.sh not found!"
fi

chmod +x make_executable.sh 2>/dev/null

echo "✅ Done!"