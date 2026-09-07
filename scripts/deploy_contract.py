"""Compile VerificationRegistry.sol and deploy it to Polygon Amoy.

Prints the deployed contract address (paste into .env as CONTRACT_ADDRESS)
and writes the ABI to src/blockchain/contract_abi.json for the app to use.
"""
import json
import os
import sys

import solcx
import solcx.install
from web3 import Web3

# py-solc-x still points at the deprecated solc-bin.ethereum.org host, which
# no longer resolves. Point it at the current official host instead.
solcx.install.BINARY_DOWNLOAD_BASE = "https://binaries.soliditylang.org/{}-amd64/{}"

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from src.config import AMOY_CHAIN_ID, AMOY_RPC_URL, WALLET_ADDRESS, WALLET_PRIVATE_KEY

CONTRACT_PATH = os.path.join(os.path.dirname(__file__), "..", "contracts", "VerificationRegistry.sol")
ABI_OUTPUT_PATH = os.path.join(os.path.dirname(__file__), "..", "src", "blockchain", "contract_abi.json")
SOLC_VERSION = "0.8.24"


def compile_contract() -> tuple[list, str]:
    solcx.install_solc(SOLC_VERSION)
    with open(CONTRACT_PATH, "r", encoding="utf-8") as f:
        source = f.read()

    compiled = solcx.compile_source(
        source,
        output_values=["abi", "bin"],
        solc_version=SOLC_VERSION,
    )
    contract_id, contract_interface = next(iter(compiled.items()))
    return contract_interface["abi"], contract_interface["bin"]


def deploy(abi: list, bytecode: str) -> str:
    if not WALLET_PRIVATE_KEY or not WALLET_ADDRESS:
        raise SystemExit("WALLET_PRIVATE_KEY / WALLET_ADDRESS must be set in .env before deploying")

    w3 = Web3(Web3.HTTPProvider(AMOY_RPC_URL))
    if not w3.is_connected():
        raise SystemExit(f"Could not connect to Amoy RPC at {AMOY_RPC_URL}")

    account = w3.eth.account.from_key(WALLET_PRIVATE_KEY)
    print(f"Deploying from {account.address} (balance: {w3.from_wei(w3.eth.get_balance(account.address), 'ether')} POL)")

    Contract = w3.eth.contract(abi=abi, bytecode=bytecode)
    nonce = w3.eth.get_transaction_count(account.address)

    tx = Contract.constructor().build_transaction({
        "chainId": AMOY_CHAIN_ID,
        "from": account.address,
        "nonce": nonce,
        "gasPrice": w3.eth.gas_price,
    })

    signed = w3.eth.account.sign_transaction(tx, private_key=WALLET_PRIVATE_KEY)
    tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
    print(f"Deployment tx sent: {tx_hash.hex()}")

    receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=180)
    print(f"Deployed at: {receipt.contractAddress}")
    print(f"View on explorer: https://amoy.polygonscan.com/address/{receipt.contractAddress}")

    return receipt.contractAddress


def main():
    print("Compiling VerificationRegistry.sol...")
    abi, bytecode = compile_contract()

    os.makedirs(os.path.dirname(ABI_OUTPUT_PATH), exist_ok=True)
    with open(ABI_OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(abi, f, indent=2)
    print(f"ABI written to {ABI_OUTPUT_PATH}")

    address = deploy(abi, bytecode)

    print("\n" + "=" * 60)
    print(f"Add this to your .env: CONTRACT_ADDRESS={address}")
    print("=" * 60)


if __name__ == "__main__":
    main()
