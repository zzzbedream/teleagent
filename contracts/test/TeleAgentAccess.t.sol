// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import {Test, console} from "forge-std/Test.sol";
import {TeleAgentAccess} from "../src/TeleAgentAccess.sol";
import {Ownable} from "@openzeppelin/contracts/access/Ownable.sol";

contract TeleAgentAccessTest is Test {
    TeleAgentAccess public teleAgent;
    address public owner;
    address public user;

    event CreditsPurchased(address indexed user, uint256 amount);

    function setUp() public {
        owner = makeAddr("owner");
        user = makeAddr("user");

        vm.prank(owner);
        teleAgent = new TeleAgentAccess();

        vm.deal(user, 100 ether);
    }

    function test_DepositAvax() public {
        uint256 depositAmount = 1 ether;
        
        vm.startPrank(user);
        
        vm.expectEmit(true, false, false, true, address(teleAgent));
        emit CreditsPurchased(user, depositAmount);
        
        teleAgent.deposit{value: depositAmount}();
        
        vm.stopPrank();

        assertEq(address(teleAgent).balance, depositAmount);
    }

    function test_RevertIf_DepositZero() public {
        vm.prank(user);
        vm.expectRevert("Deposit amount must be greater than zero");
        teleAgent.deposit{value: 0}();
    }

    function test_WithdrawAvax() public {
        uint256 depositAmount = 10 ether;
        vm.prank(user);
        teleAgent.deposit{value: depositAmount}();

        assertEq(address(teleAgent).balance, depositAmount);
        
        uint256 ownerInitialBalance = owner.balance;

        vm.prank(owner);
        teleAgent.withdraw();

        assertEq(address(teleAgent).balance, 0);
        assertEq(owner.balance, ownerInitialBalance + depositAmount);
    }

    function test_RevertIf_NotOwnerWithdraw() public {
        uint256 depositAmount = 10 ether;
        vm.prank(user);
        teleAgent.deposit{value: depositAmount}();

        vm.prank(user);
        
        vm.expectRevert(abi.encodeWithSelector(Ownable.OwnableUnauthorizedAccount.selector, user));
        teleAgent.withdraw();
    }
}
