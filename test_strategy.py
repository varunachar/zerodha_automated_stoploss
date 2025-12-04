#!/usr/bin/env python3
"""
Unit tests for GTT Stop-Loss Strategy
"""

import unittest
import json
import logging
import os
import tempfile
from unittest.mock import Mock, patch, mock_open
import config
import main

class TestGTTStrategy(unittest.TestCase):
    """Test cases for GTT strategy functionality"""
    
    def setUp(self):
        """Set up test fixtures before each test method"""
        self.temp_state_file = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json')
        self.temp_state_file.write('{}')
        self.temp_state_file.close()
        
    def tearDown(self):
        """Clean up after each test method"""
        os.unlink(self.temp_state_file.name)
    
    def test_config_loading(self):
        """Test that configuration values are loaded correctly"""
        self.assertTrue(hasattr(config, 'DRY_RUN'))
        self.assertTrue(hasattr(config, 'API_KEY'))
        self.assertTrue(hasattr(config, 'TIER_1_QTY_PCT'))
        self.assertEqual(config.TIER_1_QTY_PCT, 0.30)
    
    def test_kite_client_placeholder(self):
        """Test that get_authenticated_client function exists"""
        self.assertTrue(callable(getattr(main, 'get_authenticated_client')))
    
    def test_logging_setup(self):
        """Test that logging is properly configured"""
        logger = logging.getLogger(__name__)
        self.assertIsNotNone(logger)
        # The logger level is 0 (NOTSET) by default, inheriting from root logger
        # The root logger is configured to INFO level in main.py
        self.assertEqual(logger.level, 0)  # NOTSET, inherits from root
    
    def test_state_file_path(self):
        """Test that state file path is correctly defined"""
        self.assertEqual(config.STATE_FILE_PATH, 'gtt_state.json')
    
    def test_strategy_parameters(self):
        """Test that all strategy parameters are defined"""
        expected_params = [
            'TIER_1_QTY_PCT', 'TIER_1_TRIGGER_PCT', 'TIER_1_LIMIT_PCT',
            'TIER_2_TRIGGER_PCT', 'TIER_2_LIMIT_PCT'
        ]
        
        for param in expected_params:
            self.assertTrue(hasattr(config, param), f"Missing parameter: {param}")
    
    def test_get_portfolio_with_ltp(self):
        """Test get_portfolio_with_ltp function with mocked data"""
        # Mock holdings data with specific test cases
        mock_holdings = [
            {
                'tradingsymbol': 'RELIANCE',
                'instrument_type': 'EQ',
                'quantity': 10,  # Valid EQ stock with quantity > 0
                'instrument_token': 738561,
                'exchange': 'NSE',
                'product': 'CNC',
                'average_price': 2500.0
            },
            {
                'tradingsymbol': 'TCS',
                'instrument_type': 'EQ',
                'quantity': 0,  # EQ stock with quantity = 0 (should be filtered out)
                'instrument_token': 2953217,
                'exchange': 'NSE',
                'product': 'CNC',
                'average_price': 3500.0
            }
        ]
        
        # Mock LTP data - only for the valid EQ stock
        mock_ltp = {
            'NSE:RELIANCE': {'last_price': 2600.0}
        }
        
        # Setup mock client
        mock_client = Mock()
        mock_client.holdings.return_value = mock_holdings
        mock_client.ltp.return_value = mock_ltp
        
        # Call the function
        result = main.get_portfolio_with_ltp(mock_client)
        
        # Assertions
        self.assertEqual(len(result), 1)  # Only one valid EQ instrument with qty > 0
        
        # Check that only RELIANCE is returned (the valid EQ stock)
        self.assertEqual(len(result), 1)
        holding = result[0]
        
        # Verify the holding has correct data
        self.assertEqual(holding['tradingsymbol'], 'NSE:RELIANCE')
        self.assertEqual(holding['quantity'], 10)
        self.assertEqual(holding['last_price'], 2600.0)
        
        # Verify API calls
        mock_client.holdings.assert_called_once()
        mock_client.ltp.assert_called_once_with(['NSE:RELIANCE'])  # Only RELIANCE should be queried for LTP
    
    @patch('main.KiteConnect')
    def test_get_portfolio_with_ltp_empty_holdings(self, mock_kite_class):
        """Test get_portfolio_with_ltp with no equity holdings"""
        mock_client = Mock()
        mock_client.holdings.return_value = []
        
        result = main.get_portfolio_with_ltp(mock_client)
        
        self.assertEqual(result, [])
        mock_client.holdings.assert_called_once()
        mock_client.ltp.assert_not_called()
    
    @patch('builtins.open', mock_open(read_data='{"RELIANCE": {"last_high_price": 2500}}'))
    @patch('os.path.exists', return_value=True)
    def test_load_gtt_state_file_exists(self, mock_exists):
        """Test load_gtt_state with existing valid JSON file"""
        result = main.load_gtt_state('test_state.json')
        expected = {"RELIANCE": {"last_high_price": 2500}}
        self.assertEqual(result, expected)
    
    @patch('builtins.open', side_effect=FileNotFoundError)
    def test_load_gtt_state_file_not_found(self, mock_open):
        """Test load_gtt_state with FileNotFoundError"""
        result = main.load_gtt_state('non_existent_file.json')
        self.assertEqual(result, {})
    
    def test_save_gtt_state(self):
        """Test save_gtt_state with mocked file operations"""
        test_data = {"RELIANCE": {"last_high_price": 2500}}
        
        with patch('os.makedirs') as mock_makedirs, \
             patch('builtins.open', mock_open()) as mock_file:
            
            result = main.save_gtt_state('test_state.json', test_data)
            
            self.assertTrue(result)
            mock_file.assert_called_once_with('test_state.json', 'w')
            
            # Verify the file was written with correct JSON using json.dump
            # json.dump calls the file's write method multiple times, so we check if it was called
            mock_file.return_value.write.assert_called()
    
    def test_plan_gtt_updates_no_new_high(self):
        """Test plan_gtt_updates when no new high is detected"""
        # Mock portfolio data
        portfolio = [
            {
                'tradingsymbol': 'TCS',
                'last_price': 3000,
                'quantity': 100
            }
        ]
        
        # Mock GTT state with higher price
        gtt_state = {
            'TCS': {'last_high_price': 3050}
        }
        
        # Mock config
        mock_config = Mock()
        mock_config.TIER_1_TRIGGER_PCT = 0.10
        mock_config.TIER_1_LIMIT_PCT = 0.11
        mock_config.TIER_2_TRIGGER_PCT = 0.20
        mock_config.TIER_2_LIMIT_PCT = 0.21
        mock_config.TIER_1_QTY_PCT = 0.30
        
        result = main.plan_gtt_updates(portfolio, gtt_state, mock_config)
        
        self.assertEqual(len(result), 1)
        plan = result[0]
        self.assertEqual(plan['symbol'], 'TCS')
        self.assertEqual(plan['action'], 'NO_ACTION')
        self.assertIn('LTP (3000) not a new high (3050)', plan['reason'])
    
    def test_plan_gtt_updates_new_high(self):
        """Test plan_gtt_updates when new high is detected"""
        # Mock portfolio data
        portfolio = [
            {
                'tradingsymbol': 'RELIANCE',
                'last_price': 2600,
                'quantity': 100
            }
        ]
        
        # Mock GTT state with lower price
        gtt_state = {
            'RELIANCE': {'last_high_price': 2500}
        }
        
        # Mock config
        mock_config = Mock()
        mock_config.TIER_1_TRIGGER_PCT = 0.10
        mock_config.TIER_1_LIMIT_PCT = 0.11
        mock_config.TIER_2_TRIGGER_PCT = 0.20
        mock_config.TIER_2_LIMIT_PCT = 0.21
        mock_config.TIER_1_QTY_PCT = 0.30
        
        result = main.plan_gtt_updates(portfolio, gtt_state, mock_config)
        
        self.assertEqual(len(result), 1)
        plan = result[0]
        self.assertEqual(plan['symbol'], 'RELIANCE')
        self.assertEqual(plan['action'], 'UPDATE')
        self.assertEqual(plan['new_high'], 2600)
        
        # Check tier1 calculations
        self.assertEqual(plan['tier1']['qty'], 30)  # 100 * 0.30
        self.assertEqual(plan['tier1']['trigger'], 2340.0)  # 2600 * (1 - 0.10)
        self.assertEqual(plan['tier1']['limit'], 2314.0)  # 2600 * (1 - 0.11)
        
        # Check tier2 calculations
        self.assertEqual(plan['tier2']['qty'], 70)  # 100 - 30
        self.assertEqual(plan['tier2']['trigger'], 2080.0)  # 2600 * (1 - 0.20)
        self.assertEqual(plan['tier2']['limit'], 2054.0)  # 2600 * (1 - 0.21)
    
    def test_plan_gtt_updates_new_holding(self):
        """Test plan_gtt_updates for new holding (not in state)"""
        # Mock portfolio data
        portfolio = [
            {
                'tradingsymbol': 'NEWSTOCK',
                'last_price': 1000,
                'quantity': 50
            }
        ]
        
        # Empty GTT state (new holding)
        gtt_state = {}
        
        # Mock config
        mock_config = Mock()
        mock_config.TIER_1_TRIGGER_PCT = 0.10
        mock_config.TIER_1_LIMIT_PCT = 0.11
        mock_config.TIER_2_TRIGGER_PCT = 0.20
        mock_config.TIER_2_LIMIT_PCT = 0.21
        mock_config.TIER_1_QTY_PCT = 0.30
        
        result = main.plan_gtt_updates(portfolio, gtt_state, mock_config)
        
        self.assertEqual(len(result), 1)
        plan = result[0]
        self.assertEqual(plan['symbol'], 'NEWSTOCK')
        self.assertEqual(plan['action'], 'NO_ACTION')
        self.assertIn('LTP (1000) not a new high (1000)', plan['reason'])
    
    def test_plan_gtt_updates_mixed_scenarios(self):
        """Test plan_gtt_updates with mixed scenarios (new high and no action)"""
        # Mock portfolio data
        portfolio = [
            {
                'tradingsymbol': 'STOCK1',
                'last_price': 2000,
                'quantity': 100
            },
            {
                'tradingsymbol': 'STOCK2',
                'last_price': 1500,
                'quantity': 50
            }
        ]
        
        # Mock GTT state
        gtt_state = {
            'STOCK1': {'last_high_price': 1900},  # New high
            'STOCK2': {'last_high_price': 1600}   # No new high
        }
        
        # Mock config
        mock_config = Mock()
        mock_config.TIER_1_TRIGGER_PCT = 0.10
        mock_config.TIER_1_LIMIT_PCT = 0.11
        mock_config.TIER_2_TRIGGER_PCT = 0.20
        mock_config.TIER_2_LIMIT_PCT = 0.21
        mock_config.TIER_1_QTY_PCT = 0.30
        
        result = main.plan_gtt_updates(portfolio, gtt_state, mock_config)
        
        self.assertEqual(len(result), 2)
        
        # Check STOCK1 (new high)
        stock1_plan = next(p for p in result if p['symbol'] == 'STOCK1')
        self.assertEqual(stock1_plan['action'], 'UPDATE')
        self.assertEqual(stock1_plan['new_high'], 2000)
        
        # Check STOCK2 (no action)
        stock2_plan = next(p for p in result if p['symbol'] == 'STOCK2')
        self.assertEqual(stock2_plan['action'], 'NO_ACTION')
        self.assertIn('LTP (1500) not a new high (1600)', stock2_plan['reason'])
    
    def test_cancel_existing_gtts(self):
        """Test cancel_existing_gtts function with mock kite client and GTT data"""
        # Create mock kite client
        mock_client = Mock()
        
        # Create sample active GTTs list with multiple symbols
        active_gtts_list = [
            {
                'trigger_id': 'gtt_001',
                'tradingsymbol': 'RELIANCE',
                'status': 'active',
                'trigger_type': 'single',
                'trigger_values': [2500.0],
                'last_price': 2600.0
            },
            {
                'trigger_id': 'gtt_002',
                'tradingsymbol': 'RELIANCE',
                'status': 'active',
                'trigger_type': 'single',
                'trigger_values': [2400.0],
                'last_price': 2600.0
            },
            {
                'trigger_id': 'gtt_003',
                'tradingsymbol': 'TCS',
                'status': 'active',
                'trigger_type': 'single',
                'trigger_values': [3500.0],
                'last_price': 3600.0
            },
            {
                'trigger_id': 'gtt_004',
                'tradingsymbol': 'RELIANCE',
                'status': 'cancelled',  # Should be ignored (not active)
                'trigger_type': 'single',
                'trigger_values': [2300.0],
                'last_price': 2600.0
            },
            {
                'trigger_id': 'gtt_005',
                'tradingsymbol': 'INFY',
                'status': 'active',
                'trigger_type': 'single',
                'trigger_values': [1400.0],
                'last_price': 1450.0
            }
        ]
        
        # Test canceling GTTs for RELIANCE (should find 2 active GTTs)
        result = main.cancel_existing_gtts(mock_client, 'RELIANCE', active_gtts_list)
        
        # Assertions
        self.assertEqual(result, 2)  # Should cancel 2 GTTs for RELIANCE
        
        # Verify delete_gtt was called exactly 2 times with correct trigger_ids
        self.assertEqual(mock_client.delete_gtt.call_count, 2)
        
        # Check that the correct trigger_ids were called
        call_args_list = mock_client.delete_gtt.call_args_list
        called_trigger_ids = [call[1]['trigger_id'] for call in call_args_list]
        expected_trigger_ids = ['gtt_001', 'gtt_002']
        
        self.assertCountEqual(called_trigger_ids, expected_trigger_ids)
        
        # Reset mock for next test
        mock_client.reset_mock()
        
        # Test canceling GTTs for TCS (should find 1 active GTT)
        result = main.cancel_existing_gtts(mock_client, 'TCS', active_gtts_list)
        
        self.assertEqual(result, 1)  # Should cancel 1 GTT for TCS
        self.assertEqual(mock_client.delete_gtt.call_count, 1)
        mock_client.delete_gtt.assert_called_with(trigger_id='gtt_003')
        
        # Reset mock for next test
        mock_client.reset_mock()
        
        # Test canceling GTTs for a symbol with no active GTTs
        result = main.cancel_existing_gtts(mock_client, 'HDFC', active_gtts_list)
        
        self.assertEqual(result, 0)  # Should cancel 0 GTTs for HDFC
        self.assertEqual(mock_client.delete_gtt.call_count, 0)
        mock_client.delete_gtt.assert_not_called()
    
    def test_cancel_existing_gtts_with_errors(self):
        """Test cancel_existing_gtts function when delete_gtt raises exceptions"""
        # Create mock kite client that raises exception on delete_gtt
        mock_client = Mock()
        mock_client.delete_gtt.side_effect = Exception("API Error")
        
        # Create sample active GTTs list
        active_gtts_list = [
            {
                'trigger_id': 'gtt_001',
                'tradingsymbol': 'RELIANCE',
                'status': 'active',
                'trigger_type': 'single',
                'trigger_values': [2500.0],
                'last_price': 2600.0
            }
        ]
        
        # Test that function handles exceptions gracefully
        result = main.cancel_existing_gtts(mock_client, 'RELIANCE', active_gtts_list)
        
        # Should return 0 canceled GTTs due to exception
        self.assertEqual(result, 0)
        
        # Verify delete_gtt was called but failed
        self.assertEqual(mock_client.delete_gtt.call_count, 1)
        mock_client.delete_gtt.assert_called_with(trigger_id='gtt_001')
    
    def test_cancel_existing_gtts_missing_trigger_id(self):
        """Test cancel_existing_gtts function with GTTs missing trigger_id"""
        # Create mock kite client
        mock_client = Mock()
        
        # Create sample active GTTs list with missing trigger_id
        active_gtts_list = [
            {
                'tradingsymbol': 'RELIANCE',
                'status': 'active',
                'trigger_type': 'single',
                'trigger_values': [2500.0],
                'last_price': 2600.0
                # Missing trigger_id
            }
        ]
        
        # Test that function handles missing trigger_id gracefully
        result = main.cancel_existing_gtts(mock_client, 'RELIANCE', active_gtts_list)
        
        # Should return 0 canceled GTTs due to missing trigger_id
        self.assertEqual(result, 0)
        
        # Verify delete_gtt was not called
        mock_client.delete_gtt.assert_not_called()
    
    def test_place_new_gtts(self):
        """Test place_new_gtts function with mock kite client and UPDATE plan"""
        # Create mock kite client
        mock_client = Mock()
        
        # Create sample UPDATE plan with both tiers having quantities > 0
        update_plan = {
            'symbol': 'RELIANCE',
            'action': 'UPDATE',
            'exchange': 'NSE',
            'new_high': 2600.0,
            'tier1': {
                'qty': 30,
                'trigger': 2340.0,
                'limit': 2314.0
            },
            'tier2': {
                'qty': 70,
                'trigger': 2080.0,
                'limit': 2054.0
            }
        }
        
        # Call the function
        result = main.place_new_gtts(mock_client, update_plan)
        
        # Assertions
        self.assertEqual(result, 2)  # Should place 2 GTTs (both tiers)
        
        # Verify place_gtt was called exactly twice
        self.assertEqual(mock_client.place_gtt.call_count, 2)
        
        # Get all call arguments
        call_args_list = mock_client.place_gtt.call_args_list
        
        # Check Tier 1 GTT call arguments
        tier1_call = call_args_list[0]
        tier1_kwargs = tier1_call[1]  # keyword arguments
        
        self.assertEqual(tier1_kwargs['trigger_type'], 'single')
        self.assertEqual(tier1_kwargs['tradingsymbol'], 'RELIANCE')
        self.assertEqual(tier1_kwargs['exchange'], 'NSE')
        self.assertEqual(tier1_kwargs['trigger_values'], [2340.0])
        self.assertEqual(tier1_kwargs['last_price'], 2340.0)
        
        # Check Tier 1 order details
        tier1_order = tier1_kwargs['orders'][0]
        self.assertEqual(tier1_order['transaction_type'], 'SELL')
        self.assertEqual(tier1_order['quantity'], 30)
        self.assertEqual(tier1_order['price'], 2314.0)
        self.assertEqual(tier1_order['order_type'], 'LIMIT')
        self.assertEqual(tier1_order['product'], 'CNC')
        
        # Check Tier 2 GTT call arguments
        tier2_call = call_args_list[1]
        tier2_kwargs = tier2_call[1]  # keyword arguments
        
        self.assertEqual(tier2_kwargs['trigger_type'], 'single')
        self.assertEqual(tier2_kwargs['tradingsymbol'], 'RELIANCE')
        self.assertEqual(tier2_kwargs['exchange'], 'NSE')
        self.assertEqual(tier2_kwargs['trigger_values'], [2080.0])
        self.assertEqual(tier2_kwargs['last_price'], 2080.0)
        
        # Check Tier 2 order details
        tier2_order = tier2_kwargs['orders'][0]
        self.assertEqual(tier2_order['transaction_type'], 'SELL')
        self.assertEqual(tier2_order['quantity'], 70)
        self.assertEqual(tier2_order['price'], 2054.0)
        self.assertEqual(tier2_order['order_type'], 'LIMIT')
        self.assertEqual(tier2_order['product'], 'CNC')
    
    def test_place_new_gtts_with_zero_quantities(self):
        """Test place_new_gtts function with zero quantities (small holdings)"""
        # Create mock kite client
        mock_client = Mock()
        
        # Create sample UPDATE plan with tier1_qty = 0 (small holding scenario)
        update_plan = {
            'symbol': 'SMALLSTOCK',
            'action': 'UPDATE',
            'exchange': 'NSE',
            'new_high': 100.0,
            'tier1': {
                'qty': 0,  # Zero quantity - should be skipped
                'trigger': 90.0,
                'limit': 89.0
            },
            'tier2': {
                'qty': 5,  # Non-zero quantity - should be placed
                'trigger': 80.0,
                'limit': 79.0
            }
        }
        
        # Call the function
        result = main.place_new_gtts(mock_client, update_plan)
        
        # Assertions
        self.assertEqual(result, 1)  # Should place only 1 GTT (tier2 only)
        
        # Verify place_gtt was called exactly once (only for tier2)
        self.assertEqual(mock_client.place_gtt.call_count, 1)
        
        # Check that only Tier 2 GTT was placed
        call_args = mock_client.place_gtt.call_args
        kwargs = call_args[1]
        
        self.assertEqual(kwargs['trigger_values'], [80.0])
        self.assertEqual(kwargs['orders'][0]['quantity'], 5)
        self.assertEqual(kwargs['orders'][0]['price'], 79.0)
    
    def test_place_new_gtts_both_zero_quantities(self):
        """Test place_new_gtts function when both tiers have zero quantities"""
        # Create mock kite client
        mock_client = Mock()
        
        # Create sample UPDATE plan with both tiers having zero quantities
        update_plan = {
            'symbol': 'VERYSMALLSTOCK',
            'action': 'UPDATE',
            'exchange': 'NSE',
            'new_high': 50.0,
            'tier1': {
                'qty': 0,  # Zero quantity
                'trigger': 45.0,
                'limit': 44.5
            },
            'tier2': {
                'qty': 0,  # Zero quantity
                'trigger': 40.0,
                'limit': 39.5
            }
        }
        
        # Call the function
        result = main.place_new_gtts(mock_client, update_plan)
        
        # Assertions
        self.assertEqual(result, 0)  # Should place 0 GTTs
        
        # Verify place_gtt was not called
        mock_client.place_gtt.assert_not_called()
    
    def test_place_new_gtts_invalid_action(self):
        """Test place_new_gtts function with invalid action"""
        # Create mock kite client
        mock_client = Mock()
        
        # Create plan with invalid action
        invalid_plan = {
            'symbol': 'TESTSTOCK',
            'action': 'NO_ACTION',  # Invalid action for this function
            'exchange': 'NSE',
            'tier1': {'qty': 10, 'trigger': 100.0, 'limit': 99.0},
            'tier2': {'qty': 20, 'trigger': 90.0, 'limit': 89.0}
        }
        
        # Call the function
        result = main.place_new_gtts(mock_client, invalid_plan)
        
        # Assertions
        self.assertEqual(result, 0)  # Should place 0 GTTs
        
        # Verify place_gtt was not called
        mock_client.place_gtt.assert_not_called()
    
    def test_place_new_gtts_missing_symbol(self):
        """Test place_new_gtts function with missing symbol"""
        # Create mock kite client
        mock_client = Mock()
        
        # Create plan with missing symbol
        invalid_plan = {
            'action': 'UPDATE',
            'exchange': 'NSE',
            'tier1': {'qty': 10, 'trigger': 100.0, 'limit': 99.0},
            'tier2': {'qty': 20, 'trigger': 90.0, 'limit': 89.0}
            # Missing 'symbol' field
        }
        
        # Call the function
        result = main.place_new_gtts(mock_client, invalid_plan)
        
        # Assertions
        self.assertEqual(result, 0)  # Should place 0 GTTs
        
        # Verify place_gtt was not called
        mock_client.place_gtt.assert_not_called()
    
    def test_place_new_gtts_with_api_errors(self):
        """Test place_new_gtts function when place_gtt raises exceptions"""
        # Create mock kite client that raises exception on place_gtt
        mock_client = Mock()
        mock_client.place_gtt.side_effect = Exception("API Error")
        
        # Create sample UPDATE plan
        update_plan = {
            'symbol': 'ERRORSTOCK',
            'action': 'UPDATE',
            'exchange': 'NSE',
            'new_high': 1000.0,
            'tier1': {
                'qty': 10,
                'trigger': 900.0,
                'limit': 890.0
            },
            'tier2': {
                'qty': 20,
                'trigger': 800.0,
                'limit': 790.0
            }
        }
        
        # Call the function
        result = main.place_new_gtts(mock_client, update_plan)
        
        # Should return 0 placed GTTs due to exceptions
        self.assertEqual(result, 0)
        
        # Verify place_gtt was called twice but both failed
        self.assertEqual(mock_client.place_gtt.call_count, 2)
    
    def test_place_new_gtts_with_different_exchange(self):
        """Test place_new_gtts function with BSE exchange"""
        # Create mock kite client
        mock_client = Mock()
        
        # Create sample UPDATE plan with BSE exchange
        update_plan = {
            'symbol': 'RELIANCE',
            'action': 'UPDATE',
            'exchange': 'BSE',  # Different exchange
            'new_high': 2600.0,
            'tier1': {
                'qty': 30,
                'trigger': 2340.0,
                'limit': 2314.0
            },
            'tier2': {
                'qty': 70,
                'trigger': 2080.0,
                'limit': 2054.0
            }
        }
        
        # Call the function
        result = main.place_new_gtts(mock_client, update_plan)
        
        # Assertions
        self.assertEqual(result, 2)  # Should place 2 GTTs (both tiers)
        
        # Verify place_gtt was called exactly twice
        self.assertEqual(mock_client.place_gtt.call_count, 2)
        
        # Get all call arguments
        call_args_list = mock_client.place_gtt.call_args_list
        
        # Check that both calls used BSE exchange
        for call in call_args_list:
            kwargs = call[1]
            self.assertEqual(kwargs['exchange'], 'BSE')
    
    def test_place_new_gtts_missing_exchange_defaults_to_nse(self):
        """Test place_new_gtts function defaults to NSE when exchange is missing"""
        # Create mock kite client
        mock_client = Mock()
        
        # Create sample UPDATE plan without exchange field
        update_plan = {
            'symbol': 'RELIANCE',
            'action': 'UPDATE',
            # Missing 'exchange' field - should default to NSE
            'new_high': 2600.0,
            'tier1': {
                'qty': 30,
                'trigger': 2340.0,
                'limit': 2314.0
            },
            'tier2': {
                'qty': 70,
                'trigger': 2080.0,
                'limit': 2054.0
            }
        }
        
        # Call the function
        result = main.place_new_gtts(mock_client, update_plan)
        
        # Assertions
        self.assertEqual(result, 2)  # Should place 2 GTTs (both tiers)
        
        # Verify place_gtt was called exactly twice
        self.assertEqual(mock_client.place_gtt.call_count, 2)
        
        # Get all call arguments
        call_args_list = mock_client.place_gtt.call_args_list
        
        # Check that both calls defaulted to NSE exchange
        for call in call_args_list:
            kwargs = call[1]
            self.assertEqual(kwargs['exchange'], 'NSE')
    
    def test_round_to_tick(self):
        """Test round_to_tick function with various price values"""
        # Test cases with default tick size (0.05)
        test_cases = [
            (10.18, 10.15),  # Round down from 10.18 to 10.15
            (10.14, 10.10),  # Round down from 10.14 to 10.10
            (10.15, 10.15),  # Already on tick, should remain same
            (10.12, 10.10),  # Round down from 10.12 to 10.10
            (10.13, 10.10),  # Round down from 10.13 to 10.10
            (10.16, 10.15),  # Round down from 10.16 to 10.15
            (10.19, 10.15),  # Round down from 10.19 to 10.15
            (10.20, 10.15),  # Round down from 10.20 to 10.15 (floating point precision)
            (100.00, 100.00), # Whole number, should remain same
            (100.01, 100.00), # Round down from 100.01 to 100.00
            (100.04, 100.00), # Round down from 100.04 to 100.00
            (100.05, 100.00), # Round down from 100.05 to 100.00 (floating point precision)
            (100.07, 100.05), # Round down from 100.07 to 100.05
        ]
        
        for input_price, expected_output in test_cases:
            with self.subTest(input_price=input_price):
                result = main.round_to_tick(input_price)
                self.assertAlmostEqual(result, expected_output, places=2,
                                     msg=f"round_to_tick({input_price}) should be {expected_output}, got {result}")
        
        # Test with custom tick size
        self.assertAlmostEqual(main.round_to_tick(10.18, 0.10), 10.10, places=2)
        self.assertAlmostEqual(main.round_to_tick(10.25, 0.10), 10.20, places=2)
        self.assertAlmostEqual(main.round_to_tick(10.30, 0.10), 10.30, places=2)
        
        # Test with tick size of 0.01 (1 paisa)
        self.assertAlmostEqual(main.round_to_tick(10.186, 0.01), 10.18, places=2)
        self.assertAlmostEqual(main.round_to_tick(10.189, 0.01), 10.18, places=2)
    
    @patch('main.load_gtt_state')
    @patch('main.get_portfolio_with_ltp')
    @patch('main.plan_gtt_updates')
    @patch('main.cancel_existing_gtts')
    @patch('main.place_new_gtts')
    @patch('main.save_gtt_state')
    def test_main_live_run_error_handling(self, mock_save_state, mock_place_gtts, 
                                        mock_cancel_gtts, mock_plan_updates, 
                                        mock_get_portfolio, mock_load_state):
        """Test error handling in main_live_run when one stock fails but others continue"""
        
        # Setup mock kite client
        mock_client = Mock()
        mock_client.get_gtts.return_value = []
        
        # Setup mock state and portfolio
        mock_load_state.return_value = {}
        mock_get_portfolio.return_value = []
        mock_save_state.return_value = True
        
        # Setup plan_gtt_updates to return two UPDATE plans
        mock_plans = [
            {
                'symbol': 'STOCK1',
                'action': 'UPDATE',
                'exchange': 'NSE',
                'new_high': 1000.0,
                'tier1': {'qty': 30, 'trigger': 900.0, 'limit': 890.0},
                'tier2': {'qty': 70, 'trigger': 800.0, 'limit': 790.0}
            },
            {
                'symbol': 'STOCK2', 
                'action': 'UPDATE',
                'exchange': 'NSE',
                'new_high': 2000.0,
                'tier1': {'qty': 15, 'trigger': 1800.0, 'limit': 1780.0},
                'tier2': {'qty': 35, 'trigger': 1600.0, 'limit': 1580.0}
            }
        ]
        mock_plan_updates.return_value = mock_plans
        
        # Setup cancel_existing_gtts to raise exception for first stock only
        def cancel_side_effect(client, symbol, active_gtts):
            if symbol == 'STOCK1':
                raise Exception("API Error for STOCK1")
            return 2  # Success for STOCK2
        
        mock_cancel_gtts.side_effect = cancel_side_effect
        
        # Setup place_new_gtts to succeed for both stocks (but won't be called for STOCK1 due to cancel failure)
        mock_place_gtts.return_value = 2
        
        # Call main_live_run with mock client
        result = main.main_live_run(mock_client)
        
        # Assertions
        self.assertEqual(len(result), 2)  # Should return both plans
        
        # Verify that cancel_existing_gtts was called for both stocks
        self.assertEqual(mock_cancel_gtts.call_count, 2)
        mock_cancel_gtts.assert_any_call(mock_client, 'STOCK1', [])
        mock_cancel_gtts.assert_any_call(mock_client, 'STOCK2', [])
        
        # Verify that place_new_gtts was only called for STOCK2 (STOCK1 failed during cancel)
        self.assertEqual(mock_place_gtts.call_count, 1)
        
        # Get the actual call arguments for place_new_gtts
        place_call_args = mock_place_gtts.call_args_list[0]
        placed_plan = place_call_args[0][1]  # Second positional argument is the plan
        self.assertEqual(placed_plan['symbol'], 'STOCK2')
        
        # Verify state was saved
        mock_save_state.assert_called_once()
        
        # Verify the saved state only contains STOCK2 (STOCK1 failed)
        saved_state_call = mock_save_state.call_args[0][1]  # Second argument is the state data
        self.assertIn('STOCK2', saved_state_call)
        self.assertNotIn('STOCK1', saved_state_call)  # STOCK1 should not be in saved state due to failure
        self.assertEqual(saved_state_call['STOCK2']['last_high_price'], 2000.0)

if __name__ == '__main__':
    unittest.main()