// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

/**
 * @title Nomad Bridge Replica (2022 Vulnerability Archetype)
 * @notice Reproduction of the Nomad cross-chain bridge zero-root validation bug.
 * During contract upgrade/initialization, confirmAt[0x00...00] was set to 1.
 * As unproven messages default to root 0x00...00, any fraudulent transaction was accepted.
 */
contract NomadReplica {
    mapping(bytes32 => uint256) public confirmAt;
    mapping(bytes32 => bool) public executedMessages;

    address public owner;

    event MessageProcessed(bytes32 indexed messageHash, bool success);

    constructor() {
        owner = msg.sender;
        // Historical flaw: root 0x0 was inadvertently confirmed in deployment scripts
        confirmAt[bytes32(0)] = 1;
    }

    function process(bytes memory message) external returns (bool) {
        bytes32 messageHash = keccak256(message);
        require(!executedMessages[messageHash], "Already executed");

        // If an unproven message evaluates to root 0x0, it passes because confirmAt[0x0] == 1
        bytes32 root = bytes32(0);
        require(confirmAt[root] > 0 && confirmAt[root] <= block.timestamp, "Root not confirmed");

        executedMessages[messageHash] = true;
        emit MessageProcessed(messageHash, true);
        return true;
    }
}
