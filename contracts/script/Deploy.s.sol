// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import {Script} from "forge-std/Script.sol";
import {TeleAgentAccess} from "../src/TeleAgentAccess.sol";

contract DeployScript is Script {
    function run() public returns (TeleAgentAccess deployed) {
        // Lee la clave privada del deployer desde contracts/.env (Foundry lo carga solo).
        // Acepta formato 0x... (64 caracteres hex).
        uint256 deployerPrivateKey = vm.envUint("DEPLOYER_PRIVATE_KEY");
        vm.startBroadcast(deployerPrivateKey);

        deployed = new TeleAgentAccess();

        vm.stopBroadcast();
    }
}
