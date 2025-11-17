Environment for Solidity / contract deployment (optional)
If you plan to compile and deploy the Solidity contracts yourself, you will also need:

Node.js and npm installed.

Inside backend/contracts/:

bash
cd backend/contracts
npm install
A separate .env in backend/contracts/ (this is already in your tree) with things like:

dotenv
RPC_URL=https://goerli.infura.io/v3/your-key
PRIVATE_KEY=0xyourprivatekey
The exact variable names depend on how deploy_v2.py / JS scripts are written.

If you do not care about on‑chain deployment, you can ignore this whole section.

Running the app (local simulation)
From the project root:

bash
streamlit run frontend/app.py
Streamlit will print a local URL, usually:

text
You can now view your Streamlit app in your browser.

  Local URL: http://localhost:8501
Open that URL in your browser.

Using the simulator
Start the app as above.

In the sidebar you will see Web3 status:

✅ Web3 connection OK if the RPC endpoint and contract address are valid.
⚠️ Cannot connect to blockchain... otherwise. In this case, the app automatically runs in local simulation mode.
Select run mode on the main page:

Local simulation (recommended)
Uses the pure Python model in backend/model.py + backend/controller.py.
On-chain mode (requires contract/keys)
Forwards some actions to the contract at STABLE_ADDR using backend/web3_api.py. This is experimental.
Click “Start simulation”:

The app runs for 500 steps (configurable in frontend/app.py).
You’ll see:
Live LUNA & UST prices at the top.

A 4×2 Plotly dashboard:

Row 1: LUNA & UST prices (CEX, smoothed).
Row 2: LUNA & UST total supplies + mint/burn volumes.
Row 3: AMM vs CEX LUNA price, UST/LUNA spreads, LFG reserve, LFG spending.
Row 4: AMM pool balances, relative 
k/k0
​
 , UST share, per‑step slippage.
When finished you will see Simulation finished!.

Exporting figures (for papers / reports)
All charts are interactive Plotly figures. To export:

Hover over any chart panel.
Click the camera icon (“Download plot as PNG”).
Save the image (e.g. luna_price_cex.png, ust_price_cex.png, luna_supply_mint_burn.png, etc.).
Use these images directly in LaTeX / Overleaf or other documents.
Commonly useful panels:

LUNA price (CEX)
UST price (CEX)
LUNA supply + mint/burn
UST supply + mint/burn
LFG reserve + spending
AMM pool balances and k/k0  
​
 
Model overview (high level)
The core discrete‑time model (in backend/model.py) updates the system once per step:

Apply exogenous shocks
Large UST or LUNA sell orders at specified steps (from a preset scenario).

Update CEX prices
Use an asymmetric bounded impact function with decaying depth:
prices move by a capped log‑return depending on net USD order flow and current depth.

Bank‑run withdrawals
Model panic exits as an additional UST sell flow that grows with the de‑peg and a time‑varying “panic” factor.

Mint/burn arbitrage

If UST < $1: redeem UST for $1 worth of LUNA at an oracle price, burn UST, mint LUNA (with caps).
If UST > $1: optionally mint UST and burn LUNA (with lower intensity).
Route minted LUNA

A fraction goes straight to the AMM to be sold.
The rest goes into a queue that drips LUNA onto the CEX over future steps.
AMM trades
Run swaps in a constant‑product UST–LUNA pool, tracking reserves, implied price, 
k
k, and UST share.

LFG reserve intervention
When UST is slightly below $1, a finite reserve buys UST, partially offsetting sell flows.
When the de‑peg is too deep or the reserve is exhausted, intervention stops.

Liquidity withdrawal
As the de‑peg worsens, liquidity providers withdraw from the AMM, shrinking the pool and amplifying price moves.

Record metrics
At each step the simulator logs prices, supplies, LFG reserve, pool state, spreads, and slippage for plotting.

For a more complete mathematical description (including formulas), see the accompanying LaTeX report (if included) or your documentation.

Customising the scenario
The main initial conditions and parameters are defined in terra_may_2022_preset() inside frontend/app.py:

Initial conditions

ust_supply, luna_supply
ust_price, luna_price
pool_ust, pool_luna
lfg_reserve_usd, etc.
External events (ext_events)

python
"ext_events": [
    {"step": 20, "type": "ust_sell",  "usd": 250_000_000, "latency": 0},
    {"step": 28, "type": "ust_sell",  "usd": 300_000_000, "latency": 0},
    {"step": 36, "type": "luna_sell", "usd": 200_000_000, "latency": 0},
    ...
]
Modify these to test different attack sizes and timings.

Model parameters (params)

Includes:

AMM fee, max_trade_mult
redeem_alpha, max_redeem_usd_frac, max_luna_mint_frac_of_supply
Bank‑run curve: bankrun_low, bankrun_high, bankrun_t0, bankrun_tau, max_bankrun_frac
CEX depth and impact asymmetry
LFG trigger level, per‑step spend, cutoff de‑peg, effectiveness decay
LP withdrawal rates: pool_drain_base, pool_drain_slope
Hard bounds on prices: ust_min, ust_max, luna_min, luna_max
After changing parameters, restart the Streamlit app to see the new dynamics.

On‑chain mode (experimental)
If you want to run the logic against a real contract:

Deploy the contract

Use the Solidity sources in backend/contracts/ (AlgoStableV2.sol).
Compile and deploy via your preferred tool (e.g. Hardhat, Truffle, or the provided scripts such as deploy_v2.py).
Note the deployed address of AlgoStableV2.
Configure the Python Web3 layer

Put the contract address into backend/.env as STABLE_ADDR.
Set WEB3_PROVIDER_URL to your RPC endpoint.
Set ACCOUNT_ADDRESS (and the private key if web3_api.py needs signing).
Start the app

Run streamlit run frontend/app.py.
Choose “On-chain mode (requires contract/keys)” in the UI.
If Web3 initialisation fails, the app falls back to local simulation automatically.
The exact interaction pattern with the contract depends on how backend/controller.py and backend/web3_api.py are implemented.

Development notes
Python: recommended 3.9+ (tested with ≥3.10).
Node.js: needed only if you want to work with the Solidity contracts in backend/contracts/.
Code organisation:
Keep simulation logic in backend/model.py and orchestration in backend/controller.py.
Keep UI code in frontend/app.py.
Ideas for extensions:
Add multiple stablecoins or additional pools.
Model other reserve assets explicitly (e.g. BTC, ETH).
Add agent‑based behaviour with explicit expectations.
Calibrate parameters against real market data.
License
Choose a license and add it here, for example:
