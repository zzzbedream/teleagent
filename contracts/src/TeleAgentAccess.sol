// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import {Ownable} from "@openzeppelin/contracts/access/Ownable.sol";
import {ReentrancyGuard} from "@openzeppelin/contracts/utils/ReentrancyGuard.sol";

/**
 * @title TeleAgentAccess
 * @dev MVP Contract for accepting AVAX payments to grant API credits.
 * Gatekeeper for the TeleAgent system.
 */
contract TeleAgentAccess is Ownable, ReentrancyGuard {
    
    event CreditsPurchased(address indexed user, uint256 amount);

    constructor() Ownable(msg.sender) {}

    /**
     * @dev Accepts native AVAX to credit the user's account off-chain.
     */
    function deposit() external payable nonReentrant {
        require(msg.value > 0, "Deposit amount must be greater than zero");
        
        emit CreditsPurchased(msg.sender, msg.value);
    }

    /**
     * @dev Allows the owner to withdraw collected funds.
     */
    function withdraw() external onlyOwner nonReentrant {
        uint256 balance = address(this).balance;
        require(balance > 0, "No funds to withdraw");
        
        (bool success, ) = payable(owner()).call{value: balance}("");
        require(success, "Withdraw failed");
    }
}
