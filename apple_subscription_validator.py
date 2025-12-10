#!/usr/bin/env python3
"""
Apple Subscription Validator
Validates both legacy base64 receipts and new JWS signed tokens
"""

import base64
import json
import sys
from typing import Dict, Any, Optional
import jwt
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.backends import default_backend
from cryptography.x509 import load_pem_x509_certificate
import requests


class AppleSubscriptionValidator:
    
    # Apple's App Store Server API endpoints
    SANDBOX_URL = "https://api.storekit-sandbox.itunes.apple.com/inApps/v1/subscriptions/"
    PRODUCTION_URL = "https://api.storekit.itunes.apple.com/inApps/v1/subscriptions/"
    
    # Apple's root certificate URL (for JWS verification)
    APPLE_ROOT_CA_URL = "https://www.apple.com/certificateauthority/AppleRootCA-G3.cer"
    
    def __init__(self, shared_secret: Optional[str] = None, sandbox: bool = True):
        """
        Initialize validator
        
        Args:
            shared_secret: Your app's shared secret (for receipt validation)
            sandbox: Whether to use sandbox environment
        """
        self.shared_secret = shared_secret
        self.sandbox = sandbox
        
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
                return unverified_payload
            
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
                print("\n--- Verified Payload ---")
                print(json.dumps(verified_payload, indent=2))
                
                self._display_jws_info(verified_payload)
                
                return verified_payload
                
            except jwt.ExpiredSignatureError:
                print("\n✗ Token has expired")
                return unverified_payload
            except jwt.InvalidSignatureError:
                print("\n✗ Invalid signature")
                return unverified_payload
                
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
            except:
                pass
        
        # Parse signedRenewalInfo if present
        if "data" in payload and "signedRenewalInfo" in payload["data"]:
            signed_renewal = payload["data"]["signedRenewalInfo"]
            try:
                renewal = jwt.decode(signed_renewal, options={"verify_signature": False})
                print("\n--- Renewal Info ---")
                print(f"Auto Renew Status: {renewal.get('autoRenewStatus')}")
                print(f"Expiration Intent: {renewal.get('expirationIntent', 'N/A')}")
            except:
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
