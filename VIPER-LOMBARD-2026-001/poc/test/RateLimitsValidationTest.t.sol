// SPDX-License-Identifier: MIT
pragma solidity 0.8.24;

import {RateLimits} from "../src/RateLimits.sol";
import {PatchedRateLimits} from "../src/PatchedRateLimits.sol";

/// @notice Minimal mock reflecting BridgeV2 storage, authorization, and withdrawal path
contract MockBridgeV2 {
    using RateLimits for RateLimits.Data;

    address public owner;
    mapping(bytes32 => RateLimits.Data) internal rateLimits;
    uint256 public totalMinted;

    event RateLimitsSet(address indexed token, bytes32 indexed chainId, uint256 limit, uint256 window);
    event WithdrawFromBridge(address recipient, bytes32 chainId, address token, uint256 amount);

    constructor(address _owner) {
        owner = _owner;
    }

    modifier onlyOwner() {
        require(msg.sender == owner, "Ownable: caller is not the owner");
        _;
    }

    function _calcRateLimitId(bytes32 chainId, address token) internal pure returns (bytes32) {
        return keccak256(abi.encodePacked(chainId, token));
    }

    /// @notice Exact BridgeV2.sol lines 249-258 logic
    function setTokenRateLimits(address token, RateLimits.Config memory config) external onlyOwner {
        RateLimits.setRateLimit(
            rateLimits[_calcRateLimitId(config.chainId, token)],
            config
        );
        emit RateLimitsSet(token, config.chainId, config.limit, config.window);
    }

    /// @notice Exact BridgeV2.sol lines 635-643 withdrawal execution path
    function handleInboundWithdraw(bytes32 chainId, address token, address recipient, uint256 amount) external {
        RateLimits.Data storage rl = rateLimits[_calcRateLimitId(chainId, token)];
        RateLimits.updateLimit(rl, amount);
        totalMinted += amount;
        emit WithdrawFromBridge(recipient, chainId, token, amount);
    }

    function getRateLimitState(bytes32 chainId, address token) external view returns (uint256 inFlight, uint256 canBeSent) {
        return RateLimits.availableAmountToSend(rateLimits[_calcRateLimitId(chainId, token)]);
    }
}

/// @notice Helper proxy to test caller authorization
contract CallerProxy {
    function callSetTokenRateLimits(MockBridgeV2 bridge, address token, RateLimits.Config memory config) external {
        bridge.setTokenRateLimits(token, config);
    }
}

contract RateLimitsValidationTest {
    using RateLimits for RateLimits.Data;
    using PatchedRateLimits for PatchedRateLimits.Data;

    RateLimits.Data internal rl;
    PatchedRateLimits.Data internal patchedRl;
    MockBridgeV2 internal bridge;
    CallerProxy internal nonOwnerCaller;

    address internal constant TOKEN = address(uint160(0xBBBB));
    bytes32 internal constant CHAIN_ID = bytes32(uint256(1));
    address internal constant RECIPIENT = address(0xCAFE);

    function setUp() public {
        RateLimits.Config memory cfg = RateLimits.Config({
            chainId: CHAIN_ID,
            limit: 1000 ether,
            window: 86400
        });
        rl.setRateLimit(cfg);
        bridge = new MockBridgeV2(address(this));
        nonOwnerCaller = new CallerProxy();
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

    // 4. Invariant V07: Failed transition strictly preserves state
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
            chainId: CHAIN_ID,
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
            chainId: CHAIN_ID,
            limit: 1000 ether,
            window: 0
        });
        rl.setRateLimit(config);
        rl.availableAmountToSend();
    }

    // 7. Library-Level Finding: Setting window = 0 silently bypasses the rate limit completely
    function test_ZeroWindow_SilentlyBypassesRateLimiting() public {
        RateLimits.Config memory config = RateLimits.Config({
            chainId: CHAIN_ID,
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

    // 8. Test 8: Bridge-level Reachability - Full call chain through BridgeV2
    function test_BridgeV2_Reachability_RateLimitBypass() public {
        // Owner configures BridgeV2 with window = 0
        bridge.setTokenRateLimits(TOKEN, RateLimits.Config({
            chainId: CHAIN_ID,
            limit: 1000 ether,
            window: 0
        }));

        // Execute multiple max-capacity withdrawals through BridgeV2 in the same block
        bridge.handleInboundWithdraw(CHAIN_ID, TOKEN, RECIPIENT, 1000 ether);
        bridge.handleInboundWithdraw(CHAIN_ID, TOKEN, RECIPIENT, 1000 ether);
        bridge.handleInboundWithdraw(CHAIN_ID, TOKEN, RECIPIENT, 1000 ether);

        // Total minted equals 3000 ether despite 1000 ether limit!
        require(bridge.totalMinted() == 3000 ether, "Bridge minted 3000 ether without reverting");

        (uint256 inFlight, uint256 canBeSent) = bridge.getRateLimitState(CHAIN_ID, TOKEN);
        require(inFlight == 0, "Bridge in-flight remained 0");
        require(canBeSent == 1000 ether, "Bridge available capacity remained 1000 ether");
    }

    // 9. Test 9: Nonzero-Window A/B Control Experiment
    function test_BridgeV2_ABControl_NonzeroWindowVsZeroWindow() public {
        // --- PHASE A: CONTROL (window > 0) ---
        bridge.setTokenRateLimits(TOKEN, RateLimits.Config({
            chainId: CHAIN_ID,
            limit: 1000 ether,
            window: 86400 // Legitimate nonzero window
        }));

        // Operation 1 succeeds (1000 ether sent)
        bridge.handleInboundWithdraw(CHAIN_ID, TOKEN, RECIPIENT, 1000 ether);
        require(bridge.totalMinted() == 1000 ether, "Phase A: First transfer succeeded");

        // Operation 2 in same window MUST REVERT with RateLimitExceeded
        try bridge.handleInboundWithdraw(CHAIN_ID, TOKEN, RECIPIENT, 1000 ether) {
            revert("Phase A Failed: Operation 2 should have reverted with RateLimitExceeded");
        } catch (bytes memory reason) {
            require(bytes4(reason) == RateLimits.RateLimitExceeded.selector, "Phase A: Expected RateLimitExceeded");
        }

        // --- PHASE B: NEGATIVE CONTROL (window == 0) ---
        bridge.setTokenRateLimits(TOKEN, RateLimits.Config({
            chainId: CHAIN_ID,
            limit: 1000 ether,
            window: 0 // Zero window
        }));

        uint256 baselineMinted = bridge.totalMinted(); // 1000 ether
        // In same block, execute three 1000 ether transfers
        bridge.handleInboundWithdraw(CHAIN_ID, TOKEN, RECIPIENT, 1000 ether); // PASS
        bridge.handleInboundWithdraw(CHAIN_ID, TOKEN, RECIPIENT, 1000 ether); // PASS
        bridge.handleInboundWithdraw(CHAIN_ID, TOKEN, RECIPIENT, 1000 ether); // PASS

        require(bridge.totalMinted() == baselineMinted + 3000 ether, "Phase B: All three 1000 ether transfers succeeded");
    }

    // 10. Test 10: Authorization Boundary - Non-owner cannot call setTokenRateLimits
    function test_BridgeV2_Authorization_NonOwnerReverted() public {
        try nonOwnerCaller.callSetTokenRateLimits(bridge, TOKEN, RateLimits.Config(CHAIN_ID, 1000 ether, 0)) {
            revert("Expected revert from non-owner");
        } catch Error(string memory reason) {
            require(keccak256(bytes(reason)) == keccak256(bytes("Ownable: caller is not the owner")), "Unexpected reason");
        }
    }

    // 11. Test 12: Fix Validation - Patched library reverts with MalformedRateLimit on window == 0
    function test_FixValidation_PatchedRateLimits_RejectsZeroWindow() public {
        PatchedRateLimits.Config memory badConfig = PatchedRateLimits.Config({
            chainId: CHAIN_ID,
            limit: 1000 ether,
            window: 0
        });

        try this.externalPatchedSetRateLimit(badConfig) {
            revert("Expected revert on window == 0");
        } catch (bytes memory reason) {
            bytes4 errorSelector = bytes4(reason);
            require(errorSelector == PatchedRateLimits.MalformedRateLimit.selector, "Expected MalformedRateLimit selector");
        }
    }

    // 12. Test 12 (Part B): Fix Validation - Patched library preserves normal nonzero window functionality
    function test_FixValidation_PatchedRateLimits_PreservesNormalOperation() public {
        PatchedRateLimits.Config memory goodConfig = PatchedRateLimits.Config({
            chainId: CHAIN_ID,
            limit: 1000 ether,
            window: 86400
        });
        patchedRl.setRateLimit(goodConfig);

        // Spend 400
        patchedRl.updateLimit(400 ether);
        (uint256 inFlight, uint256 canBeSent) = patchedRl.availableAmountToSend();
        require(inFlight == 400 ether, "Patched: inFlight must be 400 ether");
        require(canBeSent == 600 ether, "Patched: canBeSent must be 600 ether");

        // Try spend 700 (exceeds 600 remaining)
        try this.externalPatchedUpdateLimit(700 ether) {
            revert("Expected RateLimitExceeded");
        } catch (bytes memory reason) {
            require(bytes4(reason) == PatchedRateLimits.RateLimitExceeded.selector, "Expected RateLimitExceeded");
        }
    }

    // Helper functions for external calls
    function externalUpdateLimit(uint256 amount) external {
        rl.updateLimit(amount);
    }

    function externalPatchedSetRateLimit(PatchedRateLimits.Config memory config) external {
        patchedRl.setRateLimit(config);
    }

    function externalPatchedUpdateLimit(uint256 amount) external {
        patchedRl.updateLimit(amount);
    }
}
