// SPDX-License-Identifier: MIT
pragma solidity ^0.4.24;

/**
 * @title BeautyChain (BEC 2018 Vulnerability Archetype)
 * @notice Reproduction of the integer overflow in batchOverflow (batchTransfer).
 * uint256 amount = uint256(cnt) * _value silently wrapped around to zero.
 */
contract BeautyChainToken {
    mapping(address => uint256) public balances;
    string public name = "BeautyChain";
    string public symbol = "BEC";

    function deposit() public payable {
        balances[msg.sender] += msg.value;
    }

    // Historical flaw: multiplication without SafeMath causes arithmetic wrap-around
    function batchTransfer(address[] _receivers, uint256 _value) public returns (bool) {
        uint256 cnt = _receivers.length;
        // Overflow vulnerability: cnt * _value wraps around if product >= 2^256
        uint256 amount = uint256(cnt) * _value;

        // Bypasses balance check when amount overflows to 0
        require(cnt > 0 && cnt <= 20);
        require(_value > 0 && balances[msg.sender] >= amount);

        balances[msg.sender] -= amount;
        for (uint i = 0; i < cnt; i++) {
            balances[_receivers[i]] += _value;
        }
        return true;
    }
}
