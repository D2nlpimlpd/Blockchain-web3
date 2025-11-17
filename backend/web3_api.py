from web3 import Web3
import os
from dotenv import load_dotenv
load_dotenv()
import random

INFURA_URL = f"https://sepolia.infura.io/v3/{os.getenv('INFURA_KEY')}"
w3 = Web3(Web3.HTTPProvider(INFURA_URL))

LUNA_ADDR = os.getenv("LUNA_ADDR")
STABLE_ADDR = os.getenv("STABLE_ADDR")
ACCOUNT_ADDRESS = os.getenv("ACCOUNT_ADDRESS")
PRIVATE_KEY = os.getenv("PRIVATE_KEY")
ACCOUNT_ADDRESS = w3.to_checksum_address(os.getenv("ACCOUNT_ADDRESS"))

def send_txn(fn, contract, *args):
    nonce = w3.eth.get_transaction_count(ACCOUNT_ADDRESS)
    # 基于当前链上gas price，自动＋随机微调避免重复
    base_gas_price = w3.eth.gas_price
    gas_price = int(base_gas_price * (1 + random.uniform(0.05, 0.15)))

    txn = fn(*args).build_transaction({
        "from": ACCOUNT_ADDRESS,
        "nonce": nonce,
        "gas": 200000,
        "gasPrice": gas_price,
    })

    signed_txn = w3.eth.account.sign_transaction(txn, private_key=os.getenv("PRIVATE_KEY"))
    tx_hash = w3.eth.send_raw_transaction(signed_txn.raw_transaction)
    return tx_hash.hex()