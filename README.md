# Kite GTT Trading Application

A Python application for automated trading using Kite Connect API with support for Good Till Triggered (GTT) orders.

## Features

- Integration with Kite Connect API
- TOTP (Time-based One-Time Password) support for two-factor authentication
- Support for GTT orders
- User profile and positions management

## Setup

### Prerequisites

- Python 3.7 or higher
- Kite Connect API key
- Kite trading account

### Installation

1. Clone or download this project
2. Install the required dependencies:

```bash
pip install -r requirements.txt
```

### Configuration

Set up your environment variables:

```bash
export KITE_API_KEY="your_api_key_here"
export KITE_ACCESS_TOKEN="your_access_token_here"  # Optional if using login_with_credentials
```

### Usage

#### Basic Usage

```python
from main import KiteGTT

# Initialize with API key
kite_app = KiteGTT()

# Login with credentials (if you don't have access token)
kite_app.login_with_credentials(
    user_id="your_user_id",
    password="your_password",
    totp_secret="your_totp_secret"
)

# Get profile
profile = kite_app.get_profile()
print(profile)

# Get positions
positions = kite_app.get_positions()
print(positions)
```

#### Using Environment Variables

```python
import os
from main import KiteGTT

# Set your credentials
os.environ['KITE_API_KEY'] = 'your_api_key'
os.environ['KITE_ACCESS_TOKEN'] = 'your_access_token'

# Initialize
kite_app = KiteGTT()
```

## Libraries Used

- **kiteconnect**: Official Kite Connect Python library for Zerodha API
- **pyotp**: Python library for generating TOTP codes for two-factor authentication

## Getting Started with Kite Connect

1. Visit [Kite Connect](https://kite.trade/) and create an app
2. Get your API key and secret
3. Set up TOTP authentication in your Kite account
4. Use the provided methods to authenticate and start trading

## Important Notes

- Never commit your API keys or access tokens to version control
- Always use environment variables for sensitive information
- Test thoroughly in paper trading mode before using real money
- Follow Kite Connect API rate limits and guidelines

## License

This project is for educational purposes. Please ensure compliance with your broker's terms of service and local regulations.