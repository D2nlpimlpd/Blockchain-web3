from web3 import Web3
from solcx import compile_files, install_solc
import os
from dotenv import load_dotenv

print("✅ compile start")
load_dotenv()
install_solc("0.8.20")

INFURA_URL = f"https://sepolia.infura.io/v3/{os.getenv('INFURA_KEY')}"
PRIVATE_KEY = os.getenv("PRIVATE_KEY")
ACCOUNT_ADDRESS = os.getenv("ACCOUNT_ADDRESS")

w3 = Web3(Web3.HTTPProvider(INFURA_URL))

compiled = compile_files(
    ["MyToken.sol", "AlgoStable.sol"],
    solc_version="0.8.20",
    import_remappings=["@openzeppelin=node_modules/@openzeppelin"]
)

MyToken = compiled["MyToken.sol:MyToken"]
AlgoStable = compiled["AlgoStable.sol:AlgoStable"]

acct = w3.eth.account.from_key(PRIVATE_KEY)

# 部署 MyToken
token_contract = w3.eth.contract(abi=MyToken["abi"], bytecode=MyToken["bin"])
tx1 = token_contract.constructor().build_transaction({
    "from": acct.address,
    "gas": 2000000,
    "nonce": w3.eth.get_transaction_count(acct.address)
})
signed1 = acct.sign_transaction(tx1)
tx_hash1 = w3.eth.send_raw_transaction(signed1.raw_transaction)
token_address = w3.eth.wait_for_transaction_receipt(tx_hash1).contractAddress
print("MyToken deployed at", token_address)

# 部署 AlgoStable
algo_contract = w3.eth.contract(abi=AlgoStable["abi"], bytecode=AlgoStable["bin"])
tx2 = algo_contract.constructor(token_address).build_transaction({
    "from": acct.address,
    "gas": 2500000,
    "nonce": w3.eth.get_transaction_count(acct.address)
})
signed2 = acct.sign_transaction(tx2)
tx_hash2 = w3.eth.send_raw_transaction(signed2.raw_transaction)
algo_address = w3.eth.wait_for_transaction_receipt(tx_hash2).contractAddress
print("AlgoStable deployed at", algo_address)

print("✅ deploy complete")