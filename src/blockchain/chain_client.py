"""web3.py wrapper around the deployed VerificationRegistry contract."""
import json
import os
from dataclasses import dataclass

from web3 import Web3

from src.config import AMOY_CHAIN_ID, AMOY_RPC_URL, CONTRACT_ADDRESS, POLYGONSCAN_TX_URL, WALLET_PRIVATE_KEY

ABI_PATH = os.path.join(os.path.dirname(__file__), "contract_abi.json")


class ChainClientError(Exception):
    """Raised when a blockchain operation could not be completed."""


@dataclass
class OnChainRecord:
    record_id: int
    data_hash: bytes
    ipfs_cid: str
    submitter: str
    timestamp: int


@dataclass
class SubmittedRecord:
    record_id: int
    tx_hash: str
    explorer_url: str


def _load_abi() -> list:
    if not os.path.exists(ABI_PATH):
        raise ChainClientError(
            f"{ABI_PATH} not found. Run scripts/deploy_contract.py first."
        )
    with open(ABI_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


class ChainClient:
    def __init__(self):
        if not CONTRACT_ADDRESS:
            raise ChainClientError("CONTRACT_ADDRESS is not set in .env")
        if not WALLET_PRIVATE_KEY:
            raise ChainClientError("WALLET_PRIVATE_KEY is not set in .env")

        self.w3 = Web3(Web3.HTTPProvider(AMOY_RPC_URL))
        if not self.w3.is_connected():
            raise ChainClientError(f"Could not connect to Amoy RPC at {AMOY_RPC_URL}")

        self.account = self.w3.eth.account.from_key(WALLET_PRIVATE_KEY)
        self.contract = self.w3.eth.contract(
            address=Web3.to_checksum_address(CONTRACT_ADDRESS),
            abi=_load_abi(),
        )

    def register_record(self, data_hash: bytes, ipfs_cid: str) -> SubmittedRecord:
        """Submit a new evidence record on-chain. Returns once mined."""
        nonce = self.w3.eth.get_transaction_count(self.account.address)
        tx = self.contract.functions.registerRecord(data_hash, ipfs_cid).build_transaction({
            "chainId": AMOY_CHAIN_ID,
            "from": self.account.address,
            "nonce": nonce,
            "gasPrice": self.w3.eth.gas_price,
        })
        signed = self.w3.eth.account.sign_transaction(tx, private_key=WALLET_PRIVATE_KEY)
        tx_hash = self.w3.eth.send_raw_transaction(signed.raw_transaction)
        receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=180)

        record_id = self.contract.events.RecordRegistered().process_receipt(receipt)[0]["args"]["recordId"]

        return SubmittedRecord(
            record_id=record_id,
            tx_hash=tx_hash.hex(),
            explorer_url=POLYGONSCAN_TX_URL.format(tx_hash=tx_hash.hex()),
        )

    def get_record(self, record_id: int) -> OnChainRecord:
        data_hash, ipfs_cid, submitter, timestamp = self.contract.functions.getRecord(record_id).call()
        return OnChainRecord(
            record_id=record_id,
            data_hash=data_hash,
            ipfs_cid=ipfs_cid,
            submitter=submitter,
            timestamp=timestamp,
        )

    def verify_hash(self, record_id: int, data_hash: bytes) -> bool:
        """Re-verification: does the given hash match what's on-chain for this record?"""
        return self.contract.functions.verifyHash(record_id, data_hash).call()
