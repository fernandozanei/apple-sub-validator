#!/usr/bin/env python3
"""
Apple Subscription Validator
Validates both legacy base64 receipts and new JWS signed tokens
"""

import base64
import json
import os
import sys
import time
from typing import Dict, Any, Optional
import jwt
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.backends import default_backend
from cryptography.x509 import load_pem_x509_certificate
import requests
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class AppleSubscriptionValidator:
    
    # Apple's App Store Server API endpoints
    SANDBOX_URL = "https://api.storekit-sandbox.itunes.apple.com/inApps/v1/subscriptions/"
    PRODUCTION_URL = "https://api.storekit.itunes.apple.com/inApps/v1/subscriptions/"
    
    # Apple's root certificate URL (for JWS verification)
    APPLE_ROOT_CA_URL = "https://www.apple.com/certificateauthority/AppleRootCA-G3.cer"
    
    def __init__(self, shared_secret: Optional[str] = None, sandbox: Optional[bool] = None):
        """
        Initialize validator

        Args:
            shared_secret: Your app's shared secret (for receipt validation)
                          If not provided, reads from APPLE_SHARED_SECRET env var
            sandbox: Whether to use sandbox environment
                    If not provided, reads from APPLE_ENVIRONMENT env var
        """
        # Use provided value, fall back to environment variable, or use None
        self.shared_secret = shared_secret or os.getenv('APPLE_SHARED_SECRET')

        # Determine environment: use provided value, check env var, default to sandbox
        if sandbox is not None:
            self.sandbox = sandbox
        else:
            env = os.getenv('APPLE_ENVIRONMENT', 'sandbox').lower()
            self.sandbox = env == 'sandbox'

        # Load API credentials for transaction API
        self.api_key = os.getenv('APPLE_API_KEY')
        self.key_id = os.getenv('APPLE_KEY_ID')
        self.issuer_id = os.getenv('APPLE_ISSUER_ID')
        self.bundle_id = os.getenv('APPLE_BUNDLE_ID')

    @staticmethod
    def _format_date(timestamp_ms: int) -> str:
        """
        Convert millisecond timestamp to readable date string in UTC

        Args:
            timestamp_ms: Timestamp in milliseconds

        Returns:
            Formatted date string in UTC (YYYY-MM-DD HH:MM:SS UTC)
        """
        from datetime import datetime
        return datetime.utcfromtimestamp(timestamp_ms / 1000).strftime('%Y-%m-%d %H:%M:%S UTC')

    @staticmethod
    def _format_transaction_dates(transaction: Dict[str, Any]) -> Dict[str, Any]:
        """
        Format all date fields in a transaction dictionary

        Args:
            transaction: Transaction dictionary with millisecond timestamps

        Returns:
            Transaction dictionary with formatted date strings
        """
        # Comprehensive list of all date fields from Apple's App Store Server API
        date_fields = [
            # Transaction date fields
            'purchaseDate',
            'originalPurchaseDate',
            'expiresDate',
            'revocationDate',
            'signedDate',

            # Subscription date fields
            'gracePeriodExpiresDate',
            'renewalDate',
            'recentSubscriptionStartDate',
            'subscriptionStartDate',

            # Offer date fields
            'offerDiscountStartDate',
            'offerDiscountEndDate',

            # Billing and retry date fields
            'billingRetryPeriodStartDate',
            'billingRetryPeriodEndDate',

            # Other date fields
            'effectiveDate',
            'priceIncreaseDate',
            'appAccountTokenCreationDate',
        ]

        # Create a copy to avoid modifying the original
        formatted_transaction = transaction.copy()

        for field in date_fields:
            if field in formatted_transaction and formatted_transaction[field]:
                try:
                    formatted_transaction[field] = AppleSubscriptionValidator._format_date(formatted_transaction[field])
                except (TypeError, ValueError, KeyError):
                    # Keep original value if formatting fails
                    pass

        return formatted_transaction

    def _generate_jwt_token(self) -> Optional[str]:
        """
        Generate JWT token for Apple App Store Server API authentication

        Returns:
            JWT token string or None if credentials are missing
        """
        if not all([self.api_key, self.key_id, self.issuer_id]):
            print("⚠ Warning: Missing API credentials (APPLE_API_KEY, APPLE_KEY_ID, or APPLE_ISSUER_ID)")
            return None

        # Token valid for 20 minutes (Apple's maximum)
        issued_at = int(time.time())
        expiration_time = issued_at + (20 * 60)

        headers = {
            "alg": "ES256",
            "kid": self.key_id,
            "typ": "JWT"
        }

        payload = {
            "iss": self.issuer_id,
            "iat": issued_at,
            "exp": expiration_time,
            "aud": "appstoreconnect-v1"
        }

        # Add bundle_id if available (required for some endpoints)
        if self.bundle_id:
            payload["bid"] = self.bundle_id

        try:
            token = jwt.encode(
                payload,
                self.api_key,
                algorithm="ES256",
                headers=headers
            )
            return token
        except Exception as e:
            print(f"✗ Error generating JWT token: {e}")
            return None

    def _decode_and_verify_jws(self, jws_token: str, token_type: str = "Token") -> Optional[Dict[str, Any]]:
        """
        Decode and verify a JWS token with signature validation

        Args:
            jws_token: The JWS token string
            token_type: Description of the token type (for display)

        Returns:
            Decoded and verified payload, or None if verification fails
        """
        try:
            # Decode without verification first (to inspect)
            unverified_header = jwt.get_unverified_header(jws_token)
            unverified_payload = jwt.decode(jws_token, options={"verify_signature": False})

            print(f"\n=== Decoding {token_type} JWS ===")
            print("\n--- Header ---")
            print(json.dumps(unverified_header, indent=2))

            print("\n--- Payload (Unverified) ---")
            print(json.dumps(unverified_payload, indent=2))

            # Extract key info from header
            x5c = unverified_header.get('x5c', [])
            if not x5c:
                print(f"\n⚠ Warning: No x5c (certificate chain) found in {token_type} header")
                print("Cannot verify signature, returning unverified payload")
                return self._format_transaction_dates(unverified_payload)

            # Load the signing certificate from x5c[0]
            cert_der = base64.b64decode(x5c[0])
            cert = load_pem_x509_certificate(
                b"-----BEGIN CERTIFICATE-----\n" +
                base64.b64encode(cert_der) +
                b"\n-----END CERTIFICATE-----\n",
                default_backend()
            )

            # Extract public key
            public_key = cert.public_key()

            # Verify signature
            try:
                verified_payload = jwt.decode(
                    jws_token,
                    public_key,
                    algorithms=["ES256"],  # Apple uses ES256
                    options={"verify_exp": True}
                )
                print(f"\n✓ {token_type} Signature verification: PASSED")

                # Display transaction details in a formatted way
                self._display_transaction_details(verified_payload)

                # Format dates before returning
                return self._format_transaction_dates(verified_payload)

            except jwt.ExpiredSignatureError:
                print(f"\n⚠ {token_type} has expired (but signature is valid)")
                self._display_transaction_details(unverified_payload)
                # Format dates before returning
                return self._format_transaction_dates(unverified_payload)

            except jwt.InvalidSignatureError:
                print(f"\n✗ {token_type} signature verification: FAILED")
                print("Returning unverified payload (signature invalid)")
                return self._format_transaction_dates(unverified_payload)

        except Exception as e:
            print(f"\n✗ Error decoding {token_type}: {e}")
            return None

    def _display_transaction_details(self, transaction: Dict[str, Any]):
        """Display formatted transaction details"""
        from datetime import datetime

        print("\n--- Transaction Details ---")

        # Basic info
        if transaction.get('productId'):
            print(f"Product ID: {transaction.get('productId')}")
        if transaction.get('bundleId'):
            print(f"Bundle ID: {transaction.get('bundleId')}")
        if transaction.get('transactionId'):
            print(f"Transaction ID: {transaction.get('transactionId')}")
        if transaction.get('originalTransactionId'):
            print(f"Original Transaction ID: {transaction.get('originalTransactionId')}")
        if transaction.get('webOrderLineItemId'):
            print(f"Web Order Line Item ID: {transaction.get('webOrderLineItemId')}")

        # Subscription group
        if transaction.get('subscriptionGroupIdentifier'):
            print(f"Subscription Group ID: {transaction.get('subscriptionGroupIdentifier')}")

        # Dates
        purchase_date = transaction.get('purchaseDate')
        if purchase_date:
            print(f"Purchase Date: {datetime.fromtimestamp(purchase_date/1000).strftime('%Y-%m-%d %H:%M:%S')}")

        original_purchase_date = transaction.get('originalPurchaseDate')
        if original_purchase_date:
            print(f"Original Purchase Date: {datetime.fromtimestamp(original_purchase_date/1000).strftime('%Y-%m-%d %H:%M:%S')}")

        expires_date = transaction.get('expiresDate')
        if expires_date:
            print(f"Expires Date: {datetime.fromtimestamp(expires_date/1000).strftime('%Y-%m-%d %H:%M:%S')}")

        # Type and status
        if transaction.get('type'):
            print(f"Type: {transaction.get('type')}")
        if transaction.get('environment'):
            print(f"Environment: {transaction.get('environment')}")
        if transaction.get('inAppOwnershipType'):
            print(f"Ownership Type: {transaction.get('inAppOwnershipType')}")

        # Offer information
        if transaction.get('offerType'):
            print(f"Offer Type: {transaction.get('offerType')}")
        if transaction.get('offerDiscountType'):
            print(f"Offer Discount Type: {transaction.get('offerDiscountType')}")
        if transaction.get('offerIdentifier'):
            print(f"Offer Identifier: {transaction.get('offerIdentifier')}")
        if transaction.get('offerPeriod'):
            print(f"Offer Period: {transaction.get('offerPeriod')}")

        # Pricing
        if transaction.get('price') is not None:
            print(f"Price: {transaction.get('price')}")
        if transaction.get('currency'):
            print(f"Currency: {transaction.get('currency')}")

        # Store information
        if transaction.get('storefront'):
            print(f"Storefront: {transaction.get('storefront')}")
        if transaction.get('storefrontId'):
            print(f"Storefront ID: {transaction.get('storefrontId')}")

        # Transaction reason
        if transaction.get('transactionReason'):
            print(f"Transaction Reason: {transaction.get('transactionReason')}")

        # Quantity
        if transaction.get('quantity'):
            print(f"Quantity: {transaction.get('quantity')}")

        # App transaction ID
        if transaction.get('appTransactionId'):
            print(f"App Transaction ID: {transaction.get('appTransactionId')}")

    def _get_base_url(self) -> str:
        """
        Get the appropriate API base URL based on environment

        Returns:
            Base URL for Apple App Store Server API
        """
        return ("https://api.storekit-sandbox.itunes.apple.com" if self.sandbox
                else "https://api.storekit.itunes.apple.com")

    def _make_api_request(self, endpoint: str, resource_type: str = "Resource", params: Optional[Dict] = None) -> tuple:
        """
        Make an API request to Apple App Store Server API with standardized error handling

        Args:
            endpoint: API endpoint path (e.g., "/inApps/v1/transactions/12345")
            resource_type: Description of the resource being fetched (for error messages)
            params: Optional query parameters dictionary

        Returns:
            Tuple of (success: bool, data: Optional[Dict], should_retry: bool)
        """
        # Generate JWT token
        token = self._generate_jwt_token()
        if not token:
            return False, None, False

        # Build full URL
        base_url = self._get_base_url()
        url = f"{base_url}{endpoint}"

        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }

        try:
            response = requests.get(url, headers=headers, params=params)

            if response.status_code == 200:
                return True, response.json(), False
            elif response.status_code == 401:
                print("✗ Error 401: Unauthorized - Check your API credentials")
                return False, None, False
            elif response.status_code == 404:
                print(f"✗ Error 404: {resource_type} not found")
                return False, None, True  # Should retry with alternate environment
            else:
                print(f"✗ Error {response.status_code}: {response.text}")
                return False, None, False

        except Exception as e:
            print(f"✗ Request failed: {e}")
            return False, None, False

    def _retry_with_alternate_environment(self, method_name: str, retry_callable, *args, **kwargs) -> Optional[Dict[str, Any]]:
        """
        Retry an API call with the alternate environment (sandbox ↔ production)

        Args:
            method_name: Name of the method being retried (for logging)
            retry_callable: The method to call for retry
            *args: Positional arguments to pass to the method
            **kwargs: Keyword arguments to pass to the method

        Returns:
            Result from retry or None if retry also fails
        """
        other_env = "sandbox" if not self.sandbox else "production"
        print(f"\n⚠ Trying {other_env} environment...")
        self.sandbox = not self.sandbox
        return retry_callable(*args, **kwargs)

    def _decode_transaction_list(self, signed_transactions: list, description: str = "Transaction") -> list:
        """
        Decode a list of signed transactions

        Args:
            signed_transactions: List of signed transaction JWS tokens
            description: Description prefix for logging (e.g., "Transaction")

        Returns:
            List of decoded transaction dictionaries
        """
        decoded_list = []
        for idx, signed_transaction in enumerate(signed_transactions, 1):
            print(f"\n--- Decoding {description} {idx}/{len(signed_transactions)} ---")
            decoded = self._decode_and_verify_jws(signed_transaction, f"{description} {idx}")
            if decoded:
                decoded_list.append(decoded)
        return decoded_list

    def get_transaction_info(self, transaction_id: str, _retry_attempted: bool = False) -> Optional[Dict[str, Any]]:
        """
        Get transaction information from Apple App Store Server API

        Args:
            transaction_id: The transaction ID to query
            _retry_attempted: Internal flag to prevent infinite retry loops

        Returns:
            Transaction data or None if failed
        """
        print("\n=== Fetching Transaction Info ===")
        print(f"Transaction ID: {transaction_id}")
        print(f"Environment: {'sandbox' if self.sandbox else 'production'}")

        # Make API request using helper
        success, data, should_retry = self._make_api_request(
            f"/inApps/v1/transactions/{transaction_id}",
            "Transaction"
        )

        if success:
            print("✓ Transaction found!")

            # Decode and verify the signedTransaction if present
            signed_transaction = data.get('signedTransactionInfo') or data.get('signedTransaction')
            if signed_transaction:
                decoded_transaction = self._decode_and_verify_jws(signed_transaction, "Transaction")
                if decoded_transaction:
                    data['decodedTransaction'] = decoded_transaction

            return data

        elif should_retry and not _retry_attempted:
            return self._retry_with_alternate_environment(
                'get_transaction_info',
                self.get_transaction_info,
                transaction_id,
                _retry_attempted=True
            )
        else:
            if _retry_attempted:
                print("✗ Transaction not found in both environments")
            return None

    def get_transaction_history(self, original_transaction_id: str,
                                revision: Optional[str] = None,
                                start_date: Optional[int] = None,
                                end_date: Optional[int] = None,
                                product_type: Optional[str] = None,
                                sort: str = "DESCENDING",
                                _retry_attempted: bool = False) -> Optional[Dict[str, Any]]:
        """
        Get all transaction history for an original transaction ID

        Args:
            original_transaction_id: The original transaction ID (first purchase)
            revision: Pagination token (optional)
            start_date: Filter by start date in milliseconds (optional)
            end_date: Filter by end date in milliseconds (optional)
            product_type: Filter by product type (AUTO_RENEWABLE, NON_CONSUMABLE, etc.) (optional)
            sort: ASCENDING or DESCENDING (default: DESCENDING)
            _retry_attempted: Internal flag to prevent infinite retry loops

        Returns:
            Transaction history data with all signedTransactions decoded, or None if failed
        """
        print("\n=== Fetching Transaction History ===")
        print(f"Original Transaction ID: {original_transaction_id}")
        print(f"Environment: {'sandbox' if self.sandbox else 'production'}")
        print(f"Sort: {sort}")

        # Build query parameters
        params = {'sort': sort}
        if revision:
            params['revision'] = revision
        if start_date:
            params['startDate'] = start_date
        if end_date:
            params['endDate'] = end_date
        if product_type:
            params['productType'] = product_type

        # Make API request using helper
        success, data, should_retry = self._make_api_request(
            f"/inApps/v1/history/{original_transaction_id}",
            "Transaction history",
            params=params
        )

        if success:
            signed_transactions = data.get('signedTransactions', [])
            print(f"✓ Found {len(signed_transactions)} transactions!")

            # Decode all signed transactions using helper
            data['decodedTransactions'] = self._decode_transaction_list(signed_transactions, "Transaction")

            # Check if there are more pages
            if data.get('hasMore', False):
                print(f"\n⚠ More transactions available. Use revision '{data.get('revision')}' to fetch next page.")

            return data

        elif should_retry and not _retry_attempted:
            return self._retry_with_alternate_environment(
                'get_transaction_history',
                self.get_transaction_history,
                original_transaction_id, revision, start_date, end_date, product_type, sort,
                _retry_attempted=True
            )
        else:
            if _retry_attempted:
                print("✗ Transaction history not found in both environments")
            return None

    def get_subscription_statuses(self, original_transaction_id: str, _retry_attempted: bool = False) -> Optional[Dict[str, Any]]:
        """
        Get all subscription statuses for an original transaction ID

        Args:
            original_transaction_id: The original transaction ID
            _retry_attempted: Internal flag to prevent infinite retry loops

        Returns:
            Subscription status data with decoded information, or None if failed
        """
        print("\n=== Fetching Subscription Statuses ===")
        print(f"Original Transaction ID: {original_transaction_id}")
        print(f"Environment: {'sandbox' if self.sandbox else 'production'}")

        # Make API request using helper
        success, data, should_retry = self._make_api_request(
            f"/inApps/v1/subscriptions/{original_transaction_id}",
            "Subscription"
        )

        if success:
            print("✓ Subscription status found!")

            # Decode subscriptionGroupIdentifier items
            subscription_items = data.get('data', [])

            for item_idx, item in enumerate(subscription_items, 1):
                print(f"\n=== Subscription Group {item_idx} ===")

                # Decode lastTransactions
                last_transactions = item.get('lastTransactions', [])
                decoded_last_transactions = []

                for trans_idx, trans in enumerate(last_transactions, 1):
                    signed_transaction_info = trans.get('signedTransactionInfo')
                    signed_renewal_info = trans.get('signedRenewalInfo')

                    decoded_trans = {}

                    if signed_transaction_info:
                        print(f"\n--- Last Transaction {trans_idx} - Transaction Info ---")
                        decoded_transaction = self._decode_and_verify_jws(signed_transaction_info, "Transaction")
                        if decoded_transaction:
                            decoded_trans['decodedTransactionInfo'] = decoded_transaction

                    if signed_renewal_info:
                        print(f"\n--- Last Transaction {trans_idx} - Renewal Info ---")
                        decoded_renewal = self._decode_and_verify_jws(signed_renewal_info, "Renewal")
                        if decoded_renewal:
                            decoded_trans['decodedRenewalInfo'] = decoded_renewal

                    if decoded_trans:
                        decoded_last_transactions.append(decoded_trans)

                # Add decoded data to item
                if decoded_last_transactions:
                    item['decodedLastTransactions'] = decoded_last_transactions

            return data

        elif should_retry and not _retry_attempted:
            return self._retry_with_alternate_environment(
                'get_subscription_statuses',
                self.get_subscription_statuses,
                original_transaction_id,
                _retry_attempted=True
            )
        else:
            if _retry_attempted:
                print("✗ Subscription not found in both environments")
            return None

    def get_app_transaction_info(self, app_transaction_id: str, _retry_attempted: bool = False) -> Optional[Dict[str, Any]]:
        """
        Get app transaction information (verifies if app was downloaded from App Store)

        Args:
            app_transaction_id: The app transaction ID
            _retry_attempted: Internal flag to prevent infinite retry loops

        Returns:
            App transaction data with decoded information, or None if failed
        """
        print("\n=== Fetching App Transaction Info ===")
        print(f"App Transaction ID: {app_transaction_id}")
        print(f"Environment: {'sandbox' if self.sandbox else 'production'}")

        # Make API request using helper
        success, data, should_retry = self._make_api_request(
            f"/inApps/v1/appTransactions/{app_transaction_id}",
            "App transaction"
        )

        if success:
            print("✓ App transaction found!")

            # Decode the signedAppTransaction if present
            signed_app_transaction = data.get('signedAppTransaction')
            if signed_app_transaction:
                decoded_app_transaction = self._decode_and_verify_jws(signed_app_transaction, "App Transaction")
                if decoded_app_transaction:
                    data['decodedAppTransaction'] = decoded_app_transaction

            return data

        elif should_retry and not _retry_attempted:
            return self._retry_with_alternate_environment(
                'get_app_transaction_info',
                self.get_app_transaction_info,
                app_transaction_id,
                _retry_attempted=True
            )
        else:
            if _retry_attempted:
                print("✗ App transaction not found in both environments")
            return None

    def lookup_order_id(self, order_id: str, _retry_attempted: bool = False) -> Optional[Dict[str, Any]]:
        """
        Look up transactions by Order ID (Customer Order Number)

        Args:
            order_id: The Order ID from the customer's purchase
            _retry_attempted: Internal flag to prevent infinite retry loops

        Returns:
            Order lookup data with all decoded transactions, or None if failed
        """
        print("\n=== Looking Up Order ID ===")
        print(f"Order ID: {order_id}")
        print(f"Environment: {'sandbox' if self.sandbox else 'production'}")

        # Make API request using helper
        success, data, should_retry = self._make_api_request(
            f"/inApps/v1/lookup/{order_id}",
            "Order"
        )

        if success:
            signed_transactions = data.get('signedTransactions', [])
            print(f"✓ Found {len(signed_transactions)} transactions for this order!")

            # Decode all signed transactions using helper
            data['decodedTransactions'] = self._decode_transaction_list(signed_transactions, "Transaction")

            return data

        elif should_retry and not _retry_attempted:
            return self._retry_with_alternate_environment(
                'lookup_order_id',
                self.lookup_order_id,
                order_id,
                _retry_attempted=True
            )
        else:
            if _retry_attempted:
                print("✗ Order not found in both environments")
            return None

    def validate_base64_receipt(self, receipt_data: str) -> Dict[str, Any]:
        """
        Validate legacy base64-encoded receipt
        
        Args:
            receipt_data: Base64-encoded receipt string
            
        Returns:
            Validation response from Apple
        """
        print("\n=== Validating Base64 Receipt ===")
        
        # Determine endpoint
        verify_url = (
            "https://sandbox.itunes.apple.com/verifyReceipt" if self.sandbox 
            else "https://buy.itunes.apple.com/verifyReceipt"
        )
        
        # Prepare request payload
        payload = {
            "receipt-data": receipt_data,
            "exclude-old-transactions": False
        }
        
        if self.shared_secret:
            payload["password"] = self.shared_secret
        
        print(f"Sending request to: {verify_url}")
        
        # Send verification request
        response = requests.post(verify_url, json=payload)
        result = response.json()
        
        # Parse status
        status = result.get("status")
        status_messages = {
            0: "✓ Valid receipt",
            21000: "✗ The App Store could not read the JSON object you provided",
            21002: "✗ The data in the receipt-data property was malformed or missing",
            21003: "✗ The receipt could not be authenticated",
            21004: "✗ The shared secret you provided does not match",
            21005: "✗ The receipt server is not currently available",
            21006: "✗ This receipt is valid but the subscription has expired",
            21007: "✗ This receipt is from the sandbox but was sent to production",
            21008: "✗ This receipt is from production but was sent to sandbox",
            21009: "✗ Internal data access error",
            21010: "✗ The user account cannot be found or has been deleted"
        }
        
        print(f"\nStatus: {status} - {status_messages.get(status, 'Unknown status')}")
        
        # If sandbox receipt sent to production, retry with sandbox
        if status == 21007 and not self.sandbox:
            print("\n⚠ Receipt is from sandbox, retrying with sandbox endpoint...")
            self.sandbox = True
            return self.validate_base64_receipt(receipt_data)
        
        # Display subscription info if valid
        if status == 0 or status == 21006:
            self._display_receipt_info(result)
        
        return result
    
    def decode_jws_token(self, jws_token: str) -> Dict[str, Any]:
        """
        Decode and validate JWS signed token (App Store Server Notifications V2)
        
        Args:
            jws_token: The JWS token string
            
        Returns:
            Decoded payload
        """
        print("\n=== Decoding JWS Token ===")
        
        try:
            # Decode without verification first (to inspect)
            unverified_header = jwt.get_unverified_header(jws_token)
            unverified_payload = jwt.decode(jws_token, options={"verify_signature": False})
            
            print("\n--- Unverified Header ---")
            print(json.dumps(unverified_header, indent=2))
            
            print("\n--- Unverified Payload ---")
            print(json.dumps(unverified_payload, indent=2))
            
            # Extract key info from header
            x5c = unverified_header.get('x5c', [])
            if not x5c:
                print("\n⚠ Warning: No x5c (certificate chain) found in header")
                return self._format_transaction_dates(unverified_payload)

            # Load the signing certificate from x5c[0]
            cert_der = base64.b64decode(x5c[0])
            cert = load_pem_x509_certificate(
                b"-----BEGIN CERTIFICATE-----\n" +
                base64.b64encode(cert_der) +
                b"\n-----END CERTIFICATE-----\n",
                default_backend()
            )

            # Extract public key
            public_key = cert.public_key()

            # Verify signature
            try:
                verified_payload = jwt.decode(
                    jws_token,
                    public_key,
                    algorithms=["ES256"],  # Apple uses ES256
                    options={"verify_exp": True}
                )
                print("\n✓ Signature verification: PASSED")

                # Format dates before displaying and returning
                formatted_payload = self._format_transaction_dates(verified_payload)

                print("\n--- Verified Payload ---")
                print(json.dumps(formatted_payload, indent=2))

                self._display_jws_info(formatted_payload)

                return formatted_payload

            except jwt.ExpiredSignatureError:
                print("\n✗ Token has expired")
                formatted_payload = self._format_transaction_dates(unverified_payload)
                return formatted_payload
            except jwt.InvalidSignatureError:
                print("\n✗ Invalid signature")
                formatted_payload = self._format_transaction_dates(unverified_payload)
                return formatted_payload
                
        except Exception as e:
            print(f"\n✗ Error decoding JWS token: {e}")
            raise
    
    def _display_receipt_info(self, receipt_data: Dict[str, Any]):
        """Display formatted receipt information"""
        print("\n--- Receipt Information ---")
        
        receipt = receipt_data.get("receipt", {})
        print(f"Bundle ID: {receipt.get('bundle_id')}")
        print(f"Application Version: {receipt.get('application_version')}")
        
        # Display in-app purchases
        in_app = receipt.get("in_app", [])
        latest_receipt_info = receipt_data.get("latest_receipt_info", [])
        pending_renewal_info = receipt_data.get("pending_renewal_info", [])
        
        if latest_receipt_info:
            print("\n--- Latest Subscription Info ---")
            for sub in latest_receipt_info:
                print(f"\nProduct ID: {sub.get('product_id')}")
                print(f"Transaction ID: {sub.get('transaction_id')}")
                print(f"Original Transaction ID: {sub.get('original_transaction_id')}")
                print(f"Purchase Date: {sub.get('purchase_date')}")
                print(f"Expires Date: {sub.get('expires_date')}")
                print(f"Is Trial Period: {sub.get('is_trial_period')}")
                print(f"Is in Intro Offer Period: {sub.get('is_in_intro_offer_period')}")
        
        if pending_renewal_info:
            print("\n--- Renewal Status ---")
            for renewal in pending_renewal_info:
                print(f"\nAuto Renew Status: {renewal.get('auto_renew_status')}")
                print(f"Auto Renew Product ID: {renewal.get('auto_renew_product_id')}")
                print(f"Expiration Intent: {renewal.get('expiration_intent', 'N/A')}")
    
    def _display_jws_info(self, payload: Dict[str, Any]):
        """Display formatted JWS token information"""
        print("\n--- JWS Token Information ---")
        
        notification_type = payload.get("notificationType")
        subtype = payload.get("subtype")
        
        print(f"Notification Type: {notification_type}")
        if subtype:
            print(f"Subtype: {subtype}")
        
        # Parse signedTransactionInfo if present
        if "data" in payload and "signedTransactionInfo" in payload["data"]:
            signed_transaction = payload["data"]["signedTransactionInfo"]
            try:
                transaction = jwt.decode(signed_transaction, options={"verify_signature": False})
                print("\n--- Transaction Info ---")
                print(f"Product ID: {transaction.get('productId')}")
                print(f"Transaction ID: {transaction.get('transactionId')}")
                print(f"Original Transaction ID: {transaction.get('originalTransactionId')}")
                print(f"Purchase Date: {transaction.get('purchaseDate')}")
                print(f"Expires Date: {transaction.get('expiresDate')}")
            except (jwt.DecodeError, KeyError) as e:
                # Failed to decode transaction info
                pass
        
        # Parse signedRenewalInfo if present
        if "data" in payload and "signedRenewalInfo" in payload["data"]:
            signed_renewal = payload["data"]["signedRenewalInfo"]
            try:
                renewal = jwt.decode(signed_renewal, options={"verify_signature": False})
                print("\n--- Renewal Info ---")
                print(f"Auto Renew Status: {renewal.get('autoRenewStatus')}")
                print(f"Expiration Intent: {renewal.get('expirationIntent', 'N/A')}")
            except (jwt.DecodeError, KeyError) as e:
                # Failed to decode renewal info
                pass


def main():
    """Main function for CLI usage"""
    print("Apple Subscription Validator")
    print("=" * 50)
    
    if len(sys.argv) < 2:
        print("\nUsage:")
        print("  python apple_subscription_validator.py <receipt_or_token> [shared_secret] [--production]")
        print("\nExamples:")
        print("  # Validate base64 receipt (sandbox)")
        print("  python apple_subscription_validator.py 'MIITt...' 'your_shared_secret'")
        print("\n  # Validate JWS token")
        print("  python apple_subscription_validator.py 'eyJhb...'")
        print("\n  # Use production environment")
        print("  python apple_subscription_validator.py 'MIITt...' 'secret' --production")
        sys.exit(1)
    
    receipt_or_token = sys.argv[1]
    shared_secret = sys.argv[2] if len(sys.argv) > 2 and not sys.argv[2].startswith('--') else None
    sandbox = '--production' not in sys.argv
    
    validator = AppleSubscriptionValidator(shared_secret=shared_secret, sandbox=sandbox)
    
    # Determine if it's a JWS token (starts with eyJ) or base64 receipt
    if receipt_or_token.startswith('eyJ'):
        # JWS token
        validator.decode_jws_token(receipt_or_token)
    else:
        # Base64 receipt
        validator.validate_base64_receipt(receipt_or_token)


if __name__ == "__main__":
    main()
