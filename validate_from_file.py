#!/usr/bin/env python3
"""
Apple Subscription Validator - File Input Version
Reads receipt/token from files to avoid terminal paste limitations
"""

import sys
import os
from apple_subscription_validator import AppleSubscriptionValidator


def validate_from_file(filepath: str, shared_secret: str = None, sandbox: bool = None):
    """
    Validate receipt or token from a file

    Args:
        filepath: Path to file containing receipt or token
        shared_secret: Shared secret for receipt validation (falls back to .env)
        sandbox: Whether to use sandbox environment (falls back to .env)
    """
    print(f"Reading from file: {filepath}")
    
    if not os.path.exists(filepath):
        print(f"✗ Error: File not found: {filepath}")
        return
    
    # Read the content
    with open(filepath, 'r') as f:
        content = f.read().strip()
    
    print(f"Read {len(content)} characters")
    
    # Create validator
    validator = AppleSubscriptionValidator(shared_secret=shared_secret, sandbox=sandbox)

    # Detect type and validate
    if content.startswith('eyJ'):
        print("Detected: JWS Token")
        validator.decode_jws_token(content)
    elif content.isdigit():
        print("Detected: Transaction ID")
        validator.get_transaction_info(content)
    else:
        print("Detected: Base64 Receipt")
        validator.validate_base64_receipt(content)


def main():
    print("Apple Subscription Validator - File Input")
    print("=" * 60)
    
    if len(sys.argv) < 2:
        print("\nUsage:")
        print("  python validate_from_file.py <filepath> [shared_secret] [--production]")
        print("\nExamples:")
        print("  python validate_from_file.py receipt.txt")
        print("  python validate_from_file.py receipt.txt 'your_shared_secret'")
        print("  python validate_from_file.py jws_token.txt --production")
        print("  python validate_from_file.py transaction_id.txt")
        print("\nFile format:")
        print("  - Create a text file containing only:")
        print("    * Base64 receipt string")
        print("    * JWS token (starts with 'eyJ')")
        print("    * Transaction ID (numeric)")
        print("  - No extra spaces or newlines")
        print("  - Just paste the string/number and save")
        sys.exit(1)
    
    filepath = sys.argv[1]
    shared_secret = None
    sandbox = None  # Will use .env default

    # Parse arguments
    for arg in sys.argv[2:]:
        if arg == '--production':
            sandbox = False
        elif arg == '--sandbox':
            sandbox = True
        elif not arg.startswith('--'):
            shared_secret = arg
    
    validate_from_file(filepath, shared_secret, sandbox)


if __name__ == "__main__":
    main()
