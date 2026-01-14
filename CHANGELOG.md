# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.0.0] - 2024-01-14

### Added
- Modern Python packaging with pyproject.toml (enables `pip install`)
- MIT LICENSE file for legal clarity
- CHANGELOG.md for version tracking
- .python-version file for version management
- Enhanced documentation in requirements.txt explaining each dependency
- Comprehensive .env.example with required/optional field markers
- Utility functions in interactive_validator.py for code reuse
- Helper methods in AppleSubscriptionValidator class to eliminate duplication

### Changed
- **Major refactoring** of apple_subscription_validator.py:
  - Extracted `_get_base_url()` helper method (eliminates 5 duplications)
  - Extracted `_make_api_request()` helper method (consolidates HTTP logic)
  - Extracted `_retry_with_alternate_environment()` helper (standardizes retry logic)
  - Extracted `_decode_transaction_list()` helper (reuses transaction decoding)
  - Refactored all 5 API methods (get_transaction_info, get_transaction_history, get_subscription_statuses, get_app_transaction_info, lookup_order_id)
  - **Reduced code from ~950 lines to ~750 lines** (~200 line reduction)
- **Refactored** interactive_validator.py:
  - Added `read_file_with_error_handling()` utility function
  - Added `save_result_to_file()` utility function
  - Updated all 7 menu options to use utilities
  - **Reduced code from ~250 lines to ~200 lines** (~50 line reduction)
- **Improved error handling**: Replaced bare exception handlers with specific exception types
- **Fixed setup.bat**: Now uses requirements.txt instead of hard-coded versions
- **Enhanced .env.example**: Added REQUIRED vs OPTIONAL markers for each credential

### Fixed
- setup.bat missing python-dotenv installation (now included via requirements.txt)
- setup.bat missing .env file creation (now creates from .env.example)
- Bare exception handlers in _format_transaction_dates (now catches specific exceptions)
- Bare exception handlers in _display_jws_info (now catches jwt.DecodeError and KeyError)

### Documentation
- Added dependency explanations in requirements.txt
- Improved .env.example with detailed usage instructions
- Added REQUIRED/OPTIONAL markers for all credentials

## [1.0.0] - 2024-01-13

### Added
- Initial release with core functionality
- Base64 receipt validation (legacy verifyReceipt API)
- JWS token validation with signature verification
- Transaction lookup by ID
- Transaction history retrieval with pagination
- Subscription status lookup
- App transaction verification
- Order ID lookup
- Interactive CLI mode for manual testing
- File-based validation mode for large inputs
- Automatic sandbox/production environment detection and retry
- Certificate chain validation for JWS tokens
- Comprehensive error handling with status code interpretation
- Date formatting utilities for human-readable timestamps
- Environment variable configuration via .env file
- Cross-platform setup scripts (setup.sh for Linux/macOS, setup.bat for Windows)
