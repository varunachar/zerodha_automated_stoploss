# Kite Automated Stop loss via GTT orders

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

The application supports three execution modes:

#### 1. Dry Run Mode (Default - Safe for Testing)
Uses mock data and doesn't make any API calls. Perfect for testing strategy logic.

```bash
# In config.py:
DRY_RUN = True
MONITORING_MODE = False

# Run the application
python main.py
```

#### 2. Monitoring Mode (Live Data, No Execution)
Connects to live Kite API to fetch real portfolio and GTT data, but doesn't cancel or place any GTTs. Shows what actions would be taken.

```bash
# In config.py:
DRY_RUN = False
MONITORING_MODE = True

# Run the application
python main.py
```

#### 3. Live Mode (Full Execution)
⚠️ **CAUTION**: This mode will actually cancel and place GTT orders with real money.

```bash
# In config.py:
DRY_RUN = False
MONITORING_MODE = False

# Run the application
python main.py
```

#### Configuration

Update `config.py` with your API credentials and strategy parameters:

```python
# API Keys
API_KEY = "your_api_key_here"
API_SECRET = "your_api_secret_here"
ACCESS_TOKEN = "your_access_token_here"

# Strategy Parameters
TIER_1_QTY_PCT = 0.30  # 30% of holding
TIER_1_TRIGGER_PCT = 0.10  # 10% from high
TIER_1_LIMIT_PCT = 0.11    # 11% from high
TIER_2_TRIGGER_PCT = 0.20  # 20% from high
TIER_2_LIMIT_PCT = 0.21    # 21% from high
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