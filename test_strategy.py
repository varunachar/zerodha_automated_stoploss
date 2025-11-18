#!/usr/bin/env python3
"""
Unit tests for GTT Stop-Loss Strategy
"""

import unittest
import json
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
        """Test that get_kite_client function exists"""
        self.assertTrue(callable(getattr(main, 'get_kite_client')))
    
    def test_logging_setup(self):
        """Test that logging is properly configured"""
        logger = logging.getLogger(__name__)
        self.assertIsNotNone(logger)
        self.assertEqual(logger.level, logging.INFO)
    
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
            },
            {
                'tradingsymbol': 'HDFC_MF',
                'instrument_type': 'MF',  # Mutual Fund (should be filtered out)
                'quantity': 100,
                'instrument_token': 123456,
                'exchange': 'NSE',
                'product': 'CNC',
                'average_price': 1000.0
            }
        ]
        
        # Mock LTP data - only for the valid EQ stock
        mock_ltp = {
            'RELIANCE': {'last_price': 2600.0}
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
        self.assertEqual(holding['tradingsymbol'], 'RELIANCE')
        self.assertEqual(holding['quantity'], 10)
        self.assertEqual(holding['last_price'], 2600.0)
        
        # Verify API calls
        mock_client.holdings.assert_called_once()
        mock_client.ltp.assert_called_once_with(['RELIANCE'])  # Only RELIANCE should be queried for LTP
    
    @patch('main.kiteconnect.KiteConnect')
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
    
    @patch('builtins.open', mock_open())
    @patch('os.makedirs')
    def test_save_gtt_state(self, mock_makedirs, mock_file):
        """Test save_gtt_state with mocked file operations"""
        test_data = {"RELIANCE": {"last_high_price": 2500}}
        result = main.save_gtt_state('test_state.json', test_data)
        
        self.assertTrue(result)
        mock_file.assert_called_once_with('test_state.json', 'w')
        
        # Verify the file was written with correct JSON
        mock_file.return_value.write.assert_called_once()
        written_content = mock_file.return_value.write.call_args[0][0]
        expected_json = json.dumps(test_data, indent=2)
        self.assertEqual(written_content, expected_json)
    
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

if __name__ == '__main__':
    unittest.main()