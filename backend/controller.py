from backend.model import compute_new_state
from backend.web3_api import w3, send_txn

def simulate_step(state, stable_contract, step=1, use_onchain=False):
    """执行一步模拟"""
    new_state = compute_new_state(state, step=step)
    price_onchain = int(new_state["ust_price"] * 1e18)

    if use_onchain:
        tx_hash = send_txn(stable_contract.functions.setPrice, stable_contract, price_onchain)
        print(f"✅ [链上模式] setPrice 交易已发出: {tx_hash}")
        receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
        print(f"⛓️ 区块确认完成 — Block {receipt.blockNumber}")
    else:
        print(f"🧮 [本地] step={step}, price={price_onchain / 1e18:.4f} USD")

    return new_state