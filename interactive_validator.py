#!/usr/bin/env python3
"""
Interactive Apple Subscription Validator
Easier interface for manual E2E testing
"""

from apple_subscription_validator import AppleSubscriptionValidator
import json


def interactive_validate():
    """Interactive CLI for validation"""
    print("=" * 60)
    print("Apple Subscription Validator - Interactive Mode")
    print("=" * 60)
    
    # Step 1: Choose validation type
    print("\nWhat would you like to validate?")
    print("1. Base64 Receipt (legacy)")
    print("2. JWS Token (new format)")
    choice = input("\nEnter choice (1 or 2): ").strip()
    
    if choice == "1":
        # Base64 receipt validation
        print("\n--- Base64 Receipt Validation ---")
        
        # Ask for input method
        print("\nHow would you like to provide the receipt?")
        print("1. Paste directly (for short receipts)")
        print("2. Read from file (recommended for long receipts)")
        input_method = input("\nEnter choice (1 or 2) [2]: ").strip() or "2"
        
        if input_method == "2":
            filepath = input("\nEnter path to file containing receipt: ").strip()
            try:
                with open(filepath, 'r') as f:
                    receipt_data = f.read().strip()
                print(f"✓ Read {len(receipt_data)} characters from file")
            except FileNotFoundError:
                print(f"✗ Error: File not found: {filepath}")
                return
            except Exception as e:
                print(f"✗ Error reading file: {e}")
                return
        else:
            receipt_data = input("\nPaste your base64 receipt: ").strip()
        
        shared_secret = input("Enter shared secret (press Enter to skip): ").strip() or None
        
        env = input("Environment (sandbox/production) [sandbox]: ").strip().lower() or "sandbox"
        sandbox = env == "sandbox"
        
        print("\nValidating...")
        validator = AppleSubscriptionValidator(shared_secret=shared_secret, sandbox=sandbox)
        result = validator.validate_base64_receipt(receipt_data)
        
        # Optionally save result
        save = input("\nSave result to file? (y/n): ").strip().lower()
        if save == 'y':
            filename = input("Filename [receipt_result.json]: ").strip() or "receipt_result.json"
            with open(filename, 'w') as f:
                json.dump(result, f, indent=2)
            print(f"✓ Saved to {filename}")
    
    elif choice == "2":
        # JWS token validation
        print("\n--- JWS Token Validation ---")
        
        # Ask for input method
        print("\nHow would you like to provide the token?")
        print("1. Paste directly (for short tokens)")
        print("2. Read from file (recommended for long tokens)")
        input_method = input("\nEnter choice (1 or 2) [2]: ").strip() or "2"
        
        if input_method == "2":
            filepath = input("\nEnter path to file containing JWS token: ").strip()
            try:
                with open(filepath, 'r') as f:
                    jws_token = f.read().strip()
                print(f"✓ Read {len(jws_token)} characters from file")
            except FileNotFoundError:
                print(f"✗ Error: File not found: {filepath}")
                return
            except Exception as e:
                print(f"✗ Error reading file: {e}")
                return
        else:
            jws_token = input("\nPaste your JWS token: ").strip()
        
        print("\nDecoding and validating...")
        validator = AppleSubscriptionValidator()
        result = validator.decode_jws_token(jws_token)
        
        # Optionally save result
        save = input("\nSave result to file? (y/n): ").strip().lower()
        if save == 'y':
            filename = input("Filename [jws_result.json]: ").strip() or "jws_result.json"
            with open(filename, 'w') as f:
                json.dump(result, f, indent=2)
            print(f"✓ Saved to {filename}")
    
    else:
        print("Invalid choice!")
        return
    
    print("\n" + "=" * 60)
    print("Validation complete!")
    print("=" * 60)


if __name__ == "__main__":
    try:
        interactive_validate()
    except KeyboardInterrupt:
        print("\n\nExiting...")
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
