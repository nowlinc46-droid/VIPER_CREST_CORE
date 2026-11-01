// SPDX-License-Identifier: MIT
pragma solidity 0.8.24;

/// @notice Patched version of Lombard RateLimits library with window sanity check
library PatchedRateLimits {
    struct Data {
        uint256 amountInFlight;
        uint256 lastUpdated;
        uint256 limit;
        uint256 window;
    }

    struct Config {
        bytes32 chainId;
        uint256 limit;
        uint256 window;
    }

    error RateLimitExceeded();
    error MalformedRateLimit();

    function setRateLimit(Data storage rl, Config memory config) internal {
        // REMEDIATION: Validate that window is non-zero to prevent silent bypass
        if (config.window == 0) revert MalformedRateLimit();

        updateLimit(rl, 0);

        rl.limit = config.limit;
        rl.window = config.window;
    }

    function availableAmountToSend(
        Data memory rl
    )
        internal
        view
        returns (uint256 currentAmountInFlight, uint256 amountCanBeSent)
    {
        return
            availableAmountToSend(
                rl.amountInFlight,
                rl.lastUpdated,
                rl.limit,
                rl.window
            );
    }

    function availableAmountToSend(
        uint256 _amountInFlight,
        uint256 _lastUpdated,
        uint256 _limit,
        uint256 _window
    )
        internal
        view
        returns (uint256 currentAmountInFlight, uint256 amountCanBeSent)
    {
        uint256 timeSinceLastDeposit = block.timestamp - _lastUpdated;
        if (timeSinceLastDeposit >= _window) {
            currentAmountInFlight = 0;
            amountCanBeSent = _limit;
        } else {
            uint256 decay = (_limit * timeSinceLastDeposit) / _window;
            currentAmountInFlight = _amountInFlight <= decay
                ? 0
                : _amountInFlight - decay;
            amountCanBeSent = _limit <= currentAmountInFlight
                ? 0
                : _limit - currentAmountInFlight;
        }
    }

    function updateLimit(Data storage rl, uint256 _amount) internal {
        (
            uint256 currentAmountInFlight,
            uint256 amountCanBeSent
        ) = availableAmountToSend(rl);
        if (_amount > amountCanBeSent) revert RateLimitExceeded();

        rl.amountInFlight = currentAmountInFlight + _amount;
        rl.lastUpdated = block.timestamp;
    }
}
