### Prompt 1: Initial Setup and File Structure
User Prompt: "Let's start building a Python application to automate my Zerodha GTT stop-loss strategy using the kiteconnect library.

First, create the file structure for this project:

main.py: This will contain our core application logic.

config.py: This will hold our strategy configuration and API keys.

test_strategy.py: This will contain all our unittest tests.

gtt_state.json: This file will be used to store the last-known high price for each stock. Leave it empty for now (e.g., {}).

In config.py, add initial placeholder content:

```Python
# config.py
DRY_RUN = True  # Master switch for safety
STATE_FILE_PATH = 'gtt_state.json'

# API Keys (leave as placeholders)
API_KEY = "YOUR_API_KEY"
API_SECRET = "YOUR_API_SECRET"
ACCESS_TOKEN = "YOUR_ACCESS_TOKEN" # This will be generated daily

# Strategy Parameters
TIER_1_QTY_PCT = 0.30  # 30% of holding
TIER_1_TRIGGER_PCT = 0.10  # 10% from high
TIER_1_LIMIT_PCT = 0.11    # 11% from high
TIER_2_TRIGGER_PCT = 0.20  # 20% from high
TIER_2_LIMIT_PCT = 0.21    # 21% from high
```
In main.py, add the necessary imports (kiteconnect, json, logging, config) and a placeholder get_kite_client() function."

### Prompt 2: Epic 1 (Story 1.2 & 1.3) - Fetching Portfolio Data
User Prompt: "In main.py, create a function get_portfolio_with_ltp(kite_client). This function should:

Call kite_client.holdings() to get the portfolio.

Filter this list to include only instruments of instrument_type == 'EQ' and quantity > 0.

From the filtered list, create a list of tradingsymbol strings.

Call kite_client.ltp(tradingsymbol_list) to get the Last Traded Price (LTP) for all holdings.

Merge the LTP back into the holdings list, so each item in the returned list is a dictionary containing at least tradingsymbol, quantity, and last_price.

Return this merged list.

In test_strategy.py, write a unit test test_get_portfolio_with_ltp.

Use unittest.mock to create a mock kite_client.

Mock kite_client.holdings() to return a sample list containing:

An 'EQ' stock with quantity > 0.

An 'EQ' stock with quantity = 0.

A 'MF' (Mutual Fund) instrument.

Mock kite_client.ltp() to return a sample LTP dictionary.

Assert that the function's returned list only contains the valid 'EQ' stock and that its dictionary has been correctly updated with the last_price."

### Prompt 3: Epic 1 (Story 1.4) - State Management
User Prompt: "In main.py, create two functions for state management:

load_gtt_state(filepath):

This function should try to open and read the JSON file at filepath.

If the file exists and contains valid JSON, return the loaded dictionary.

If the file does not exist (FileNotFoundError) or is empty/invalid, return an empty dictionary {}.

save_gtt_state(filepath, state_data):

This function should write the state_data dictionary to the filepath in JSON format.

In test_strategy.py, write unit tests for these:

test_load_gtt_state_file_exists: Use unittest.mock.patch('builtins.open', unittest.mock.mock_open(read_data='{"RELIANCE": {"last_high_price": 2500}}')) to simulate reading a file. Assert the correct dictionary is returned.

test_load_gtt_state_file_not_found: Simulate a FileNotFoundError and assert an empty dictionary {} is returned.

test_save_gtt_state: Use unittest.mock.patch('builtins.open', unittest.mock.mock_open()) and assert that the file is written to with the correct JSON string."

### Prompt 4: Epic 1 (Story 1.5) - Core Logic (Plan Generation)
User Prompt: "This is the core logic. In main.py, create a function plan_gtt_updates(portfolio, gtt_state, config). This function will not call any APIs; it only performs calculations.

It should iterate through each holding in the portfolio and:

Get the last_high_price from gtt_state. If the stock is not in the state (new holding), use its current last_price as the last_high_price.

Compare the holding['last_price'] to the last_high_price.

If holding['last_price'] <= last_high_price: The stock has not hit a new high. The function should generate a 'plan' dictionary: {'symbol': 'TCS', 'action': 'NO_ACTION', 'reason': 'LTP (3000) not a new high (3050)'}.

If holding['last_price'] > last_high_price: This is a new high. The script must calculate the new GTTs.

new_high = holding['last_price']

tier1_trigger = new_high * (1 - config.TIER_1_TRIGGER_PCT)

tier1_limit = new_high * (1 - config.TIER_1_LIMIT_PCT)

tier2_trigger = new_high * (1 - config.TIER_2_TRIGGER_PCT)

tier2_limit = new_high * (1 - config.TIER_2_LIMIT_PCT)

tier1_qty = int(holding['quantity'] * config.TIER_1_QTY_PCT)

tier2_qty = holding['quantity'] - tier1_qty

Generate a 'plan' dictionary: {'symbol': 'RELIANCE', 'action': 'UPDATE', 'new_high': 2600, 'tier1': {'qty': 30, 'trigger': 2340, 'limit': 2314}, 'tier2': {'qty': 70, 'trigger': 2080, 'limit': 2054}}

The function should return a list of all these 'plan' dictionaries.

In test_strategy.py, write tests for plan_gtt_updates:

test_plan_no_action: Pass a holding whose LTP is less than its last_high_price. Assert the returned plan's action is NO_ACTION.

test_plan_update_action: Pass a holding whose LTP is greater than its last_high_price. Assert the action is UPDATE and that all calculated trigger, limit, and qty values are correct based on the config.

test_plan_new_stock: Pass a holding that is not in the gtt_state. Assert the action is NO_ACTION (as LTP cannot be greater than itself on the first run)."

### Prompt 5: Epic 1 (Orchestration) - The "Dry Run" Main Function
User Prompt: "In main.py, create the main_dry_run() function. This function should:

Initialize a mock kite_client (since we are not placing orders yet, it doesn't need real credentials for this part).

Call load_gtt_state() to get the current state.

Call get_portfolio_with_ltp() (you will need to mock this for now, as we aren't live).

Call plan_gtt_updates() with the portfolio and state.

Iterate through the returned plans and print a formatted, human-readable report to the console (e.g., RELIANCE: NO_ACTION or TCS: ACTION_UPDATE | New GTTs planned...).

This function will be the main entry point while config.DRY_RUN is True."

### Prompt 6: Epic 2 (Story 2.2 & 2.3) - Canceling GTTs
User Prompt: "Now we'll add the live execution logic, which will run when DRY_RUN = False.

In main.py, create cancel_existing_gtts(kite_client, tradingsymbol, active_gtts_list).

This function will receive the list of all active GTTs fetched once from kite_client.get_gtts().

It should find all GTTs in that list where gtt['tradingsymbol'] == tradingsymbol and gtt['status'] == 'active'.

For each one it finds, it should call kite_client.delete_gtt(trigger_id=gtt['trigger_id']).

It should log to the console which GTTs are being canceled.

In test_strategy.py, write test_cancel_existing_gtts:

Create a mock kite_client.

Create a sample active_gtts_list with multiple GTTs for different symbols.

Call the function with a specific tradingsymbol.

Assert that kite_client.delete_gtt was called the correct number of times and only with the trigger_ids of the matching stock."

### Prompt 7: Epic 2 (Story 2.4) - Placing GTTs
User Prompt: "In main.py, create place_new_gtts(kite_client, plan).

This function will receive a single 'plan' dictionary where action == 'UPDATE'.

It must call kite_client.place_gtt() twice:

Tier 1: Using plan['tier1'] data. Set gtt_type='single', transaction_type='SELL'.

Tier 2: Using plan['tier2'] data. Set gtt_type='single', transaction_type='SELL'.

It should log to the console that the new GTTs have been placed.

It must handle the case where tier1_qty or tier2_qty is 0 (e.g., small holding) and not place that GTT.

In test_strategy.py, write test_place_new_gtts:

Create a mock kite_client.

Create a sample 'UPDATE' plan.

Call the function with the plan.

Assert that kite_client.place_gtt was called exactly twice.

Check the call_args to ensure all parameters (quantity, price, type) were passed correctly for both tiers."

### Prompt 8: Epic 2 (Orchestration) - The "Live Run" Main Function
User Prompt: "In main.py, create the main_live_run() function. This is the main orchestrator. It should:

Initialize a real kite_client (using config.ACCESS_TOKEN, etc.).

Call `load_gtt_state()`.

Call `get_portfolio_with_ltp()`.

Call `kite_client.get_gtts()` to get all active GTTs.

Call `plan_gtt_updates()` to get the list of plans.

Loop through the plans:

If `plan['action'] == 'UPDATE'`:

Call `cancel_existing_gtts(kite_client, plan['symbol'], active_gtts)`.

Call `place_new_gtts(kite_client, plan)`.

Update the local `gtt_state dictionary: gtt_state[plan['symbol']] = {'last_high_price': plan['new_high']}`.

After the loop finishes, call `save_gtt_state()` to save the updated state to disk.

Finally, create the main entry point:"

```Python
if __name__ == "__main__":
    if config.DRY_RUN:
        print("--- RUNNING IN DRY-RUN MODE ---")
        main_dry_run()
    else:
        print("--- RUNNING IN LIVE MODE ---")
        main_live_run()
```


### Prompt 9: Epic 3 (Story 3.2 & 3.3) - Robustness
User Prompt: "Let's make the script more robust.

First, in main.py, create a utility function round_to_tick(price, tick_size=0.05).

Zerodha's API rejects prices that are not in a valid "tick size" (usually 5 paise).

This function must round a price down to the nearest valid tick. (e.g., 10.18 becomes 10.15, 10.14 becomes 10.10).

Refactor plan_gtt_updates to use this function for all calculated trigger and limit prices.

Second, refactor main_live_run().

Wrap the for plan in plans: loop's contents in a try...except Exception as e: block.

If an exception occurs for one stock (e.g., API error, invalid quantity), the script must log the error (e.g., [RELIANCE]: FAILED to process. Error: {e}) and then continue to the next stock. It must not crash.

In test_strategy.py, add:

test_round_to_tick: Test it with multiple values (e.g., 10.18 -> 10.15, 10.12 -> 10.10, 10.15 -> 10.15).

A test for the error handling in main_live_run. Mock plan_gtt_updates to return two 'UPDATE' plans. Mock cancel_existing_gtts for the first plan to raise an exception. Assert that the script still attempts to process the second plan (i.e., that place_new_gtts is still called for the second plan)."