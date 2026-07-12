// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import {Script} from "forge-std/Script.sol";
import {TeleAgentAccess} from "../src/TeleAgentAccess.sol";

contract DeployScript is Script {
    function run() public returns (TeleAgentAccess deployed) {
        vm.startBroadcast();

        deployed = new TeleAgentAccess();

        vm.stopBroadcast();
    }
}
