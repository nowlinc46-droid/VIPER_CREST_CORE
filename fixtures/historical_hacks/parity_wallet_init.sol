// SPDX-License-Identifier: MIT
pragma solidity ^0.4.24;

/**
 * @title Parity Multi-Sig Wallet (2017 Vulnerability Archetype)
 * @notice Reproduction of the Parity multi-sig library takeover flaw.
 * initWallet() is marked public and lacks an initialization guard, allowing
 * any caller to re-initialize ownership and execute kill() via selfdestruct.
 */
contract ParityWalletLibrary {
    address[] public owners;
    uint256 public required;
    bool public isInitialized;

    // Historical flaw: initWallet is unprotected and can be called on uninitialized library
    function initWallet(address[] _owners, uint256 _required) public {
        // Missing initializer modifier or guard on library contract
        owners = _owners;
        required = _required;
        isInitialized = true;
    }

    // Unprotected termination allows anyone who initialized library to destroy it
    function kill(address to) public {
        require(isOwner(msg.sender), "Not authorized");
        selfdestruct(to);
    }

    function isOwner(address _addr) public view returns (bool) {
        for (uint i = 0; i < owners.length; i++) {
            if (owners[i] == _addr) return true;
        }
        return false;
    }
}
