# Apple Subscription Validator

A Python tool for validating both legacy base64 receipts and new JWS signed tokens for Apple subscriptions during manual E2E testing.

## Features

✓ Validates legacy base64-encoded receipts via Apple's verifyReceipt API  
✓ Decodes and validates JWS tokens (App Store Server Notifications V2)  
✓ Automatically handles sandbox/production environment detection  
✓ Verifies JWT signatures using certificate chain  
✓ Extracts and displays subscription details  
✓ Both CLI and interactive modes  

## Installation

```bash
chmod +x setup.sh
./setup.sh
```

## Quick Start

### Interactive Mode (Easiest for Manual Testing)

```bash
python interactive_validator.py
```

This will guide you through validation with prompts.

### Command Line Mode

**Validate Base64 Receipt (Sandbox):**
```bash
python apple_subscription_validator.py 'MIITtw...' 'your_shared_secret'
```

**Validate Base64 Receipt (Production):**
```bash
python apple_subscription_validator.py 'MIITtw...' 'your_shared_secret' --production
```

**Validate JWS Token:**
```bash
python apple_subscription_validator.py 'eyJhbGciOiJFUzI1NiI...'
```

## Usage Details

### Base64 Receipt Validation

The legacy receipt format that you get from:
- `SKPaymentTransaction.transactionReceipt` (deprecated)
- `appStoreReceiptURL` bundle receipt

**What you need:**
- The base64-encoded receipt string
- Your app's shared secret (optional but recommended)

**Example:**
```python
from apple_subscription_validator import AppleSubscriptionValidator

validator = AppleSubscriptionValidator(
    shared_secret='your_shared_secret',
    sandbox=True
)

result = validator.validate_base64_receipt('MIITtw...')
print(result)
```

**Response Status Codes:**
- `0` - Valid receipt
- `21006` - Receipt is valid but subscription has expired
- `21007` - Sandbox receipt sent to production (auto-retries)
- `21008` - Production receipt sent to sandbox

### JWS Token Validation

The new format used in:
- App Store Server Notifications V2
- App Store Server API responses
- StoreKit 2 transactions

**What you need:**
- The JWS token string (starts with `eyJ`)

**Example:**
```python
from apple_subscription_validator import AppleSubscriptionValidator

validator = AppleSubscriptionValidator()
payload = validator.decode_jws_token('eyJhbGciOiJFUzI1NiI...')
print(payload)
```

**The tool will:**
1. Decode the JWT without verification (to inspect)
2. Extract the certificate chain from `x5c` header
3. Verify the signature using ES256 algorithm
4. Check expiration
5. Display transaction and renewal information

## Understanding the Output

### For Base64 Receipts

```
Status: 0 - ✓ Valid receipt

--- Receipt Information ---
Bundle ID: com.yourapp.bundle
Application Version: 1.0.0

--- Latest Subscription Info ---
Product ID: com.yourapp.premium_monthly
Transaction ID: 1000000123456789
Expires Date: 2024-12-31 23:59:59
Is Trial Period: false
Auto Renew Status: 1
```

### For JWS Tokens

```
✓ Signature verification: PASSED

--- JWS Token Information ---
Notification Type: SUBSCRIBED
Subtype: INITIAL_BUY

--- Transaction Info ---
Product ID: com.yourapp.premium_monthly
Transaction ID: 2000000123456789
Purchase Date: 1638360000000
Expires Date: 1640952000000
```

## Common Issues & Troubleshooting

### "Status: 21007 - Receipt is from sandbox"
Your receipt is from the sandbox environment but you're hitting production. The script auto-retries with sandbox endpoint.

### "Status: 21004 - Shared secret does not match"
The shared secret is incorrect. Get it from App Store Connect → Your App → App Information → App-Specific Shared Secret.

### "Invalid signature" for JWS
The token signature couldn't be verified. Possible causes:
- Token has been tampered with
- Certificate chain is incomplete
- Token is malformed

### "Token has expired"
The JWS token has passed its expiration time. This is normal for old notifications.

## Getting Your Test Data

### Base64 Receipt
1. Make a test purchase in sandbox
2. Retrieve receipt from device:
   - iOS: `Bundle.main.appStoreReceiptURL`
   - Read file and base64 encode it
3. Or use Xcode's StoreKit testing

### JWS Token
1. Configure App Store Server Notifications in App Store Connect
2. Set webhook URL (use ngrok for local testing)
3. Make a test purchase or trigger notification
4. Capture the JWS from notification payload

### Shared Secret
1. Go to App Store Connect
2. Select your app
3. Go to App Information
4. Look for "App-Specific Shared Secret"
5. Generate if needed

## E2E Testing Workflow

1. **Set up test environment:**
   ```bash
   ./setup.sh
   ```

2. **Make test purchase in sandbox**

3. **Get receipt/token from your app logs**

4. **Run validation:**
   ```bash
   python interactive_validator.py
   ```

5. **Verify output matches expected subscription state**

6. **Save results for documentation:**
   - Tool offers to save JSON results
   - Great for test evidence

## API Reference

### `AppleSubscriptionValidator`

**Constructor:**
```python
AppleSubscriptionValidator(shared_secret=None, sandbox=True)
```
- `shared_secret`: Your app's shared secret from App Store Connect
- `sandbox`: Whether to use sandbox environment (default: True)

**Methods:**

`validate_base64_receipt(receipt_data: str) -> Dict`
- Validates legacy base64 receipt
- Returns: Full response from Apple's verifyReceipt API

`decode_jws_token(jws_token: str) -> Dict`
- Decodes and validates JWS token
- Returns: Verified payload dictionary

## Security Notes

- Never commit shared secrets to version control
- Use environment variables for sensitive data
- JWS tokens are self-contained and more secure than receipts
- Always verify signatures for JWS tokens in production

## Resources

- [Apple Receipt Validation](https://developer.apple.com/documentation/appstorereceipts/verifyreceipt)
- [App Store Server Notifications V2](https://developer.apple.com/documentation/appstoreservernotifications)
- [StoreKit 2 Documentation](https://developer.apple.com/documentation/storekit)
