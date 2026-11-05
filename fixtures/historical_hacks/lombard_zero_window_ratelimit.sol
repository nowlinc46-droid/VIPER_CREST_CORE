// SPDX-License-Identifier: MIT
pragma solidity 0.8.24;

/**
 * @title Lombard RateLimits (2024 Invariant Archetype)
 * @notice Reproduction of the zero-window rate limit bypass.
 * When window == 0, timeSinceLastDeposit >= window is always true,
 * resetting currentAmountInFlight to 0 and bypassing cumulative throttling.
 */
contract RateLimitsRepro {
    struct Data {
        uint256 limit;
        uint256 window;
        uint256 currentAmountInFlight;
        uint256 lastUpdated;
    }

    Data public rateLimit;

    function setRateLimit(uint256 limit_, uint256 window_) external {
        // Invariant flaw: missing check that window_ > 0
        rateLimit.limit = limit_;
        rateLimit.window = window_;
        rateLimit.lastUpdated = block.timestamp;
    }

    function availableAmountToSend() public view returns (uint256 amountCanBeSent) {
        uint256 timeSinceLastDeposit = block.timestamp - rateLimit.lastUpdated;
        // If window is 0, timeSinceLastDeposit >= 0 is always true
        if (timeSinceLastDeposit >= rateLimit.window) {
            amountCanBeSent = rateLimit.limit;
        } else {
            uint256 decay = (rateLimit.limit * timeSinceLastDeposit) / rateLimit.window;
            amountCanBeSent = rateLimit.currentAmountInFlight > decay ? decay : rateLimit.limit;
        }
    }
}
