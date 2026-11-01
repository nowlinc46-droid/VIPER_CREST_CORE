// SPDX-License-Identifier: MIT
pragma solidity 0.8.24;

import {RateLimits} from "../src/RateLimits.sol";

contract RateLimitsValidationTest {
    using RateLimits for RateLimits.Data;

    RateLimits.Data internal rl;

    function setUp() public {
        RateLimits.Config memory cfg = RateLimits.Config({
            chainId: bytes32(uint256(1)),
            limit: 1000 ether,
            window: 86400
        });
        rl.setRateLimit(cfg);
    }

    // 1. Backward Hydration Proof (T4:S2): Predecessor baseline derived as 0 in-flight
    function test_BackwardHydration_PredecessorBaselineDerived() public view {
        (uint256 inFlight, uint256 canBeSent) = rl.availableAmountToSend();
        require(inFlight == 0, "Predecessor baseline invariant: inFlight must be 0");
        require(canBeSent == 1000 ether, "Predecessor baseline invariant: full capacity must be available");
    }

    // 2. Present State Proof (T5:S5): Nominal transfer of 400 ether succeeds
    function test_PresentState_NominalTransfer_Succeeds() public {
        rl.updateLimit(400 ether);
        (uint256 inFlight, uint256 canBeSent) = rl.availableAmountToSend();
        require(inFlight == 400 ether, "Observed state: inFlight must record exactly 400 ether");
        require(canBeSent == 600 ether, "Observed state: remaining must record 600 ether");
    }

    // 3. Forward Candidate Proof (T6:S6): Predictive containment triggers RateLimitExceeded
    function test_ForwardCandidate_PredictiveContainment_RateLimitExceeded() public {
        rl.updateLimit(900 ether);
        try this.externalUpdateLimit(200 ether) {
            revert("FAIL: Expected RateLimitExceeded() but call succeeded");
        } catch (bytes memory lowLevelData) {
            bytes4 errorSelector = bytes4(lowLevelData);
            require(errorSelector == RateLimits.RateLimitExceeded.selector, "FAIL: Unexpected error selector");
        }
    }

    // 4. Negative Control & Invariant V07: Failed transition strictly preserves state
    function test_ForwardCandidate_RevertPreservesState() public {
        rl.updateLimit(900 ether);
        (uint256 beforeInFlight, uint256 beforeAvailable) = rl.availableAmountToSend();
        try this.externalUpdateLimit(200 ether) {
            revert("Expected RateLimitExceeded");
        } catch (bytes memory reason) {
            require(
                bytes4(reason) == RateLimits.RateLimitExceeded.selector,
                "Unexpected error"
            );
        }
        (uint256 afterInFlight, uint256 afterAvailable) = rl.availableAmountToSend();
        require(afterInFlight == beforeInFlight, "In-flight state changed");
        require(afterAvailable == beforeAvailable, "Capacity state changed");
    }

    // 5. Negative Control: Zero-limit configuration accepted, capacity clamped to zero
    function test_ZeroLimitConfiguration_AcceptedOrRejected() public {
        RateLimits.Config memory config = RateLimits.Config({
            chainId: bytes32(uint256(1)),
            limit: 0,
            window: 86400
        });
        rl.setRateLimit(config);
        (, uint256 canBeSent) = rl.availableAmountToSend();
        require(canBeSent == 0, "Expected zero available capacity");
    }

    // 6. Negative Control: Zero-window configuration runtime consequence
    function test_ZeroWindowConfiguration_AcceptedOrRejected() public {
        RateLimits.Config memory config = RateLimits.Config({
            chainId: bytes32(uint256(1)),
            limit: 1000 ether,
            window: 0
        });
        rl.setRateLimit(config);
        // Exercise the exact runtime path whose behavior is under evaluation.
        rl.availableAmountToSend();
    }

    // 7. Critical Finding: Setting window = 0 silently bypasses the rate limit completely
    function test_ZeroWindow_SilentlyBypassesRateLimiting() public {
        RateLimits.Config memory config = RateLimits.Config({
            chainId: bytes32(uint256(1)),
            limit: 1000 ether,
            window: 0
        });
        rl.setRateLimit(config);

        // Send 1000 ether three times in the same block without reverting
        rl.updateLimit(1000 ether);
        rl.updateLimit(1000 ether);
        rl.updateLimit(1000 ether);

        (uint256 inFlight, uint256 canBeSent) = rl.availableAmountToSend();
        require(inFlight == 0, "Silent bypass: inFlight is reset to 0 on every check");
        require(canBeSent == 1000 ether, "Silent bypass: full limit perpetually available");
    }

    function externalUpdateLimit(uint256 amount) external {
        rl.updateLimit(amount);
    }
}
