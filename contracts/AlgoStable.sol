// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/token/ERC20/ERC20.sol";

contract AlgoStableV2 is ERC20 {
    address public owner;
    uint256 public price; // 模拟稳定币当前价格（USD * 1e18）
    ERC20 public lunaToken;

    event PriceUpdated(uint256 newPrice);
    event Minted(address indexed user, uint256 ustAmount);
    event Redeemed(address indexed user, uint256 ustAmount, uint256 lunaMinted);

    constructor(address lunaAddr) ERC20("AlgoStable", "UST") {
        owner = msg.sender;
        lunaToken = ERC20(lunaAddr);
        price = 1e18; // 1 USD 初始
    }

    modifier onlyOwner() {
        require(msg.sender == owner, "only owner");
        _;
    }

    // 后端更新价格（模拟外部市场变化）
    function setPrice(uint256 newPrice) external onlyOwner {
        price = newPrice;
        emit PriceUpdated(newPrice);
    }

    // 模拟 mint：用户存 LUNA，换 UST
    function mint(address to, uint256 ustAmount) external onlyOwner {
        _mint(to, ustAmount);
        emit Minted(to, ustAmount);
    }

    // 模拟 redeem：销毁 UST，生成新的 LUNA
    function redeem(address from, uint256 ustAmount, uint256 lunaToMint) external onlyOwner {
        _burn(from, ustAmount);
        emit Redeemed(from, ustAmount, lunaToMint);
    }
}