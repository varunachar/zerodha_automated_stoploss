#!/usr/bin/env python3
"""
Zerodha GTT Stop-Loss Strategy Automation
Automated Good Till Triggered (GTT) stop-loss strategy using Kite Connect API
"""

import json
import logging
import os
from kiteconnect import KiteConnect
import config
import requests
from urllib.parse import urlparse, parse_qs
from flask import Flask, request, redirect, render_template_string


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler("gtt_strategy.log"), logging.StreamHandler()],
)
logger = logging.getLogger(__name__)


def round_to_tick(price, tick_size=0.05):
    """
    Round a price down to the nearest valid tick size

    Args:
        price (float): Price to round
        tick_size (float): Tick size (default 0.05 for 5 paise)

    Returns:
        float: Price rounded down to nearest valid tick

    Examples:
        round_to_tick(10.18) -> 10.15
        round_to_tick(10.14) -> 10.10
        round_to_tick(10.15) -> 10.15
    """
    import math

    return math.floor(price / tick_size) * tick_size


def load_gtt_state(filepath):
    """
    Load GTT state from JSON file

    Args:
        filepath (str): Path to the JSON state file

    Returns:
        dict: Loaded state data or empty dictionary if file doesn't exist or is invalid
    """
    try:
        if not os.path.exists(filepath):
            logger.info(f"State file {filepath} does not exist, returning empty state")
            return {}

        with open(filepath, "r") as f:
            content = f.read().strip()
            if not content:
                logger.info(f"State file {filepath} is empty, returning empty state")
                return {}

            state_data = json.loads(content)
            logger.info(f"Successfully loaded state from {filepath}")
            return state_data

    except FileNotFoundError:
        logger.info(f"State file {filepath} not found, returning empty state")
        return {}
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in state file {filepath}: {e}")
        logger.info("Returning empty state due to JSON decode error")
        return {}
    except Exception as e:
        logger.error(f"Error loading state from {filepath}: {e}")
        logger.info("Returning empty state due to unexpected error")
        return {}


def save_gtt_state(filepath, state_data):
    """
    Save GTT state to JSON file

    Args:
        filepath (str): Path to the JSON state file
        state_data (dict): State data to save

    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(filepath), exist_ok=True)

        with open(filepath, "w") as f:
            json.dump(state_data, f, indent=2)

        logger.info(f"Successfully saved state to {filepath}")
        return True

    except Exception as e:
        logger.error(f"Error saving state to {filepath}: {e}")
        return False


def plan_gtt_updates(portfolio, gtt_state, config):
    """
    Plan GTT updates based on portfolio holdings and current state

    Args:
        portfolio (list): List of portfolio holdings with last_price
        gtt_state (dict): Current GTT state with last_high_price for each symbol
        config: Configuration object with strategy parameters

    Returns:
        list: List of plan dictionaries for each holding
    """
    plans = []

    for holding in portfolio:
        symbol = holding["tradingsymbol"]
        current_price = holding["last_price"]
        quantity = holding["quantity"]
        exchange = holding.get("exchange", "NSE")  # Default to NSE if not specified

        # Get last high price from state, or use -1.0 if new holding to force update
        last_high_price = gtt_state.get(symbol, {}).get(
            "last_high_price", -1.0
        )

        if current_price <= last_high_price:
            # No new high - no action needed
            plan = {
                "symbol": symbol,
                "action": "NO_ACTION",
                "exchange": exchange,
                "reason": f"LTP ({current_price}) not a new high ({last_high_price})",
            }
            plans.append(plan)
            logger.debug(f"NO_ACTION for {symbol}: {plan['reason']}")

        else:
            # New high detected - calculate new GTT levels
            new_high = current_price

            # Calculate trigger and limit prices for both tiers
            tier1_trigger = new_high * (1 - config.TIER_1_TRIGGER_PCT)
            tier1_limit = new_high * (1 - config.TIER_1_LIMIT_PCT)
            tier2_trigger = new_high * (1 - config.TIER_2_TRIGGER_PCT)
            tier2_limit = new_high * (1 - config.TIER_2_LIMIT_PCT)

            # Calculate quantities for each tier
            tier1_qty = int(quantity * config.TIER_1_QTY_PCT)
            tier2_qty = quantity - tier1_qty

            plan = {
                "symbol": symbol,
                "action": "UPDATE",
                "exchange": exchange,
                "new_high": new_high,
                "tier1": {
                    "qty": tier1_qty,
                    "trigger": round_to_tick(tier1_trigger),
                    "limit": round_to_tick(tier1_limit),
                },
                "tier2": {
                    "qty": tier2_qty,
                    "trigger": round_to_tick(tier2_trigger),
                    "limit": round_to_tick(tier2_limit),
                },
            }
            plans.append(plan)
            logger.info(
                f"UPDATE planned for {symbol}: new_high={new_high}, tier1_qty={tier1_qty}, tier2_qty={tier2_qty}"
            )

    logger.info(f"Generated {len(plans)} GTT plans")
    logger.debug(f"Plans: {plans}")
    return plans


def get_request_token(url):
    """
    Get the request token from the login URL

    Args:
        url (str): The login URL

    Returns:
        str: The request token
    """
    # Make GET request with allow_redirects=False to capture redirect chain
    logger.info(f"Making request to login URL: {url}")
    response = requests.get(url, allow_redirects=False)
    redirect_url = response.headers.get("Location")
    request_token = None

    # Follow redirects manually to capture all redirect URLs
    while redirect_url and response.status_code in [301, 302, 303, 307, 308]:
        logger.debug(f"Following redirect to: {redirect_url}")
        response = requests.get(redirect_url, allow_redirects=False)

        # Check if redirect URL starts with example.com
        parsed_url = urlparse(redirect_url)
        if parsed_url.netloc.startswith("example.com"):
            logger.info(f"Found example.com redirect: {redirect_url}")

            # Parse query parameters
            query_params = parse_qs(parsed_url.query)

            # Convert query params to a simple map (take first value for each key)
            param_map = {
                key: values[0] if values else None
                for key, values in query_params.items()
            }

            logger.debug(f"Query parameters: {param_map}")

            # Check the specified conditions
            if (
                param_map.get("action") == "login"
                and param_map.get("type") == "login"
                and param_map.get("status") == "success"
            ):

                request_token = param_map.get("request_token")
                if request_token:
                    logger.info(
                        f"Successfully extracted request_token: {request_token}"
                    )
                    # Store the request_token for later use
                    # You can use this token for further authentication steps
                    break
                else:
                    logger.warning(
                        "Login successful but no request_token found in parameters"
                    )
            else:
                logger.debug("Redirect conditions not met for token extraction")

        # Get next redirect URL
        redirect_url = response.headers.get("Location")
    return request_token


app = Flask(__name__)

def get_login_url():
    """
    Get the login URL for Kite Connect
    
    Returns:
        str: The login URL
    """
    try:
        kite_client = KiteConnect(api_key=config.API_KEY)
        return kite_client.login_url()
    except Exception as e:
        logger.error(f"Error getting login URL: {e}")
        return None

def get_authenticated_client(request_token):
    """
    Initialize and return an authenticated Kite Connect client using request_token
    
    Args:
        request_token (str): The request token from Zerodha login
        
    Returns:
        KiteConnect: Authenticated Kite Connect client instance
    """
    try:
        # Initialize Kite Connect client
        kite_client = KiteConnect(api_key=config.API_KEY)
        
        # Generate session
        data = kite_client.generate_session(request_token, api_secret=config.API_SECRET)
        kite_client.set_access_token(data["access_token"])
        logger.info("Successfully initialized authenticated Kite Connect client")
        
        return kite_client

    except Exception as e:
        logger.error(f"Error initializing Kite Connect client: {e}")
        raise








def get_portfolio_with_ltp(kite_client):
    """
    Get portfolio holdings with Last Traded Price (LTP) for equity instruments

    Args:
        kite_client: Kite Connect client instance

    Returns:
        list: List of dictionaries containing tradingsymbol, quantity, and last_price
              for equity holdings with quantity > 0
    """
    try:
        # Get all holdings
        holdings = kite_client.holdings()
        logger.info(f"Retrieved {len(holdings)} total holdings")
        # Log all holdings and their quantities for debugging
        logger.info(f"All holdings details: {holdings}")
        
        # Filter for equity instruments with quantity > 0
        equity_holdings = [
            holding
            for holding in holdings
            if holding.get("quantity", 0) > 0
        ]
        logger.info(f"Found {len(equity_holdings)} equity holdings with quantity > 0")

        if not equity_holdings:
            logger.info("No equity holdings found")
            return []

        # Extract tradingsymbols for LTP lookup
        trading_symbols = [holding["exchange"] + ":" + holding["tradingsymbol"] for holding in equity_holdings]
        logger.info(f"Fetching LTP for symbols: {trading_symbols}")

        # Get LTP for all equity holdings
        ltp_data = kite_client.ltp(trading_symbols)
        logger.info(f"Retrieved LTP data for {len(ltp_data)} instruments")

        # Merge LTP data back into holdings
        portfolio_with_ltp = []
        for holding in equity_holdings:
            trading_symbol = holding["exchange"] + ":" + holding["tradingsymbol"]
            if trading_symbol in ltp_data:
                # Create merged dictionary with required fields
                merged_holding = {
                    "tradingsymbol": trading_symbol,
                    "quantity": holding["quantity"],
                    "last_price": ltp_data[trading_symbol]["last_price"],
                    "instrument_token": holding.get("instrument_token"),
                    "exchange": holding.get("exchange"),
                    "product": holding.get("product"),
                    "collateral_quantity": holding.get("collateral_quantity", 0),
                    "collateral_type": holding.get("collateral_type"),
                    "t1_quantity": holding.get("t1_quantity", 0),
                    "average_price": holding.get("average_price", 0),
                    "day_change": holding.get("day_change", 0),
                    "day_change_percentage": holding.get("day_change_percentage", 0),
                    "pnl": holding.get("pnl", 0),
                    "pnl_percentage": holding.get("pnl_percentage", 0),
                }
                portfolio_with_ltp.append(merged_holding)
                logger.debug(
                    f"Added {trading_symbol}: qty={holding['quantity']}, ltp={ltp_data[trading_symbol]['last_price']}"
                )
            else:
                logger.warning(f"LTP data not found for {trading_symbol}")

        logger.info(
            f"Successfully merged portfolio data for {len(portfolio_with_ltp)} holdings"
        )
        return portfolio_with_ltp

    except Exception as e:
        logger.error(f"Error getting portfolio with LTP: {e}")
        raise


def cancel_existing_gtts(kite_client, tradingsymbol, active_gtts_list):
    """
    Cancel all active GTTs for a specific trading symbol

    Args:
        kite_client: Kite Connect client instance
        tradingsymbol (str): Trading symbol to cancel GTTs for
        active_gtts_list (list): List of all active GTTs from kite_client.get_gtts()

    Returns:
        int: Number of GTTs canceled
    """
    try:
        # Find all active GTTs for the specified trading symbol
        matching_gtts = [
            gtt
            for gtt in active_gtts_list
            if gtt.get("tradingsymbol") == tradingsymbol
            and gtt.get("status") == "active"
        ]

        if not matching_gtts:
            logger.info(f"No active GTTs found for {tradingsymbol}")
            return 0

        canceled_count = 0
        logger.info(f"Found {len(matching_gtts)} active GTT(s) for {tradingsymbol}")

        # Cancel each matching GTT
        for gtt in matching_gtts:
            trigger_id = gtt.get("trigger_id")
            if trigger_id:
                try:
                    logger.info(
                        f"Canceling GTT for {tradingsymbol} - Trigger ID: {trigger_id}"
                    )
                    kite_client.delete_gtt(trigger_id=trigger_id)
                    canceled_count += 1
                    logger.info(
                        f"Successfully canceled GTT {trigger_id} for {tradingsymbol}"
                    )
                except Exception as e:
                    logger.error(
                        f"Failed to cancel GTT {trigger_id} for {tradingsymbol}: {e}"
                    )
            else:
                logger.warning(f"GTT for {tradingsymbol} missing trigger_id: {gtt}")

        logger.info(f"Canceled {canceled_count} GTT(s) for {tradingsymbol}")
        return canceled_count

    except Exception as e:
        logger.error(f"Error canceling GTTs for {tradingsymbol}: {e}")
        raise


def place_new_gtts(kite_client, plan):
    """
    Place new GTTs for a single plan with UPDATE action

    Args:
        kite_client: Kite Connect client instance
        plan (dict): Plan dictionary with action == 'UPDATE' containing tier1 and tier2 data

    Returns:
        int: Number of GTTs placed successfully
    """
    try:
        if plan.get("action") != "UPDATE":
            logger.warning(
                f"Invalid plan action: {plan.get('action')}. Expected 'UPDATE'"
            )
            return 0

        symbol = plan.get("symbol")
        exchange = plan.get("exchange", "NSE")  # Default to NSE if not specified
        tier1 = plan.get("tier1", {})
        tier2 = plan.get("tier2", {})

        if not symbol:
            logger.error("Plan missing required 'symbol' field")
            return 0

        placed_count = 0
        logger.info(f"Placing new GTTs for {symbol}")

        # Place Tier 1 GTT if quantity > 0
        tier1_qty = tier1.get("qty", 0)
        if tier1_qty > 0:
            try:
                logger.info(
                    f"Placing Tier 1 GTT for {symbol}: qty={tier1_qty}, trigger={tier1.get('trigger')}, limit={tier1.get('limit')}"
                )
                kite_client.place_gtt(
                    trigger_type="single",
                    tradingsymbol=symbol,
                    exchange=exchange,
                    trigger_values=[tier1.get("trigger")],
                    last_price=tier1.get("trigger"),
                    orders=[
                        {
                            "transaction_type": "SELL",
                            "quantity": tier1_qty,
                            "price": tier1.get("limit"),
                            "order_type": "LIMIT",
                            "product": "CNC",
                        }
                    ],
                )
                placed_count += 1
                logger.info(f"Successfully placed Tier 1 GTT for {symbol}")
            except Exception as e:
                logger.error(f"Failed to place Tier 1 GTT for {symbol}: {e}")
        else:
            logger.info(f"Skipping Tier 1 GTT for {symbol}: quantity is 0")

        # Place Tier 2 GTT if quantity > 0
        tier2_qty = tier2.get("qty", 0)
        if tier2_qty > 0:
            try:
                logger.info(
                    f"Placing Tier 2 GTT for {symbol}: qty={tier2_qty}, trigger={tier2.get('trigger')}, limit={tier2.get('limit')}"
                )
                kite_client.place_gtt(
                    trigger_type="single",
                    tradingsymbol=symbol,
                    exchange=exchange,
                    trigger_values=[tier2.get("trigger")],
                    last_price=tier2.get("trigger"),
                    orders=[
                        {
                            "transaction_type": "SELL",
                            "quantity": tier2_qty,
                            "price": tier2.get("limit"),
                            "order_type": "LIMIT",
                            "product": "CNC",
                        }
                    ],
                )
                placed_count += 1
                logger.info(f"Successfully placed Tier 2 GTT for {symbol}")
            except Exception as e:
                logger.error(f"Failed to place Tier 2 GTT for {symbol}: {e}")
        else:
            logger.info(f"Skipping Tier 2 GTT for {symbol}: quantity is 0")

        logger.info(f"Placed {placed_count} new GTT(s) for {symbol}")
        return placed_count

    except Exception as e:
        logger.error(f"Error placing new GTTs for plan: {e}")
        raise


def format_monitoring_report(plans, active_gtts):
    """
    Format GTT plans and active GTTs into a comprehensive monitoring report

    Args:
        plans (list): List of GTT plan dictionaries
        active_gtts (list): List of active GTTs from Kite API

    Returns:
        str: Formatted monitoring report string
    """
    if not plans:
        return "No GTT plans generated."

    report_lines = []
    report_lines.append("=" * 80)
    report_lines.append("GTT STOP-LOSS STRATEGY - MONITORING MODE REPORT")
    report_lines.append("=" * 80)
    report_lines.append("")

    # Count actions
    update_count = sum(1 for plan in plans if plan["action"] == "UPDATE")
    no_action_count = sum(1 for plan in plans if plan["action"] == "NO_ACTION")

    report_lines.append(
        f"SUMMARY: {len(plans)} holdings analyzed | {update_count} updates planned | {no_action_count} no action"
    )
    report_lines.append(f"ACTIVE GTTs: {len(active_gtts)} currently active")
    report_lines.append("")
    report_lines.append("⚠️  MONITORING MODE: No GTTs will be canceled or placed")
    report_lines.append("")

    # Group plans by action type
    update_plans = [plan for plan in plans if plan["action"] == "UPDATE"]
    no_action_plans = [plan for plan in plans if plan["action"] == "NO_ACTION"]

    # Report UPDATE actions first
    if update_plans:
        report_lines.append("🔄 ACTIONS THAT WOULD BE EXECUTED:")
        report_lines.append("-" * 40)
        for plan in update_plans:
            symbol = plan["symbol"]
            new_high = plan["new_high"]
            tier1 = plan["tier1"]
            tier2 = plan["tier2"]

            # Find existing GTTs for this symbol
            existing_gtts = [
                gtt
                for gtt in active_gtts
                if gtt.get("tradingsymbol") == symbol and gtt.get("status") == "active"
            ]

            report_lines.append(f"{symbol}: WOULD_UPDATE | New High: ₹{new_high}")
            if existing_gtts:
                report_lines.append(
                    f"  ├─ Would cancel {len(existing_gtts)} existing GTT(s)"
                )
            report_lines.append(
                f"  ├─ Would place Tier 1: {tier1['qty']} shares @ Trigger: ₹{tier1['trigger']}, Limit: ₹{tier1['limit']}"
            )
            report_lines.append(
                f"  └─ Would place Tier 2: {tier2['qty']} shares @ Trigger: ₹{tier2['trigger']}, Limit: ₹{tier2['limit']}"
            )
            report_lines.append("")

    # Report NO_ACTION items
    if no_action_plans:
        report_lines.append("✅ NO ACTION REQUIRED:")
        report_lines.append("-" * 40)
        for plan in no_action_plans:
            symbol = plan["symbol"]
            reason = plan["reason"]
            report_lines.append(f"{symbol}: NO_ACTION | {reason}")
        report_lines.append("")

    # Report current active GTTs
    if active_gtts:
        report_lines.append("📋 CURRENT ACTIVE GTTs:")
        report_lines.append("-" * 40)
        for gtt in active_gtts:
            symbol = gtt.get("tradingsymbol", "UNKNOWN")
            trigger_id = gtt.get("trigger_id", "N/A")
            trigger_values = gtt.get("trigger_values", [])
            orders = gtt.get("orders", [])

            trigger_price = trigger_values[0] if trigger_values else "N/A"
            order_info = ""
            if orders:
                order = orders[0]
                qty = order.get("quantity", "N/A")
                price = order.get("price", "N/A")
                order_info = f"{qty} shares @ ₹{price}"

            report_lines.append(
                f"{symbol}: GTT#{trigger_id} | Trigger: ₹{trigger_price} | {order_info}"
            )
        report_lines.append("")

    report_lines.append("=" * 80)
    report_lines.append("End of Monitoring Report")
    report_lines.append("=" * 80)

    return "\n".join(report_lines)


def format_live_report(plans, active_gtts):
    """
    Format GTT plans and active GTTs into a comprehensive live execution report

    Args:
        plans (list): List of GTT plan dictionaries
        active_gtts (list): List of active GTTs from Kite API after execution

    Returns:
        str: Formatted live execution report string
    """
    if not plans:
        return "No GTT plans generated."

    report_lines = []
    report_lines.append("=" * 80)
    report_lines.append("GTT STOP-LOSS STRATEGY - LIVE MODE EXECUTION REPORT")
    report_lines.append("=" * 80)
    report_lines.append("")

    # Count actions
    update_count = sum(1 for plan in plans if plan["action"] == "UPDATE")
    no_action_count = sum(1 for plan in plans if plan["action"] == "NO_ACTION")

    report_lines.append(
        f"SUMMARY: {len(plans)} holdings analyzed | {update_count} updates executed | {no_action_count} no action"
    )
    report_lines.append(f"ACTIVE GTTs: {len(active_gtts)} currently active")
    report_lines.append("")
    report_lines.append("✅ LIVE MODE: GTTs were canceled and placed as planned")
    report_lines.append("")

    # Group plans by action type
    update_plans = [plan for plan in plans if plan["action"] == "UPDATE"]
    no_action_plans = [plan for plan in plans if plan["action"] == "NO_ACTION"]

    # Report UPDATE actions first
    if update_plans:
        report_lines.append("🔄 ACTIONS EXECUTED:")
        report_lines.append("-" * 40)
        for plan in update_plans:
            symbol = plan["symbol"]
            new_high = plan["new_high"]
            tier1 = plan["tier1"]
            tier2 = plan["tier2"]

            report_lines.append(f"{symbol}: EXECUTED | New High: ₹{new_high}")
            report_lines.append(
                f"  ├─ Placed Tier 1: {tier1['qty']} shares @ Trigger: ₹{tier1['trigger']}, Limit: ₹{tier1['limit']}"
            )
            report_lines.append(
                f"  └─ Placed Tier 2: {tier2['qty']} shares @ Trigger: ₹{tier2['trigger']}, Limit: ₹{tier2['limit']}"
            )
            report_lines.append("")

    # Report NO_ACTION items
    if no_action_plans:
        report_lines.append("✅ NO ACTION REQUIRED:")
        report_lines.append("-" * 40)
        for plan in no_action_plans:
            symbol = plan["symbol"]
            reason = plan["reason"]
            report_lines.append(f"{symbol}: NO_ACTION | {reason}")
        report_lines.append("")

    # Report current active GTTs
    if active_gtts:
        report_lines.append("📋 CURRENT ACTIVE GTTs:")
        report_lines.append("-" * 40)
        for gtt in active_gtts:
            symbol = gtt.get("tradingsymbol", "UNKNOWN")
            trigger_id = gtt.get("trigger_id", "N/A")
            trigger_values = gtt.get("trigger_values", [])
            orders = gtt.get("orders", [])

            trigger_price = trigger_values[0] if trigger_values else "N/A"
            order_info = ""
            if orders:
                order = orders[0]
                qty = order.get("quantity", "N/A")
                price = order.get("price", "N/A")
                order_info = f"{qty} shares @ ₹{price}"

            report_lines.append(
                f"{symbol}: GTT#{trigger_id} | Trigger: ₹{trigger_price} | {order_info}"
            )
        report_lines.append("")

    report_lines.append("=" * 80)
    report_lines.append("End of Live Execution Report")
    report_lines.append("=" * 80)

    return "\n".join(report_lines)


def format_gtt_report(plans):
    """
    Format GTT plans into a human-readable console report

    Args:
        plans (list): List of GTT plan dictionaries

    Returns:
        str: Formatted report string
    """
    if not plans:
        return "No GTT plans generated."

    report_lines = []
    report_lines.append("=" * 80)
    report_lines.append("GTT STOP-LOSS STRATEGY - DRY RUN REPORT")
    report_lines.append("=" * 80)
    report_lines.append("")

    # Count actions
    update_count = sum(1 for plan in plans if plan["action"] == "UPDATE")
    no_action_count = sum(1 for plan in plans if plan["action"] == "NO_ACTION")

    report_lines.append(
        f"SUMMARY: {len(plans)} holdings analyzed | {update_count} updates planned | {no_action_count} no action"
    )
    report_lines.append("")

    # Group plans by action type
    update_plans = [plan for plan in plans if plan["action"] == "UPDATE"]
    no_action_plans = [plan for plan in plans if plan["action"] == "NO_ACTION"]

    # Report UPDATE actions first
    if update_plans:
        report_lines.append("🔄 ACTIONS REQUIRED:")
        report_lines.append("-" * 40)
        for plan in update_plans:
            symbol = plan["symbol"]
            new_high = plan["new_high"]
            tier1 = plan["tier1"]
            tier2 = plan["tier2"]

            report_lines.append(f"{symbol}: ACTION_UPDATE | New High: ₹{new_high}")
            report_lines.append(
                f"  └─ Tier 1: {tier1['qty']} shares @ Trigger: ₹{tier1['trigger']}, Limit: ₹{tier1['limit']}"
            )
            report_lines.append(
                f"  └─ Tier 2: {tier2['qty']} shares @ Trigger: ₹{tier2['trigger']}, Limit: ₹{tier2['limit']}"
            )
            report_lines.append("")

    # Report NO_ACTION items
    if no_action_plans:
        report_lines.append("✅ NO ACTION REQUIRED:")
        report_lines.append("-" * 40)
        for plan in no_action_plans:
            symbol = plan["symbol"]
            reason = plan["reason"]
            report_lines.append(f"{symbol}: NO_ACTION | {reason}")
        report_lines.append("")

    report_lines.append("=" * 80)
    report_lines.append("End of Report")
    report_lines.append("=" * 80)

    return "\n".join(report_lines)


def main_live_run(kite_client):
    """
    Main live run function for executing GTT strategy with real orders

    This function:
    1. Uses the provided authenticated Kite Connect client
    2. Loads current GTT state
    3. Gets portfolio data with LTP
    4. Gets all active GTTs
    5. Plans GTT updates
    6. Executes the plans (cancel existing, place new GTTs)
    7. Updates and saves the GTT state
    """
    try:
        logger.info("Starting GTT Strategy Live Run...")

        # 1. Client is already initialized and passed as argument
        if not kite_client:
            logger.error("Invalid Kite Connect client provided")
            return
        # 2. Load current GTT state
        logger.info("Step 2: Loading GTT state...")
        gtt_state = load_gtt_state(config.STATE_FILE_PATH)
        logger.info(f"Loaded state for {len(gtt_state)} symbols")

        # 3. Get portfolio with LTP
        logger.info("Step 3: Getting portfolio data with LTP...")
        portfolio = get_portfolio_with_ltp(kite_client)
        logger.info(f"Retrieved portfolio with {len(portfolio)} holdings")

        # 4. Get all active GTTs
        logger.info("Step 4: Getting active GTTs...")
        active_gtts = kite_client.get_gtts()
        logger.info(f"Retrieved {len(active_gtts)} active GTTs")

        # 5. Plan GTT updates
        logger.info("Step 5: Planning GTT updates...")
        plans = plan_gtt_updates(portfolio, gtt_state, config)
        logger.info(f"Generated {len(plans)} GTT plans")

        # 6. Execute plans
        logger.info("Step 6: Executing GTT plans...")
        update_count = 0

        for plan in plans:
            if plan["action"] == "UPDATE":
                symbol = plan["symbol"]
                logger.info(f"Processing UPDATE for {symbol}...")

                try:
                    # Cancel existing GTTs for this symbol
                    canceled_count = cancel_existing_gtts(
                        kite_client, symbol, active_gtts
                    )
                    logger.info(
                        f"Canceled {canceled_count} existing GTT(s) for {symbol}"
                    )

                    # Place new GTTs
                    placed_count = place_new_gtts(kite_client, plan)
                    logger.info(f"Placed {placed_count} new GTT(s) for {symbol}")

                    # Update local GTT state
                    gtt_state[symbol] = {"last_high_price": plan["new_high"]}
                    logger.info(
                        f"Updated state for {symbol}: last_high_price={plan['new_high']}"
                    )

                    update_count += 1

                except Exception as e:
                    logger.error(f"[{symbol}]: FAILED to process. Error: {e}")
                    # Continue with other symbols even if one fails
                    continue
            else:
                try:
                    logger.debug(f"Skipping {plan['symbol']}: action={plan['action']}")
                except Exception as e:
                    logger.error(
                        f"[{plan.get('symbol', 'UNKNOWN')}]: FAILED to process. Error: {e}"
                    )
                    continue

        # 7. Save updated GTT state
        logger.info("Step 7: Saving updated GTT state...")
        if save_gtt_state(config.STATE_FILE_PATH, gtt_state):
            logger.info("Successfully saved updated GTT state")
        else:
            logger.error("Failed to save GTT state")

        # Get updated active GTTs after execution
        logger.info("Step 8: Getting updated active GTTs...")
        updated_active_gtts = kite_client.get_gtts()
        logger.info(f"Retrieved {len(updated_active_gtts)} active GTTs after execution")

        logger.info(
            f"Live run completed successfully. Processed {update_count} updates."
        )
        return plans, updated_active_gtts

    except Exception as e:
        logger.error(f"Error during live run: {e}")
        print(f"\n❌ Live run failed: {e}\n")
        raise


def main_monitoring_run(kite_client):
    """
    Main monitoring run function for live monitoring without executing orders

    This function runs in live mode but does NOT cancel or place GTTs.
    It's useful for monitoring what the strategy would do without actual execution.

    This function:
    1. Uses the provided authenticated Kite Connect client
    2. Loads current GTT state
    3. Gets real portfolio data with LTP
    4. Gets all active GTTs
    5. Plans GTT updates
    6. Prints formatted report to console (no execution)
    """
    try:
        logger.info("Starting GTT Strategy Monitoring Run...")

        # 1. Client is already initialized and passed as argument
        if not kite_client:
            logger.error("Invalid Kite Connect client provided")
            return

        # 2. Load current GTT state
        logger.info("Step 2: Loading GTT state...")
        gtt_state = load_gtt_state(config.STATE_FILE_PATH)
        logger.info(f"Loaded state for {len(gtt_state)} symbols")

        # 3. Get portfolio with LTP
        logger.info("Step 3: Getting portfolio data with LTP...")
        portfolio = get_portfolio_with_ltp(kite_client)
        logger.info(f"Retrieved portfolio with {len(portfolio)} holdings")

        # 4. Get all active GTTs
        logger.info("Step 4: Getting active GTTs...")
        active_gtts = kite_client.get_gtts()
        logger.info(f"Retrieved {len(active_gtts)} active GTTs")

        # 5. Plan GTT updates
        logger.info("Step 5: Planning GTT updates...")
        plans = plan_gtt_updates(portfolio, gtt_state, config)
        logger.info(f"Generated {len(plans)} GTT plans")

        # 6. Generate and print formatted report (NO EXECUTION)
        logger.info("Step 6: Generating monitoring report...")
        report = format_monitoring_report(plans, active_gtts)

        # Print report to console
        print("\n")
        print(report)
        print("\n")

        logger.info("Monitoring run completed successfully")
        return plans, active_gtts

    except Exception as e:
        logger.error(f"Error during monitoring run: {e}")
        print(f"\n❌ Monitoring run failed: {e}\n")
        raise





@app.route('/')
def index():
    """Home page with Login button"""
    login_url = get_login_url()
    html = f"""
    <html>
        <head>
            <title>Zerodha GTT Strategy</title>
            <style>
                body {{ font-family: Arial, sans-serif; text-align: center; padding_top: 50px; }}
                .btn {{ display: inline-block; padding: 10px 20px; background-color: #388e3c; color: white; text-decoration: none; border-radius: 5px; font-weight: bold; }}
                .btn:hover {{ background-color: #2e7d32; }}
            </style>
        </head>
        <body>
            <h1>Zerodha GTT Strategy Automation</h1>
            <p>Click the button below to login with Zerodha and start the strategy.</p>
            <a href="{login_url}" class="btn">Login with Zerodha</a>
        </body>
    </html>
    """
    return render_template_string(html)

@app.route('/callback') # Or whatever your redirect URL path is configured to be
def callback():
    """Callback URL for Zerodha login"""
    status = request.args.get('status')
    request_token = request.args.get('request_token')
    
    if status != 'success' or not request_token:
        return f"Login Failed: {request.args.get('message', 'Unknown error')}", 400
        
    try:
        # Initialize authenticated client
        kite_client = get_authenticated_client(request_token)
        
        # Run strategy based on config
        output_report = ""
        
        if config.MONITORING_MODE:
            logger.info("Running in MONITORING MODE via web request")
            plans, active_gtts = main_monitoring_run(kite_client)
            # Generate formatted monitoring report
            output_report = format_monitoring_report(plans, active_gtts)
        else:
            logger.info("Running in LIVE MODE via web request")
            plans, active_gtts = main_live_run(kite_client)
            # Generate formatted live execution report
            output_report = format_live_report(plans, active_gtts)
            
        # Convert report to HTML (preserve formatting with <pre> tag)
        html_report = output_report.replace("<", "&lt;").replace(">", "&gt;")
        
        return f"""
        <html>
            <head>
                <title>Strategy Execution Result</title>
                <style>
                    body {{ font-family: Arial, sans-serif; padding: 20px; background-color: #f5f5f5; }}
                    .container {{ max-width: 1200px; margin: 0 auto; background-color: white; padding: 30px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
                    .success {{ color: #2e7d32; font-weight: bold; font-size: 18px; margin-bottom: 20px; }}
                    .report {{ background-color: #1e1e1e; color: #d4d4d4; padding: 20px; border-radius: 4px; overflow-x: auto; font-family: 'Courier New', monospace; font-size: 14px; line-height: 1.6; white-space: pre-wrap; }}
                    .back-link {{ display: inline-block; margin-top: 20px; padding: 10px 20px; background-color: #388e3c; color: white; text-decoration: none; border-radius: 5px; font-weight: bold; }}
                    .back-link:hover {{ background-color: #2e7d32; }}
                    h1 {{ color: #333; margin-bottom: 10px; }}
                </style>
            </head>
            <body>
                <div class="container">
                    <h1>Execution Complete</h1>
                    <p class="success">✅ Successfully authenticated and executed strategy.</p>
                    <div class="report">{html_report}</div>
                    <a href="/" class="back-link">Back to Home</a>
                </div>
            </body>
        </html>
        """
        
    except Exception as e:
        logger.error(f"Error in callback: {e}")
        return f"Error executing strategy: {str(e)}", 500

if __name__ == "__main__":
    if config.DRY_RUN:
        print("--- RUNNING IN DRY-RUN MODE ---")
        from test_helpers import main_dry_run
        main_dry_run()
    else:
        # Start Flask server
        print("--- STARTING WEB SERVER ---")
        print("Please open http://localhost:5001 in your browser")
        app.run(host='0.0.0.0', port=5001, debug=True)

