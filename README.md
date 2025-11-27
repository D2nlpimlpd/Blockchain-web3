# LUNA–UST Collapse Simulator

Interactive simulator of a Terra-style algorithmic stablecoin system, focusing on the May 2022 LUNA–UST “death spiral”.

The video demonstration webpage link for this project is：https://youtu.be/VXG-TY5stcs3

The project combines:

- A **discrete‑time simulation engine** (Python, in `backend/`)
- A **Streamlit** front‑end with a 4×2 Plotly dashboard (in `frontend/`)
- Optional **Web3 + Solidity contracts** (in `backend/contracts/`) to deploy and test an on‑chain implementation

It is designed for research, teaching, and stress‑testing algorithmic stablecoin designs.

---

## Features

- **Historical-style preset**  
  One‑click preset that roughly mimics the May 2022 Terra breakdown (pre‑crisis stability → peg defence → death spiral).

- **Mechanistic model components**
  - Constant‑product **AMM** pool (UST–LUNA)
  - Asymmetric, bounded **CEX price impact** with decaying depth
  - On‑chain style **mint/burn arbitrage** (UST ↔ LUNA)
  - Time‑varying **bank‑run dynamics**
  - **LFG reserve** that defends the peg and then runs out
  - **Liquidity withdrawal** from the AMM as the de‑peg worsens
  - **Delayed LUNA sell queue** (not all minted LUNA is dumped at once)

- **Rich visualisation (Plotly)**
  - LUNA / UST prices on CEX
  - Mint / burn volumes and total supplies
  - AMM vs CEX price, price spreads
  - LFG reserve level and per‑step spending
  - Pool balances, relative \(k/k_0\), UST share, slippage

- **Two run modes**
  - 🧮 **Local simulation (recommended)** — purely off‑chain, deterministic  
  - 🔗 **On‑chain mode (experimental)** — can be wired to a deployed contract via Web3

---

## Project structure

    .
    ├── backend/
    │   ├── __pycache__/
    │   ├── .env                    # Python backend / Web3 config (local)
    │   ├── AlgoStableV2_abi.json   # ABI for the on-chain contract (used by web3_api.py)
    │   ├── controller.py           # High-level simulation step orchestration
    │   ├── model.py                # Core discrete-time model (AMM, bank run, etc.)
    │   ├── requirements.txt        # Python dependencies for backend + frontend
    │   ├── web3_api.py             # Web3 provider + helpers for on-chain mode
    │   ├── Blockchain-web3/        # (Optional) extra Web3 utilities / scripts
    │   └── contracts/              # Solidity contracts + deployment scripts
    │       ├── @openzeppelin/      # OpenZeppelin contracts (installed via npm)
    │       ├── node_modules/       # JS dependencies
    │       ├── .env                # Contract deployment config (RPC, private key, etc.)
    │       ├── AlgoStable.sol      # Original algorithmic stablecoin contract
    │       ├── AlgoStableV2.sol    # V2 contract (used by this simulator)
    │       ├── MyToken.sol         # Simple ERC20 test token
    │       ├── compile_v2.py       # Helper to compile V2 (e.g. via solcx/web3)
    │       ├── deploy_v2.py        # Python deployment script for AlgoStableV2
    │       ├── deploy.py           # Generic deployment script (earlier version)
    │       ├── init_state_check.py # Sanity checks on on-chain state
    │       ├── package.json        # JS project config (for Hardhat/Truffle/etc.)
    │       └── package-lock.json   # npm lockfile
    ├── frontend/
    │   ├── static/                 # Static assets (if any)
    │   ├── app.py                  # Streamlit UI + plotting + simulation loop
    │   └── index.html              # Optional landing page / wrapper
    ├── output/                     # Optional: exported figures / logs
    └── README.md                   # This file

---

## Installation

### 1. Clone the repository

    git clone https://github.com/<your-username>/<your-repo>.git
    cd <your-repo>

### 2. Create and activate a virtual environment (optional but recommended)

On macOS / Linux:

    python -m venv .venv
    source .venv/bin/activate

On Windows (PowerShell / CMD):

    python -m venv .venv
    .venv\Scripts\activate

### 3. Install Python dependencies

Use the backend requirements file:

    pip install -r backend/requirements.txt

This should install (among others):

- `streamlit`, `plotly`, `pandas`
- `web3`, `python-dotenv`

If some packages are missing, install them manually with:

    pip install <package>

---

## Configuration

### Environment variables for the Python/Web3 layer

The Python backend reads a `.env` in `backend/` (via `python-dotenv`) to configure Web3 / on‑chain mode.

Create `backend/.env`:

    cd backend
    touch .env

Populate it with at least:

    # Address of the deployed AlgoStableV2 contract (for on-chain mode)
    STABLE_ADDR=0xYourStableContractAddress

    # Address you control (EOA, for transactions, if needed)
    ACCOUNT_ADDRESS=0xYourEOAAddress

    # RPC endpoint used by web3_api.py
    WEB3_PROVIDER_URL=https://mainnet.infura.io/v3/your-key

If you only want **local simulation**, you can leave `STABLE_ADDR` and `ACCOUNT_ADDRESS` empty.
The frontend will detect that Web3 is not available and automatically fall back to local mode.

### Environment for Solidity / contract deployment (optional)

If you plan to **compile and deploy** the Solidity contracts yourself, you will also need:

1. **Node.js and npm** installed.
2. Inside `backend/contracts/`:

       cd backend/contracts
       npm install

3. A separate `.env` in `backend/contracts/` with things like:

       RPC_URL=https://goerli.infura.io/v3/your-key
       PRIVATE_KEY=0xyourprivatekey

The exact variable names depend on how `deploy_v2.py` / JS scripts are written.

If you do not care about on‑chain deployment, you can ignore this whole section.

---

## Running the app (local simulation)

From the project **root**:

    streamlit run frontend/app.py

Streamlit will print a local URL, usually:

    You can now view your Streamlit app in your browser.

      Local URL: http://localhost:8501

Open that URL in your browser.

---

## Using the simulator

1. **Start the app** as above.
2. In the sidebar you will see Web3 status:
   - `✅ Web3 connection OK` if the RPC endpoint and contract address are valid.
   - `⚠️ Cannot connect to blockchain...` otherwise.  
     In this case, the app automatically runs in **local simulation** mode.

3. **Select run mode** on the main page:
   - `Local simulation (recommended)` — uses the pure Python model in `backend/model.py` + `backend/controller.py`.
   - `On-chain mode (requires contract/keys)` — forwards some actions to the contract at `STABLE_ADDR` using `backend/web3_api.py` (experimental).

4. Click **“Start simulation”**:
   - The app runs for 500 steps (configurable in `frontend/app.py`).
   - You’ll see:
     - Live LUNA & UST prices at the top.
     - A 4×2 Plotly dashboard:

       - **Row 1:** LUNA & UST prices (CEX, smoothed).
       - **Row 2:** LUNA & UST total supplies + mint/burn volumes.
       - **Row 3:** AMM vs CEX LUNA price, UST/LUNA spreads, LFG reserve, LFG spending.
       - **Row 4:** AMM pool balances, relative \(k/k_0\), UST share, per‑step slippage.

5. When finished you will see a message like `Simulation finished!`.

---

## Exporting figures (for papers / reports)

All charts are interactive Plotly figures. To export:

1. Hover over any chart panel.
2. Click the **camera** icon (“Download plot as PNG”).
3. Save the image (e.g. `luna_price_cex.png`, `ust_price_cex.png`, `luna_supply_mint_burn.png`, etc.).
4. Use these images directly in LaTeX / Overleaf or other documents.

Commonly useful panels:

- LUNA price (CEX)  
- UST price (CEX)  
- LUNA supply + mint/burn  
- UST supply + mint/burn  
- LFG reserve + spending  
- AMM pool balances and \(k/k_0\)

---

## Model overview (high level)

The core discrete‑time model (in `backend/model.py`) updates the system once per step:

1. **Apply exogenous shocks**  
   Large UST or LUNA sell orders at specified steps (from a preset scenario).

2. **Update CEX prices**  
   Use an **asymmetric bounded impact function** with decaying depth:
   prices move by a capped log‑return depending on net USD order flow and current depth.

3. **Bank‑run withdrawals**  
   Model panic exits as an additional UST sell flow that grows with the de‑peg and a time‑varying “panic” factor.

4. **Mint/burn arbitrage**  
   - If UST \< \$1: redeem UST for \$1 worth of LUNA at an oracle price, burn UST, mint LUNA (with caps).
   - If UST \> \$1: optionally mint UST and burn LUNA (with lower intensity).

5. **Route minted LUNA**
   - A fraction goes straight to the AMM to be sold.
   - The rest goes into a **queue** that drips LUNA onto the CEX over future steps.

6. **AMM trades**  
   Run swaps in a constant‑product UST–LUNA pool, tracking reserves, implied price, \(k\), and UST share.

7. **LFG reserve intervention**  
   When UST is slightly below \$1, a finite reserve buys UST, partially offsetting sell flows.  
   When the de‑peg is too deep or the reserve is exhausted, intervention stops.

8. **Liquidity withdrawal**  
   As the de‑peg worsens, liquidity providers withdraw from the AMM, shrinking the pool and amplifying price moves.

9. **Record metrics**  
   At each step the simulator logs prices, supplies, LFG reserve, pool state, spreads, and slippage for plotting.

For a more complete mathematical description (including formulas), see your accompanying paper / LaTeX document if available.

---

## Customising the scenario

The main initial conditions and parameters are defined in `terra_may_2022_preset()` inside `frontend/app.py`:

- **Initial conditions**
  - `ust_supply`, `luna_supply`
  - `ust_price`, `luna_price`
  - `pool_ust`, `pool_luna`
  - `lfg_reserve_usd`, etc.

- **External events (`ext_events`)**, for example:

      "ext_events": [
          {"step": 20, "type": "ust_sell",  "usd": 250_000_000, "latency": 0},
          {"step": 28, "type": "ust_sell",  "usd": 300_000_000, "latency": 0},
          {"step": 36, "type": "luna_sell", "usd": 200_000_000, "latency": 0}
      ]

  Modify these to test different attack sizes and timings.

- **Model parameters (`params`)**

  Includes (non‑exhaustive):

  - AMM fee, `max_trade_mult`
  - `redeem_alpha`, `max_redeem_usd_frac`, `max_luna_mint_frac_of_supply`
  - Bank‑run curve: `bankrun_low`, `bankrun_high`, `bankrun_t0`, `bankrun_tau`, `max_bankrun_frac`
  - CEX depth and impact asymmetry
  - LFG trigger level, per‑step spend, cutoff de‑peg, effectiveness decay
  - LP withdrawal rates: `pool_drain_base`, `pool_drain_slope`
  - Hard bounds on prices: `ust_min`, `ust_max`, `luna_min`, `luna_max`

After changing parameters, restart the Streamlit app to see the new dynamics.

---

## On‑chain mode (experimental)

If you want to run the logic against a real contract:

1. **Deploy the contract**

   - Use the Solidity sources in `backend/contracts/` (`AlgoStableV2.sol`).
   - Compile and deploy via your preferred tool (Hardhat, Truffle, Foundry, or the provided Python scripts such as `deploy_v2.py`).
   - Note the deployed address of `AlgoStableV2`.

2. **Configure the Python Web3 layer**

   - Put the contract address into `backend/.env` as `STABLE_ADDR`.
   - Set `WEB3_PROVIDER_URL` to your RPC endpoint.
   - Set `ACCOUNT_ADDRESS` (and the private key if `web3_api.py` needs signing).

3. **Start the app**

   - Run `streamlit run frontend/app.py`.
   - Choose **“On-chain mode (requires contract/keys)”** in the UI.
   - If Web3 initialisation fails, the app falls back to local simulation automatically.

The exact interaction pattern with the contract depends on how `backend/controller.py` and `backend/web3_api.py` are implemented.

---

## Development notes

- **Python:** recommended 3.9+ (tested with ≥3.10).
- **Node.js:** needed only if you want to work with the Solidity contracts in `backend/contracts/`.
- **Code organisation:**
  - Keep simulation logic in `backend/model.py` and orchestration in `backend/controller.py`.
  - Keep UI code in `frontend/app.py`.
- **Ideas for extensions:**
  - Add multiple stablecoins or additional pools.
  - Model other reserve assets explicitly (e.g. BTC, ETH).
  - Add agent‑based behaviour with explicit expectations.
  - Calibrate parameters against real market data.

---




