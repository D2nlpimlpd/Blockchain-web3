# LUNA–UST Collapse Simulator

Interactive simulator of a Terra-style algorithmic stablecoin system, focusing on the May 2022 LUNA–UST “death spiral”.

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

```text  
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
