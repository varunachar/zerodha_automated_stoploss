#!/usr/bin/env python3
"""
Testing Helper Functions for Zerodha GTT Strategy
Contains mock data generators and dry run functionality for testing
"""

import logging
from unittest.mock import Mock
import config

logger = logging.getLogger(__name__)


def get_mock_kite_client():
    """
    Create a mock Kite Connect client for dry run mode

    Returns:
        Mock: Mock client with basic functionality for testing
    """
    mock_client = Mock()
    mock_client.name = "MockKiteClient"
    logger.info("Created mock Kite Connect client for dry run mode")
    return mock_client


def get_mock_portfolio_with_ltp():
    """
    Generate mock portfolio data for dry run testing

    LTP increased for TCS to test the strategy

    Returns:
        list: Mock portfolio holdings with LTP data
    """
    mock_portfolio = [
        {
            "tradingsymbol": "RELIANCE",
            "quantity": 100,
            "last_price": 2650.0,
            "instrument_token": 738561,
            "exchange": "NSE",
            "product": "CNC",
        },
        {
            "tradingsymbol": "TCS",
            "quantity": 50,
            "last_price": 3700.0,
            "instrument_token": 2953217,
            "exchange": "NSE",
            "product": "CNC",
        },
        {
            "tradingsymbol": "INFY",
            "quantity": 75,
            "last_price": 1450.0,
            "instrument_token": 408065,
            "exchange": "NSE",
            "product": "CNC",
        },
        {
            "tradingsymbol": "HDFC",
            "quantity": 25,
            "last_price": 1580.0,
            "instrument_token": 340481,
            "exchange": "NSE",
            "product": "CNC",
        },
    ]

    logger.info(f"Generated mock portfolio with {len(mock_portfolio)} holdings")
    return mock_portfolio


def main_dry_run():
    """
    Main dry run function for testing GTT strategy without placing actual orders

    This function:
    1. Initializes a mock kite client
    2. Loads current GTT state
    3. Gets mock portfolio data
    4. Plans GTT updates
    5. Prints formatted report to console
    """
    # Import here to avoid circular dependency
    from main import load_gtt_state, plan_gtt_updates, format_gtt_report
    
    try:
        logger.info("Starting GTT Strategy Dry Run...")

        # 1. Initialize mock kite client
        logger.info("Step 1: Initializing mock Kite client...")
        kite_client = get_mock_kite_client()

        # 2. Load current GTT state
        logger.info("Step 2: Loading GTT state...")
        gtt_state = load_gtt_state(config.TEST_STATE_FILE_PATH)
        logger.info(f"Loaded state for {len(gtt_state)} symbols")

        # 3. Get portfolio with LTP (using mock data for dry run)
        logger.info("Step 3: Getting portfolio data...")
        portfolio = get_mock_portfolio_with_ltp()
        logger.info(f"Retrieved portfolio with {len(portfolio)} holdings")

        # 4. Plan GTT updates
        logger.info("Step 4: Planning GTT updates...")
        plans = plan_gtt_updates(portfolio, gtt_state, config)
        logger.info(f"Generated {len(plans)} GTT plans")

        # 5. Generate and print formatted report
        logger.info("Step 5: Generating report...")
        report = format_gtt_report(plans)

        # Print report to console
        print("\n")
        print(report)
        print("\n")

        logger.info("Dry run completed successfully")
        return plans

    except Exception as e:
        logger.error(f"Error during dry run: {e}")
        print(f"\n❌ Dry run failed: {e}\n")
        raise
