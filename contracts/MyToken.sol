// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/token/ERC20/ERC20.sol";

contract MyToken is ERC20 {
    address public controller;
    constructor() ERC20("MyToken", "MTK") {
        controller = msg.sender;
        _mint(msg.sender, 1000 ether);
    }

    function mint(address to, uint256 amount) external {
        require(msg.sender == controller, "only controller");
        _mint(to, amount);
    }

    function burn(address from, uint256 amount) external {
        require(msg.sender == controller, "only controller");
        _burn(from, amount);
    }
}