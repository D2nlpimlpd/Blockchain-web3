# backend/model.py
import math
import random

def compute_new_state(state, step=1):
    """
    模拟 UST/LUNA 链上稳定币系统的演化：
    从稳定锚定 → 轻微波动 → 恶化脱锚 → 崩溃归零
    """

    ust_price = state["ust_price"]
    luna_price = state["luna_price"]
    ust_supply = state["ust_supply"]
    luna_supply = state["luna_supply"]

    # === 第一阶段：稳定锚定（0 ~ 10步） ===
    if step < 10:
        noise = random.uniform(-0.002, 0.002)
        ust_price = max(0.98, min(1.02, ust_price + noise))
        luna_price *= 1 + random.uniform(-0.01, 0.01)

    # === 第二阶段：轻微脱锚（10 ~ 20步） ===
    elif step < 20:
        deviation = (ust_price - 1.0)
        ust_price *= (1 - 0.005 - random.uniform(0.0, 0.002))
        luna_price *= (1 - 0.01 - deviation * 5)
        ust_supply *= 1.01  # 市场信心下降，UST 抛盘增加
        luna_supply *= 1.02  # 铸造更多LUNA来支撑

    # === 第三阶段：锚定失效，恐慌蔓延（20 ~ 40步） ===
    elif step < 40:
        # 模拟死亡螺旋：UST下跌 + LUNA超发 + 市场信心崩塌
        ust_price *= 0.95 - random.uniform(0.0, 0.03)
        ust_supply *= 1.05
        luna_supply *= 1.2  # 铸造剧增（LUNA 通胀失控）
        luna_price *= 0.85 - random.uniform(0.0, 0.05)

    # === 第四阶段：彻底崩溃（40步后） ===
    else:
        ust_price *= 0.5  # 崩盘后UST几乎归零
        luna_price *= 0.2
        ust_supply *= 1.1
        luna_supply *= 2.0

    # 限制 UST最低值（避免NaN）
    ust_price = max(ust_price, 0.0001)
    luna_price = max(luna_price, 0.000001)

    # === 计算价格联动 ===
    ust_to_luna_ratio = ust_supply / (luna_supply + 1e-9)
    # 简单动态平衡机制：UST脱锚程度反映到LUNA价格
    adjust_factor = math.exp(-abs(1 - ust_price) * 5)
    luna_price *= adjust_factor

    # 更新状态
    return {
        "ust_price": ust_price,
        "luna_price": luna_price,
        "ust_supply": ust_supply,
        "luna_supply": luna_supply,
        "peg_ust": state["peg_ust"],
        "peg_luna": state["peg_luna"],
    }