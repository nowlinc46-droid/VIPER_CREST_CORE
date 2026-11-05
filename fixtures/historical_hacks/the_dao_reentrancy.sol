// SPDX-License-Identifier: MIT
pragma solidity ^0.4.24;

/**
 * @title The DAO (2016 Vulnerability Archetype)
 * @notice Historical reproduction of The DAO reentrancy vulnerability.
 * In withdraw(), funds are transferred before internal balance is deducted.
 */
contract TheDAO {
    mapping(address => uint256) public balances;
    uint256 public totalSupply;

    function deposit() public payable {
        balances[msg.sender] += msg.value;
        totalSupply += msg.value;
    }

    // Historical flaw: State mutation occurs AFTER external ether transfer
    function withdraw(uint256 amount) public {
        require(balances[msg.sender] >= amount, "Insufficient balance");

        // External call to msg.sender triggers fallback() in caller contract
        bool success = msg.sender.call.value(amount)();
        require(success, "Transfer failed");

        // State update happens too late (check-effects-interactions violation)
        balances[msg.sender] -= amount;
        totalSupply -= amount;
    }

    function getBalance(address account) public view returns (uint256) {
        return balances[account];
    }
}
