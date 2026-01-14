# Apple Subscription Validator

A comprehensive Python tool for validating Apple In-App Purchase receipts and transactions during manual E2E testing.

## Features

- Validates legacy base64-encoded receipts via Apple's verifyReceipt API
- Decodes and validates JWS tokens (App Store Server Notifications V2)
- Queries transactions by ID via App Store Server API
- Retrieves complete transaction history for a subscription
- Fetches current subscription statuses
- Verifies app transaction info (confirms app was downloaded from App Store)
- Looks up transactions by Order ID (Customer Order Number)
- Automatically handles sandbox/production environment detection
- Verifies JWT signatures using certificate chain
- Generates JWT tokens for API authentication
- Extracts and displays subscription details
- Both CLI and interactive modes
- Reads credentials from `.env` file

## Requirements

- Python 3.7 or higher
- pip (Python package manager)
- Virtual environment (recommended)

## Installation

### Step 1: Set up virtual environment (recommended)

```bash
# Create virtual environment
python3 -m venv venv

# Activate virtual environment
# On macOS/Linux:
source venv/bin/activate

# On Windows:
venv\Scripts\activate
```

### Step 2: Run setup script

**On macOS/Linux:**
```bash
chmod +x setup.sh
./setup.sh
```

**On Windows:**
```bash
setup.bat
```

This will:
- Install all required Python dependencies
- Create a `.env` file from `.env.example` (if it doesn't exist)

### Required Credentials

**For Legacy Receipt Validation (verifyReceipt API):**
```env
APPLE_SHARED_SECRET=your_shared_secret_here
```

Get your shared secret from:
1. Go to [App Store Connect](https://appstoreconnect.apple.com)
2. Select your app
3. Go to **App Information**
4. Look for **App-Specific Shared Secret**
5. Generate if needed

**For New Transaction API (App Store Server API):**
```env
APPLE_API_KEY="-----BEGIN PRIVATE KEY-----
...your private key...
-----END PRIVATE KEY-----"
APPLE_KEY_ID=your_key_id_here
APPLE_ISSUER_ID=your_issuer_id_here
APPLE_BUNDLE_ID=com.yourapp.bundleid
```

Get these from:
1. Go to [App Store Connect](https://appstoreconnect.apple.com)
2. Go to **Users and Access** → **Keys**
3. Create a new **App Store Connect API** key
4. Download the `.p8` key file and copy its contents to `APPLE_API_KEY` (with quotes and real line breaks)
5. Note the Key ID and Issuer ID
6. Get your Bundle ID from your app's configuration

**Environment Setting:**
```env
APPLE_ENVIRONMENT=sandbox  # or 'production'
```

### Using .env Defaults

Once configured, you can run validators without providing credentials in the command line - they will automatically use values from `.env`:

```bash
# Uses APPLE_SHARED_SECRET and APPLE_ENVIRONMENT from .env
python validate_from_file.py receipt.txt

# Override .env with command line arguments
python validate_from_file.py receipt.txt 'different_secret' --production
```

## Quick Start

### Interactive Mode (Easiest for Manual Testing)

```bash
python interactive_validator.py
```

This will guide you through validation with prompts.

### Command Line Mode

**Validate Base64 Receipt (using .env for secrets):**
```bash
python apple_subscription_validator.py 'MIITtw...'
```

**Validate Base64 Receipt (with explicit secret):**
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

### Transaction ID Lookup

Query transaction information directly from Apple's App Store Server API using a transaction ID.

**What you need:**
- Transaction ID (numeric, e.g., `400001298440177`)
- API credentials configured in `.env` file:
  - `APPLE_API_KEY` (private key)
  - `APPLE_KEY_ID`
  - `APPLE_ISSUER_ID`
  - `APPLE_BUNDLE_ID`

**Example:**
```python
from apple_subscription_validator import AppleSubscriptionValidator

validator = AppleSubscriptionValidator()
result = validator.get_transaction_info('400001298440177')
print(result)
```

**The tool will:**
1. Generate a JWT token for authentication
2. Query the App Store Server API
3. Decode the signed transaction response
4. Display transaction details (product, dates, environment, etc.)
5. Auto-retry with sandbox if production fails (and vice versa)

### Transaction History Lookup

Get ALL transactions (renewals, upgrades, downgrades, refunds) for a given original transaction ID.

**What you need:**
- Original Transaction ID (the first transaction ID of the subscription)
- API credentials configured in `.env` file (same as Transaction ID Lookup)

**Example:**
```python
from apple_subscription_validator import AppleSubscriptionValidator

validator = AppleSubscriptionValidator()
result = validator.get_transaction_history(
    original_transaction_id='400001298440177',
    sort='DESCENDING'  # or 'ASCENDING'
)
print(result)
```

**The tool will:**
1. Generate a JWT token for authentication
2. Query the transaction history endpoint
3. Decode ALL signed transactions in the response
4. Display each transaction with full details
5. Handle pagination if there are many transactions
6. Auto-retry with sandbox if production fails

**Optional Parameters:**
- `sort`: `ASCENDING` or `DESCENDING` (default: DESCENDING)
- `revision`: Pagination token for fetching next page
- `start_date`: Filter by start date (milliseconds)
- `end_date`: Filter by end date (milliseconds)
- `product_type`: Filter by product type (e.g., AUTO_RENEWABLE)

### Subscription Statuses

Get the current subscription status for all subscription groups associated with an original transaction ID.

**What you need:**
- Original Transaction ID
- API credentials configured in `.env` file

**Example:**
```python
from apple_subscription_validator import AppleSubscriptionValidator

validator = AppleSubscriptionValidator()
result = validator.get_subscription_statuses('400001298440177')
print(result)
```

**The tool will:**
1. Generate a JWT token for authentication
2. Query the subscription status endpoint
3. Decode all signed transaction and renewal info
4. Display current status for each subscription group
5. Show latest transactions and renewal information
6. Auto-retry with sandbox if production fails

**This endpoint returns:**
- Current subscription status
- Latest transaction for each subscription
- Renewal information (auto-renew status, expiration intent, etc.)
- Subscription group information

### App Transaction Info

Verify if an app was downloaded from the App Store. This is useful for validating app authenticity and preventing piracy.

**What you need:**
- App Transaction ID
- API credentials configured in `.env` file

**Example:**
```python
from apple_subscription_validator import AppleSubscriptionValidator

validator = AppleSubscriptionValidator()
result = validator.get_app_transaction_info('app_transaction_id_here')
print(result)
```

**The tool will:**
1. Generate a JWT token for authentication
2. Query the app transaction endpoint
3. Decode the signed app transaction response
4. Display app download verification details
5. Auto-retry with sandbox if production fails

**This endpoint verifies:**
- App was legitimately downloaded from App Store
- Original app version and purchase date
- Device verification info
- Bundle ID verification

### Order ID Lookup

Look up all transactions associated with a Customer Order Number. This is useful when you have the order ID from a customer's purchase receipt.

**What you need:**
- Order ID (Customer Order Number, e.g., "MK2ABC3DEFG")
- API credentials configured in `.env` file

**Example:**
```python
from apple_subscription_validator import AppleSubscriptionValidator

validator = AppleSubscriptionValidator()
result = validator.lookup_order_id('MK2ABC3DEFG')
print(result)
```

**The tool will:**
1. Generate a JWT token for authentication
2. Query the order lookup endpoint
3. Decode ALL signed transactions in the response
4. Display all transactions associated with the order
5. Auto-retry with sandbox if production fails

**This endpoint returns:**
- All transactions for the order
- Multiple transactions if order contains multiple products
- Decoded transaction details for each item

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

### For Transaction ID Lookup

```
=== Fetching Transaction Info ===
Transaction ID: 400001298440177
Environment: production
✓ Transaction found!

--- Transaction Details ---
Product ID: com.yourapp.premium_annual
Bundle ID: com.yourapp.bundle
Transaction ID: 400001298440177
Original Transaction ID: 400001298440177
Purchase Date: 2023-05-29 15:34:09
Expires Date: 2023-06-12 15:34:09
Type: Auto-Renewable Subscription
Environment: Production
Offer Type: 1
Offer Discount Type: FREE_TRIAL
```

### For Transaction History

```
=== Fetching Transaction History ===
Original Transaction ID: 400001298440177
Environment: production
Sort: DESCENDING
✓ Found 5 transactions!

--- Decoding Transaction 1/5 ---
=== Decoding Transaction JWS ===
✓ Transaction Signature verification: PASSED

--- Transaction Details ---
Product ID: com.yourapp.premium_annual
Transaction ID: 400001298440177
Original Transaction ID: 400001298440177
Purchase Date: 2023-05-29 15:34:09
Expires Date: 2023-06-12 15:34:09
Type: Auto-Renewable Subscription

--- Decoding Transaction 2/5 ---
... (continues for all transactions)
```

### For Subscription Statuses

```
=== Fetching Subscription Statuses ===
Original Transaction ID: 400001298440177
Environment: production
✓ Subscription status found!

=== Subscription Group 1 ===

--- Last Transaction 1 - Transaction Info ---
✓ Transaction Signature verification: PASSED
Product ID: com.yourapp.premium_annual
Transaction ID: 400001298440177
Purchase Date: 2023-05-29 15:34:09
Expires Date: 2023-06-12 15:34:09

--- Last Transaction 1 - Renewal Info ---
✓ Renewal Signature verification: PASSED
Auto Renew Status: 1 (Enabled)
Expiration Intent: N/A
```

### For App Transaction Info

```
=== Fetching App Transaction Info ===
App Transaction ID: abc123def456
Environment: production
✓ App transaction found!

=== Decoding App Transaction JWS ===
✓ App Transaction Signature verification: PASSED

--- Transaction Details ---
Bundle ID: com.yourapp.bundle
App Version: 1.0.0
Original Purchase Date: 2023-01-15 10:30:00
Device Verification: Passed
Receipt Type: Production
```

### For Order ID Lookup

```
=== Looking Up Order ID ===
Order ID: MK2ABC3DEFG
Environment: production
✓ Found 2 transactions for this order!

--- Decoding Transaction 1/2 ---
=== Decoding Transaction JWS ===
✓ Transaction Signature verification: PASSED

--- Transaction Details ---
Product ID: com.yourapp.premium_annual
Transaction ID: 400001298440177
Purchase Date: 2023-05-29 15:34:09
Expires Date: 2023-06-12 15:34:09

--- Decoding Transaction 2/2 ---
... (continues for all transactions in the order)
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

### "Error 401: Unauthorized" for Transaction ID
Your API credentials are incorrect or missing. Check that your `.env` file contains:
- `APPLE_API_KEY` (with proper line breaks)
- `APPLE_KEY_ID`
- `APPLE_ISSUER_ID`
- `APPLE_BUNDLE_ID` (required for JWT authentication)

### "Error 404: Transaction not found"
The transaction ID doesn't exist in the current environment. The tool will automatically retry with the other environment (sandbox/production).

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

### Transaction ID
1. Make a test purchase (sandbox or production)
2. Get the transaction ID from:
   - App Store Connect → Sales and Trends
   - Your app's transaction logs
   - StoreKit 2's `Transaction.id` property
   - Server notifications payload
3. Use the numeric transaction ID directly with the validator

Note: See the [Configuration](#configuration) section above for how to obtain your Apple credentials.

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
AppleSubscriptionValidator(shared_secret=None, sandbox=None)
```
- `shared_secret`: Your app's shared secret from App Store Connect (falls back to `.env`)
- `sandbox`: Whether to use sandbox environment (falls back to `.env`, default: sandbox)

**Methods:**

`validate_base64_receipt(receipt_data: str) -> Dict`
- Validates legacy base64 receipt
- Returns: Full response from Apple's verifyReceipt API

`decode_jws_token(jws_token: str) -> Dict`
- Decodes and validates JWS token
- Returns: Verified payload dictionary

`get_transaction_info(transaction_id: str) -> Dict`
- Gets transaction information by transaction ID
- Returns: Transaction data with decoded signed transaction

`get_transaction_history(original_transaction_id: str, revision: str = None, start_date: int = None, end_date: int = None, product_type: str = None, sort: str = 'DESCENDING') -> Dict`
- Gets complete transaction history for an original transaction ID
- Returns: All transactions with decoded data and pagination info

`get_subscription_statuses(original_transaction_id: str) -> Dict`
- Gets current subscription statuses for an original transaction ID
- Returns: Status data with decoded transaction and renewal information

`get_app_transaction_info(app_transaction_id: str) -> Dict`
- Gets app transaction information to verify app was downloaded from App Store
- Returns: App transaction data with decoded signed app transaction

`lookup_order_id(order_id: str) -> Dict`
- Looks up all transactions by Order ID (Customer Order Number)
- Returns: All transactions for the order with decoded data

## Security Notes

- **Never commit `.env` file to version control** - it's already in `.gitignore`
- The `.env.example` file is safe to commit as it contains no real credentials
- Use `.env` file for storing sensitive data like shared secrets and API keys
- JWS tokens are self-contained and more secure than receipts
- Always verify signatures for JWS tokens in production
- Keep your `APPLE_SHARED_SECRET` and API credentials secure

## Resources

- [Apple Receipt Validation](https://developer.apple.com/documentation/appstorereceipts/verifyreceipt)
- [App Store Server Notifications V2](https://developer.apple.com/documentation/appstoreservernotifications)
- [StoreKit 2 Documentation](https://developer.apple.com/documentation/storekit)
- [App Store Server API](https://developer.apple.com/documentation/appstoreserverapi)

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

### Development Setup

1. Fork the repository
2. Clone your fork:
   ```bash
   git clone https://github.com/yourusername/apple-subscription-validator.git
   cd apple-subscription-validator
   ```

3. Create a virtual environment and install dependencies:
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

4. Install development dependencies (optional):
   ```bash
   pip install -e ".[dev]"
   ```

5. Make your changes and test thoroughly

6. Submit a pull request with a clear description of your changes

### Code Style

- Follow PEP 8 guidelines
- Use meaningful variable and function names
- Add docstrings to all functions and classes
- Keep functions focused and concise
- Add comments for complex logic

### Testing

Before submitting a pull request:
- Test all validation methods (base64 receipt, JWS token, transaction lookups)
- Test both sandbox and production environments
- Verify error handling works correctly
- Ensure no credentials are committed

## License

MIT License - see [LICENSE](LICENSE) file for details
