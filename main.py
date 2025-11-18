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

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('gtt_strategy.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

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
        
        with open(filepath, 'r') as f:
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
        
        with open(filepath, 'w') as f:
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
        symbol = holding['tradingsymbol']
        current_price = holding['last_price']
        quantity = holding['quantity']
        exchange = holding.get('exchange', 'NSE')  # Default to NSE if not specified
        
        # Get last high price from state, or use current price if new holding
        last_high_price = gtt_state.get(symbol, {}).get('last_high_price', current_price)
        
        if current_price <= last_high_price:
            # No new high - no action needed
            plan = {
                'symbol': symbol,
                'action': 'NO_ACTION',
                'exchange': exchange,
                'reason': f"LTP ({current_price}) not a new high ({last_high_price})"
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
                'symbol': symbol,
                'action': 'UPDATE',
                'exchange': exchange,
                'new_high': new_high,
                'tier1': {
                    'qty': tier1_qty,
                    'trigger': round(tier1_trigger, 2),
                    'limit': round(tier1_limit, 2)
                },
                'tier2': {
                    'qty': tier2_qty,
                    'trigger': round(tier2_trigger, 2),
                    'limit': round(tier2_limit, 2)
                }
            }
            plans.append(plan)
            logger.info(f"UPDATE planned for {symbol}: new_high={new_high}, tier1_qty={tier1_qty}, tier2_qty={tier2_qty}")
    
    logger.info(f"Generated {len(plans)} GTT plans")
    return plans

def get_kite_client():
    """
    Initialize and return a Kite Connect client
    
    Returns:
        KiteConnect: Configured Kite Connect client instance
    """
    # TODO: Implement Kite Connect client initialization
    # This will include API key setup and access token handling
    pass

def get_mock_kite_client():
    """
    Create a mock Kite Connect client for dry run mode
    
    Returns:
        Mock: Mock client with basic functionality for testing
    """
    from unittest.mock import Mock
    
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
            'tradingsymbol': 'RELIANCE',
            'quantity': 100,
            'last_price': 2650.0,
            'instrument_token': 738561,
            'exchange': 'NSE',
            'product': 'CNC'
        },
        {
            'tradingsymbol': 'TCS',
            'quantity': 50,
            'last_price': 3700.0,
            'instrument_token': 2953217,
            'exchange': 'NSE',
            'product': 'CNC'
        },
        {
            'tradingsymbol': 'INFY',
            'quantity': 75,
            'last_price': 1450.0,
            'instrument_token': 408065,
            'exchange': 'NSE',
            'product': 'CNC'
        },
        {
            'tradingsymbol': 'HDFC',
            'quantity': 25,
            'last_price': 1580.0,
            'instrument_token': 340481,
            'exchange': 'NSE',
            'product': 'CNC'
        }
    ]
    
    logger.info(f"Generated mock portfolio with {len(mock_portfolio)} holdings")
    return mock_portfolio

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
        
        # Filter for equity instruments with quantity > 0
        equity_holdings = [
            holding for holding in holdings 
            if holding.get('instrument_type') == 'EQ' and holding.get('quantity', 0) > 0
        ]
        logger.info(f"Found {len(equity_holdings)} equity holdings with quantity > 0")
        
        if not equity_holdings:
            logger.info("No equity holdings found")
            return []
        
        # Extract tradingsymbols for LTP lookup
        tradingsymbols = [holding['tradingsymbol'] for holding in equity_holdings]
        logger.info(f"Fetching LTP for symbols: {tradingsymbols}")
        
        # Get LTP for all equity holdings
        ltp_data = kite_client.ltp(tradingsymbols)
        logger.info(f"Retrieved LTP data for {len(ltp_data)} instruments")
        
        # Merge LTP data back into holdings
        portfolio_with_ltp = []
        for holding in equity_holdings:
            tradingsymbol = holding['tradingsymbol']
            if tradingsymbol in ltp_data:
                # Create merged dictionary with required fields
                merged_holding = {
                    'tradingsymbol': tradingsymbol,
                    'quantity': holding['quantity'],
                    'last_price': ltp_data[tradingsymbol]['last_price'],
                    'instrument_token': holding.get('instrument_token'),
                    'exchange': holding.get('exchange'),
                    'product': holding.get('product'),
                    'collateral_quantity': holding.get('collateral_quantity', 0),
                    'collateral_type': holding.get('collateral_type'),
                    't1_quantity': holding.get('t1_quantity', 0),
                    'average_price': holding.get('average_price', 0),
                    'day_change': holding.get('day_change', 0),
                    'day_change_percentage': holding.get('day_change_percentage', 0),
                    'pnl': holding.get('pnl', 0),
                    'pnl_percentage': holding.get('pnl_percentage', 0)
                }
                portfolio_with_ltp.append(merged_holding)
                logger.debug(f"Added {tradingsymbol}: qty={holding['quantity']}, ltp={ltp_data[tradingsymbol]['last_price']}")
            else:
                logger.warning(f"LTP data not found for {tradingsymbol}")
        
        logger.info(f"Successfully merged portfolio data for {len(portfolio_with_ltp)} holdings")
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
            gtt for gtt in active_gtts_list 
            if gtt.get('tradingsymbol') == tradingsymbol and gtt.get('status') == 'active'
        ]
        
        if not matching_gtts:
            logger.info(f"No active GTTs found for {tradingsymbol}")
            return 0
        
        canceled_count = 0
        logger.info(f"Found {len(matching_gtts)} active GTT(s) for {tradingsymbol}")
        
        # Cancel each matching GTT
        for gtt in matching_gtts:
            trigger_id = gtt.get('trigger_id')
            if trigger_id:
                try:
                    logger.info(f"Canceling GTT for {tradingsymbol} - Trigger ID: {trigger_id}")
                    kite_client.delete_gtt(trigger_id=trigger_id)
                    canceled_count += 1
                    logger.info(f"Successfully canceled GTT {trigger_id} for {tradingsymbol}")
                except Exception as e:
                    logger.error(f"Failed to cancel GTT {trigger_id} for {tradingsymbol}: {e}")
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
        if plan.get('action') != 'UPDATE':
            logger.warning(f"Invalid plan action: {plan.get('action')}. Expected 'UPDATE'")
            return 0
        
        symbol = plan.get('symbol')
        exchange = plan.get('exchange', 'NSE')  # Default to NSE if not specified
        tier1 = plan.get('tier1', {})
        tier2 = plan.get('tier2', {})
        
        if not symbol:
            logger.error("Plan missing required 'symbol' field")
            return 0
        
        placed_count = 0
        logger.info(f"Placing new GTTs for {symbol}")
        
        # Place Tier 1 GTT if quantity > 0
        tier1_qty = tier1.get('qty', 0)
        if tier1_qty > 0:
            try:
                logger.info(f"Placing Tier 1 GTT for {symbol}: qty={tier1_qty}, trigger={tier1.get('trigger')}, limit={tier1.get('limit')}")
                kite_client.place_gtt(
                    trigger_type='single',
                    tradingsymbol=symbol,
                    exchange=exchange,
                    trigger_values=[tier1.get('trigger')],
                    last_price=tier1.get('trigger'),
                    orders=[{
                        'transaction_type': 'SELL',
                        'quantity': tier1_qty,
                        'price': tier1.get('limit'),
                        'order_type': 'LIMIT',
                        'product': 'CNC'
                    }]
                )
                placed_count += 1
                logger.info(f"Successfully placed Tier 1 GTT for {symbol}")
            except Exception as e:
                logger.error(f"Failed to place Tier 1 GTT for {symbol}: {e}")
        else:
            logger.info(f"Skipping Tier 1 GTT for {symbol}: quantity is 0")
        
        # Place Tier 2 GTT if quantity > 0
        tier2_qty = tier2.get('qty', 0)
        if tier2_qty > 0:
            try:
                logger.info(f"Placing Tier 2 GTT for {symbol}: qty={tier2_qty}, trigger={tier2.get('trigger')}, limit={tier2.get('limit')}")
                kite_client.place_gtt(
                    trigger_type='single',
                    tradingsymbol=symbol,
                    exchange=exchange,
                    trigger_values=[tier2.get('trigger')],
                    last_price=tier2.get('trigger'),
                    orders=[{
                        'transaction_type': 'SELL',
                        'quantity': tier2_qty,
                        'price': tier2.get('limit'),
                        'order_type': 'LIMIT',
                        'product': 'CNC'
                    }]
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
    update_count = sum(1 for plan in plans if plan['action'] == 'UPDATE')
    no_action_count = sum(1 for plan in plans if plan['action'] == 'NO_ACTION')
    
    report_lines.append(f"SUMMARY: {len(plans)} holdings analyzed | {update_count} updates planned | {no_action_count} no action")
    report_lines.append("")
    
    # Group plans by action type
    update_plans = [plan for plan in plans if plan['action'] == 'UPDATE']
    no_action_plans = [plan for plan in plans if plan['action'] == 'NO_ACTION']
    
    # Report UPDATE actions first
    if update_plans:
        report_lines.append("🔄 ACTIONS REQUIRED:")
        report_lines.append("-" * 40)
        for plan in update_plans:
            symbol = plan['symbol']
            new_high = plan['new_high']
            tier1 = plan['tier1']
            tier2 = plan['tier2']
            
            report_lines.append(f"{symbol}: ACTION_UPDATE | New High: ₹{new_high}")
            report_lines.append(f"  └─ Tier 1: {tier1['qty']} shares @ Trigger: ₹{tier1['trigger']}, Limit: ₹{tier1['limit']}")
            report_lines.append(f"  └─ Tier 2: {tier2['qty']} shares @ Trigger: ₹{tier2['trigger']}, Limit: ₹{tier2['limit']}")
            report_lines.append("")
        
    # Report NO_ACTION items
    if no_action_plans:
        report_lines.append("✅ NO ACTION REQUIRED:")
        report_lines.append("-" * 40)
        for plan in no_action_plans:
            symbol = plan['symbol']
            reason = plan['reason']
            report_lines.append(f"{symbol}: NO_ACTION | {reason}")
        report_lines.append("")
    
    report_lines.append("=" * 80)
    report_lines.append("End of Report")
    report_lines.append("=" * 80)
    
    return "\n".join(report_lines)

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

if __name__ == "__main__":
    logger.info("GTT Stop-Loss Strategy Application Starting...")
    logger.info(f"Dry Run Mode: {config.DRY_RUN}")
    
    if config.DRY_RUN:
        logger.info("Running in DRY RUN mode - no actual orders will be placed")
        main_dry_run()
    else:
        logger.info("Running in LIVE mode")
        # TODO: Add live trading logic here
        print("Live trading mode not yet implemented")
        pass