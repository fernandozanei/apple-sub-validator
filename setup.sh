#!/bin/bash
# Setup script for Apple Subscription Validator

echo "=========================================="
echo "Apple Subscription Validator - Setup"
echo "=========================================="
echo ""

# Check Python version
echo "Checking Python installation..."
if command -v python3 &> /dev/null; then
    PYTHON_CMD=python3
elif command -v python &> /dev/null; then
    PYTHON_CMD=python
else
    echo "❌ Error: Python not found!"
    echo "Please install Python 3.7 or higher"
    exit 1
fi

echo "✓ Found Python: $($PYTHON_CMD --version)"
echo ""

# Install dependencies
echo "Installing dependencies..."
echo ""

$PYTHON_CMD -m pip install -r requirements.txt

if [ $? -ne 0 ]; then
    echo ""
    echo "❌ Installation failed!"
    echo "Try running manually:"
    echo "  pip install -r requirements.txt"
    echo "Or:"
    echo "  pip3 install -r requirements.txt"
    exit 1
fi

echo ""
echo "✓ Dependencies installed"
echo ""

# Setup .env file
if [ ! -f .env ]; then
    echo "Creating .env file from template..."
    cp .env.example .env
    echo "✓ Created .env file"
    echo ""
    echo "⚠️  IMPORTANT: Edit .env file and add your Apple credentials:"
    echo "   - APPLE_SHARED_SECRET (for legacy receipt validation)"
    echo "   - APPLE_API_KEY, APPLE_KEY_ID, APPLE_ISSUER_ID (for new transaction API)"
    echo ""
else
    echo "✓ .env file already exists"
    echo ""
fi

echo "=========================================="
echo "✓ Setup Complete!"
echo "=========================================="
echo ""
echo "Next steps:"
echo "  1. Edit .env file with your Apple credentials"
echo "  2. Run the validator:"
echo "     $PYTHON_CMD validate_from_file.py receipt.txt"
echo "     $PYTHON_CMD interactive_validator.py"
echo ""
