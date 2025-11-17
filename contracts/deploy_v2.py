from web3 import Web3
import os, json
from solcx import compile_files
from dotenv import load_dotenv

# 加载环境变量
load_dotenv(".env")  # 如果 .env 在项目根目录，请注意路径

INFURA_URL = f"https://sepolia.infura.io/v3/{os.getenv('INFURA_KEY')}"
PRIVATE_KEY = os.getenv("PRIVATE_KEY")
ACCOUNT_ADDRESS = os.getenv("ACCOUNT_ADDRESS")
LUNA_ADDR = os.getenv("LUNA_ADDR")

w3 = Web3(Web3.HTTPProvider(INFURA_URL))
print("✅ 连接 Infura:", w3.is_connected())
# 转换为 checksum 地址
LUNA_ADDR = w3.to_checksum_address(LUNA_ADDR)
ACCOUNT_ADDRESS = w3.to_checksum_address(ACCOUNT_ADDRESS)
# 读取编译结果
compiled = compile_files(
    ["AlgoStableV2.sol"],
    output_values=["abi", "bin"],
    solc_version="0.8.20",
    import_remappings=["@openzeppelin=node_modules/@openzeppelin"]
)
contract_id, contract_interface = list(compiled.items())[0]

abi = contract_interface['abi']
bytecode = contract_interface['bin']

# 创建合约工厂
AlgoStableV2 = w3.eth.contract(abi=abi, bytecode=bytecode)

# 构造交易
construct_txn = AlgoStableV2.constructor(LUNA_ADDR).build_transaction({
    'from': ACCOUNT_ADDRESS,
    'nonce': w3.eth.get_transaction_count(ACCOUNT_ADDRESS),
    'gas': 3000000,
    'gasPrice': w3.to_wei('5', 'gwei')
})

signed = w3.eth.account.sign_transaction(construct_txn, private_key=PRIVATE_KEY)
tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
print("⏳ 正在部署，TxHash:", tx_hash.hex())

receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
address = receipt.contractAddress
print("🚀 部署成功！AlgoStableV2 地址:", address)

# 保存 ABI 文件以供前端使用
os.makedirs("../backend", exist_ok=True)
with open("../backend/AlgoStableV2_abi.json", "w") as f:
    json.dump(abi, f)
print("✅ ABI 已保存为 ../backend/AlgoStableV2_abi.json")

# === 自动初始化 mint 1,000,000 UST 给自己地址 ===
# 读取 ABI
AlgoStableV2 = w3.eth.contract(address=address, abi=abi)

# 1_000_000 UST = 1e6 * 10^18
ust_amount = 1_000_000 * (10 ** 18)

# 构造交易
mint_txn = AlgoStableV2.functions.mint(ACCOUNT_ADDRESS, ust_amount).build_transaction({
    'from': ACCOUNT_ADDRESS,
    'nonce': w3.eth.get_transaction_count(ACCOUNT_ADDRESS),
    'gas': 300000,
    'gasPrice': w3.to_wei('5', 'gwei'),
})

# 私钥签名并广播
signed_txn = w3.eth.account.sign_transaction(mint_txn, private_key=PRIVATE_KEY)
tx_hash = w3.eth.send_raw_transaction(signed_txn.raw_transaction)
print("⏳ 正在执行初始 mint 交易:", tx_hash.hex())

receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
print("✅ 初始化完成。已为地址", ACCOUNT_ADDRESS, "铸造 1,000,000 UST！")
print("区块号:", receipt.blockNumber)

# === 自动初始化 mint 1,000,000 UST 给自己地址 ===
# 读取 ABI
AlgoStableV2 = w3.eth.contract(address=address, abi=abi)

# 1_000_000 UST = 1e6 * 10^18
ust_amount = 1_000_000 * (10 ** 18)

# 构造交易
mint_txn = AlgoStableV2.functions.mint(ACCOUNT_ADDRESS, ust_amount).build_transaction({
    'from': ACCOUNT_ADDRESS,
    'nonce': w3.eth.get_transaction_count(ACCOUNT_ADDRESS),
    'gas': 300000,
    'gasPrice': w3.to_wei('5', 'gwei'),
})

# 私钥签名并广播
signed_txn = w3.eth.account.sign_transaction(mint_txn, private_key=PRIVATE_KEY)
tx_hash = w3.eth.send_raw_transaction(signed_txn.raw_transaction)
print("⏳ 正在执行初始 mint 交易:", tx_hash.hex())

receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
print("✅ 初始化完成。已为地址", ACCOUNT_ADDRESS, "铸造 1,000,000 UST！")
print("区块号:", receipt.blockNumber)