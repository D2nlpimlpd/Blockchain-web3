from solcx import compile_files, install_solc
import json

# 1. 安装编译器
install_solc("0.8.20")

# 2. 编译文件
compiled = compile_files(
    ["AlgoStableV2.sol"],
    output_values=["abi", "bin"],
    solc_version="0.8.20",
    import_remappings=["@openzeppelin=node_modules/@openzeppelin"]
)

# 3. 找到合约数据 (文件名:合约名)
contract_id, contract_interface = list(compiled.items())[0]

# 4. 导出 ABI 文件
with open("../backend/AlgoStableV2_abi.json", "w") as f:
    json.dump(contract_interface["abi"], f)

print("✅ 编译成功！ABI 已导出到 ../backend/AlgoStableV2_abi.json")

# 5. 打印合约详情
print("Contract key:", contract_id)
print("Bytecode size:", len(contract_interface["bin"]))