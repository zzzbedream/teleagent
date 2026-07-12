# TeleAgent — Contratos (Foundry)

`TeleAgentAccess.sol` es el motor de pagos del MVP: acepta depósitos nativos de AVAX
en Fuji y emite `CreditsPurchased(address user, uint256 amount)`, que el indexador
off-chain convierte en créditos de API.

## Requisitos

- [Foundry](https://book.getfoundry.sh/getting-started/installation)
- AVAX de testnet: [Fuji Faucet](https://core.app/tools/testnet-faucet/)

## Build y tests

```shell
forge build
forge test
```

## Deploy a Fuji

```shell
export PRIVATE_KEY=<tu_clave_privada_de_testnet>

forge script script/Deploy.s.sol:DeployScript \
  --rpc-url https://api.avax-test.network/ext/bc/C/rpc \
  --private-key $PRIVATE_KEY \
  --broadcast
```

Copia la dirección desplegada a la variable `CONTRACT_ADDRESS` del `.env` en la raíz
del repositorio y (opcional) verifícala en [Snowtrace testnet](https://testnet.snowtrace.io/).

## Probar un depósito

```shell
cast send $CONTRACT_ADDRESS "deposit()" \
  --value 0.1ether \
  --rpc-url https://api.avax-test.network/ext/bc/C/rpc \
  --private-key $PRIVATE_KEY
```

El indexador (`indexer/indexer.py`) detecta el evento y acredita el saldo a la
billetera vinculada vía `/link_wallet` en Discord.

## Retiro de fondos (solo owner)

```shell
cast send $CONTRACT_ADDRESS "withdraw()" \
  --rpc-url https://api.avax-test.network/ext/bc/C/rpc \
  --private-key $PRIVATE_KEY
```
