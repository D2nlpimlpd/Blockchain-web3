from web3 import Web3
import os, json
from dotenv import load_dotenv

load_dotenv(".env")

INFURA_URL = f"https://sepolia.infura.io/v3/{os.getenv('INFURA_KEY')}"
w3 = Web3(Web3.HTTPProvider(INFURA_URL))

ACCOUNT_ADDRESS = w3.to_checksum_address(os.getenv("ACCOUNT_ADDRESS"))
STABLE_ADDR = w3.to_checksum_address(os.getenv("STABLE_ADDR"))

# 读取 ABI
with open("../backend/AlgoStableV2_abi.json") as f:
    abi = json.load(f)

contract = w3.eth.contract(address=STABLE_ADDR, abi=abi)

owner = contract.functions.owner().call()
price = contract.functions.price().call()
balance = contract.functions.balanceOf(ACCOUNT_ADDRESS).call()

print("📊 合约状态：")
print("  合约地址：", STABLE_ADDR)
print("  合约所有者：", owner)
print("  当前价格(USD * 1e18)：", price)
print("  当前账户UST余额：", balance / 1e18)