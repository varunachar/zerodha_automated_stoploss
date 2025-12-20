# Setup Guide for Zerodha GTT Automation

This guide is designed for non-developers to set up and run the Zerodha Automated Stop-Loss system on their computer.

## What this tool does
This tool connects to your Zerodha account, checks your stock holdings, and automatically sets "Good Till Triggered" (GTT) stop-loss orders to protect your profits. It helps you manage risk without constantly watching the market.

---

## Part 1: Install Required Software

You need two things installed on your computer: **Python** (to run the code) and a **Code Editor** (to change settings).

### 1. Install Python
Python is the programming language this tool is built with.
1.  Go to the [Python Downloads Page](https://www.python.org/downloads/).
2.  Click the big yellow button **"Download Python 3.x.x"**.
3.  Run the installer you downloaded.
    *   **IMPORTANT for Windows Users**: On the first screen of the installer, check the box that says **"Add Python to PATH"**. This is critical!
4.  Follow the instructions to finish installation.

### 2. Install VS Code (Optional but Recommended)
You need a way to edit the configuration file. You can use Notepad or TextEdit, but VS Code makes it easier.
1.  Download [Visual Studio Code](https://code.visualstudio.com/download).
2.  Install it like any normal program.

---

## Part 2: Download the Project

1.  Download this project code (if you haven't already).
    *   If you are on GitHub, click the green **Code** button -> **Download ZIP**.
2.  Unzip the folder to a location you can easily find (e.g., your `Desktop` or `Documents` folder).
3.  Rename the folder to something simple like `kite-gtt`.

---

## Part 3: Zerodha API Setup

To verify your identity and place orders, this tool needs access to your Zerodha account via their "Kite Connect" API.

1.  **Register for Kite Connect**:
    *   Go to [developers.kite.trade](https://developers.kite.trade/).
    *   Sign up for an account. **Note**: Zerodha charges ₹2000 per month for this API service. This is required for any automated trading tool.
2.  **Create an App**:
    *   Log in to the developer portal.
    *   Click **"Create New App"**.
    *   **App Name**: `AutoStopLoss` (or anything you like).
    *   **Zerodha Client ID**: Enter your Zerodha user ID (e.g., AB1234).
    *   **Redirect URL**: Copy and paste this EXACTLY:
        ```
        http://localhost:5001/callback
        ```
    *   **Description**: `Automated GTT Manager`.
    *   Click **Create**.
3.  **Get Your Keys**:
    *   Once created, click on your app name.
    *   You will see an **API Key** and an **API Secret**. Keep this page open; you will need these in the next step.

---

## Part 4: Configure the Tool

Now we need to tell the tool your API keys.

1.  Open the `kite-gtt` folder you unzipped in Part 2.
2.  Find the file named `config.py`.
3.  Right-click it and select **Open with VS Code** (or your preferred text editor).
4.  Find the lines that look like this (around line 21):
    ```python
    API_KEY = "bh00266o5f0h4lpd"
    API_SECRET = "ilfbmkjlmu5hjqv7dhym7fgmhhz1ra7f"
    ```
5.  Replace the text inside the quotes with **your** actual keys from the Zerodha developer page.
    *   Example: `API_KEY = "your_actual_api_key_here"`
6.  **Safety Setting**:
    Find the line around line 9:
    ```python
    MONITORING_MODE = False
    ```
    Change it to `True` for your first run:
    ```python
    MONITORING_MODE = True
    ```
    *This ensures the tool only **shows** you what it would do, without actually placing any orders.*

7.  Save the file (Ctrl+S or Cmd+S).

---

## Part 5: One-Time Installation of Libraries

You need to install some "helper" code libraries that our project uses.

1.  Open your computer's Terminal (Mac) or Command Prompt (Windows).
    *   **Mac**: Press `Cmd + Space`, type `Terminal`, and hit Enter.
    *   **Windows**: Press `Start`, type `cmd`, and hit Enter.
2.  Navigate to your project folder.
    *   Type `cd` (space), then **drag and drop** the `kite-gtt` folder from your desktop into the terminal window. It will paste the path for you.
    *   Press Enter.
3.  Run this command to install dependencies:
    ```bash
    pip install -r requirements.txt
    ```
    (Note: If `pip` doesn't work, try `pip3`)

---

## Part 6: How to Run the Tool

You will do this every time you want to check your portfolio and update stop-losses.

### Option A: The Easy Way (Mac Only)
1.  Open Terminal.
2.  Navigate to the folder.
3.  Type:
    ```bash
    ./run.sh
    ```

### Option B: The Standard Way
1.  Open Terminal/Command Prompt and navigate to the folder (as in Step 5.2).
2.  Run the program:
    ```bash
    python main.py
    ```
    (Or `python3 main.py` on Mac)
3.  You will see a message:
    ```
    --- STARTING WEB SERVER ---
    Please open http://localhost:5001 in your browser
    ```
4.  Open your web browser (Chrome, Safari, etc.) and go to:
    [http://localhost:5001](http://localhost:5001)
5.  Click the big green button **"Login with Zerodha"**.
6.  Log in with your Zerodha credentials on the page that opens.
7.  After login, you will be redirected back to a report page.
    *   **If MONITORING_MODE = True**: It will show you a comprehensive report of what GTTs *would* be placed.
    *   **If MONITORING_MODE = False**: It will actively CANCEL old GTTs and PLACE new ones.

---

## Troubleshooting

*   **"pip command not found"**: You didn't add Python to PATH (Windows) or need to use `pip3` (Mac).
*   **"Login Failed" or Redirect Error**: Double-check your **Redirect URL** in the Zerodha Developer Portal. It MUST be `http://localhost:5001/callback`.
*   **Browser says "This site can't be reached"**: Ensure the black Terminal window is still open and running the `main.py` script.
