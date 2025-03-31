#!/usr/bin/env bash

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    >&2 echo "Creating virtual environment..."
    python3 -m venv venv && \
    >&2 echo "Virtual environment created."
fi

# Check if pytest-playwright is installed
if ! venv/bin/pip show pytest-playwright >/dev/null 2>&1; then
    >&2 echo "Installing pytest-playwright..."
    venv/bin/pip install pytest-playwright && \
    >&2 echo "pytest-playwright installed."
fi

if ! [ -z "$VIRTUAL_ENV" ]; then
    if [ "$VIRTUAL_ENV" == "$(pwd)/venv" ]; then
        >&2 echo "✅ Virtual environment already activated."
    else
        >&2 echo "❌ Some other virtual environment is activated: $VIRTUAL_ENV"
        >&2 echo "Please deactivate it before activating this one:"
        >&2 echo "    deactivate"
        exit 1
    fi
else
    >&2 echo "🔑    To activate the virtual environment, run:"
    >&2 echo "    source ./venv/bin/activate"
fi

exit 0
