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

$PYTHON_CMD -m pip install PyJWT[crypto]==2.8.0 cryptography==41.0.7 requests==2.31.0

if [ $? -eq 0 ]; then
    echo ""
    echo "=========================================="
    echo "✓ Setup Complete!"
    echo "=========================================="
    echo ""
    echo "You can now run:"
    echo "  $PYTHON_CMD validate_from_file.py receipt.txt 'your_secret'"
    echo "  $PYTHON_CMD interactive_validator.py"
    echo ""
else
    echo ""
    echo "❌ Installation failed!"
    echo "Try running manually:"
    echo "  pip install PyJWT[crypto] cryptography requests"
    echo "Or:"
    echo "  pip3 install PyJWT[crypto] cryptography requests"
    exit 1
fi
