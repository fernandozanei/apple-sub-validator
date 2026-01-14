#!/usr/bin/env python3
"""
Interactive Apple Subscription Validator
Easier interface for manual E2E testing
"""

from apple_subscription_validator import AppleSubscriptionValidator
import json
import os
from typing import Optional
from dotenv import load_dotenv

# Load environment variables at module level
load_dotenv()


def read_file_with_error_handling(prompt_text: str) -> Optional[str]:
    """
    Read file content with unified error handling

    Args:
        prompt_text: The prompt to display to the user

    Returns:
        File content as string or None if error occurred
    """
    filepath = input(prompt_text).strip()
    try:
        with open(filepath, 'r') as f:
            content = f.read().strip()
        print(f"✓ Read {len(content)} characters from file")
        return content
    except FileNotFoundError:
        print(f"✗ Error: File not found: {filepath}")
        return None
    except Exception as e:
        print(f"✗ Error reading file: {e}")
        return None


def save_result_to_file(result: dict, default_filename: str) -> None:
    """
    Prompt user to save result to file

    Args:
        result: The result dictionary to save
        default_filename: Default filename if user doesn't specify one
    """
    save = input("\nSave result to file? (y/n): ").strip().lower()
    if save == 'y':
        filename = input(f"Filename [{default_filename}]: ").strip() or default_filename
        with open(filename, 'w') as f:
            json.dump(result, f, indent=2)
        print(f"✓ Saved to {filename}")


def interactive_validate():
    """Interactive CLI for validation"""
    print("=" * 60)
    print("Apple Subscription Validator - Interactive Mode")
    print("=" * 60)
    
    # Step 1: Choose validation type
    print("\nWhat would you like to do?")
    print("1. Validate Base64 Receipt (receipt file) - legacy")
    print("2. Decode JWS Token (JWS token file) - local")
    print("3. Get Transaction Info (transaction ID)")
    print("4. Get Transaction History (original transaction ID)")
    print("5. Get All Subscription Statuses (original transaction ID)")
    print("6. Get App Transaction Info (app transaction ID)")
    print("7. Look Up Order ID (order ID)")
    choice = input("\nEnter choice (1-7): ").strip()
    
    if choice == "1":
        # Base64 receipt validation
        print("\n--- Base64 Receipt Validation ---")

        # Read receipt from file
        receipt_data = read_file_with_error_handling("\nEnter path to file containing receipt: ")
        if not receipt_data:
            return

        # Check if shared secret is in .env
        shared_secret_from_env = os.getenv('APPLE_SHARED_SECRET')
        if shared_secret_from_env:
            print(f"Using shared secret from .env")
            shared_secret = None  # Will use .env value
        else:
            shared_secret = input("Enter shared secret (press Enter to skip): ").strip() or None

        # Check if environment is already set in .env
        env_from_file = os.getenv('APPLE_ENVIRONMENT', '').lower()

        if env_from_file in ['sandbox', 'production']:
            print(f"Using environment from .env: {env_from_file}")
            sandbox = None  # Use .env default
        else:
            env = input("Environment (sandbox/production) [sandbox]: ").strip().lower() or "sandbox"
            sandbox = env == "sandbox"

        print("\nValidating...")
        validator = AppleSubscriptionValidator(shared_secret=shared_secret, sandbox=sandbox)
        result = validator.validate_base64_receipt(receipt_data)

        # Optionally save result
        save_result_to_file(result, "receipt_result.json")
    
    elif choice == "2":
        # JWS token validation
        print("\n--- JWS Token Validation ---")

        # Read JWS token from file
        jws_token = read_file_with_error_handling("\nEnter path to file containing JWS token: ")
        if not jws_token:
            return

        print("\nDecoding and validating...")
        validator = AppleSubscriptionValidator()
        result = validator.decode_jws_token(jws_token)

        # Optionally save result
        save_result_to_file(result, "jws_result.json")

    elif choice == "3":
        # Transaction ID lookup via Server API
        print("\n--- Transaction ID Lookup ---")

        transaction_id = input("\nEnter transaction ID: ").strip()

        if not transaction_id:
            print("✗ Transaction ID is required")
            return

        print("\nFetching transaction info...")
        validator = AppleSubscriptionValidator()
        result = validator.get_transaction_info(transaction_id)

        if result:
            # Optionally save result
            save_result_to_file(result, "transaction_result.json")

    elif choice == "4":
        # Transaction History lookup
        print("\n--- Transaction History Lookup ---")

        original_transaction_id = input("\nEnter original transaction ID: ").strip()

        if not original_transaction_id:
            print("✗ Original transaction ID is required")
            return

        # Optional filters
        print("\n--- Optional Filters (press Enter to skip) ---")
        sort_choice = input("Sort order (ASCENDING/DESCENDING) [DESCENDING]: ").strip().upper() or "DESCENDING"

        print("\nFetching transaction history...")
        validator = AppleSubscriptionValidator()
        result = validator.get_transaction_history(
            original_transaction_id=original_transaction_id,
            sort=sort_choice
        )

        if result:
            # Optionally save result
            save_result_to_file(result, "history_result.json")

    elif choice == "5":
        # Subscription Statuses lookup
        print("\n--- Subscription Statuses Lookup ---")

        original_transaction_id = input("\nEnter original transaction ID: ").strip()

        if not original_transaction_id:
            print("✗ Original transaction ID is required")
            return

        print("\nFetching subscription statuses...")
        validator = AppleSubscriptionValidator()
        result = validator.get_subscription_statuses(original_transaction_id)

        if result:
            # Optionally save result
            save_result_to_file(result, "subscription_result.json")

    elif choice == "6":
        # App Transaction Info lookup
        print("\n--- App Transaction Info Lookup ---")

        app_transaction_id = input("\nEnter app transaction ID: ").strip()

        if not app_transaction_id:
            print("✗ App transaction ID is required")
            return

        print("\nFetching app transaction info...")
        validator = AppleSubscriptionValidator()
        result = validator.get_app_transaction_info(app_transaction_id)

        if result:
            # Optionally save result
            save_result_to_file(result, "app_transaction_result.json")

    elif choice == "7":
        # Order ID lookup
        print("\n--- Order ID Lookup ---")

        order_id = input("\nEnter Order ID: ").strip()

        if not order_id:
            print("✗ Order ID is required")
            return

        print("\nLooking up order...")
        validator = AppleSubscriptionValidator()
        result = validator.lookup_order_id(order_id)

        if result:
            # Optionally save result
            save_result_to_file(result, "order_result.json")

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
