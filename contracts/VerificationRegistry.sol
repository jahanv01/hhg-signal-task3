// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

/// @title VerificationRegistry
/// @notice Stores a tamper-evident fingerprint of an off-chain evidence
/// bundle (face match + matched social post + similarity score). The full
/// bundle lives on IPFS; only its SHA-256 hash and IPFS CID are stored here,
/// so anyone can re-fetch the bundle, hash it locally, and compare against
/// this on-chain record to detect tampering.
contract VerificationRegistry {
    struct Record {
        bytes32 dataHash;   // sha256 of the canonical evidence bundle JSON
        string ipfsCID;     // where the full bundle is pinned
        address submitter;
        uint256 timestamp;
    }

    Record[] private records;

    event RecordRegistered(
        uint256 indexed recordId,
        bytes32 dataHash,
        string ipfsCID,
        address indexed submitter,
        uint256 timestamp
    );

    /// @notice Register a new evidence record on-chain.
    /// @return recordId The index used to look up this record later.
    function registerRecord(bytes32 dataHash, string calldata ipfsCID) external returns (uint256 recordId) {
        recordId = records.length;
        records.push(Record({
            dataHash: dataHash,
            ipfsCID: ipfsCID,
            submitter: msg.sender,
            timestamp: block.timestamp
        }));
        emit RecordRegistered(recordId, dataHash, ipfsCID, msg.sender, block.timestamp);
    }

    /// @notice Fetch a previously registered record.
    function getRecord(uint256 recordId) external view returns (
        bytes32 dataHash,
        string memory ipfsCID,
        address submitter,
        uint256 timestamp
    ) {
        Record storage r = records[recordId];
        return (r.dataHash, r.ipfsCID, r.submitter, r.timestamp);
    }

    /// @notice Re-verify: does the given hash match what's on-chain for this record?
    function verifyHash(uint256 recordId, bytes32 dataHash) external view returns (bool) {
        return records[recordId].dataHash == dataHash;
    }

    function totalRecords() external view returns (uint256) {
        return records.length;
    }
}
