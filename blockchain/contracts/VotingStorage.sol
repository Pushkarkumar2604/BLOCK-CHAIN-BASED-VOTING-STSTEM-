// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

contract VotingStorage {
    address public admin;

    struct VoteRecord {
        bytes32 voterHash;
        uint256 candidateId;
        uint256 timestamp;
    }

    VoteRecord[] public votes;

    event VoteStored(
        bytes32 indexed voterHash,
        uint256 indexed candidateId,
        uint256 timestamp
    );

    constructor() {
        admin = msg.sender;
    }

    function storeVote(bytes32 voterHash, uint256 candidateId) public {
        votes.push(
            VoteRecord(
                voterHash,
                candidateId,
                block.timestamp
            )
        );

        emit VoteStored(
            voterHash,
            candidateId,
            block.timestamp
        );
    }

    function getTotalVotesOnChain() public view returns (uint256) {
        return votes.length;
    }

    function getVote(uint256 index) public view returns (
        bytes32 voterHash,
        uint256 candidateId,
        uint256 timestamp
    ) {
        VoteRecord memory voteRecord = votes[index];

        return (
            voteRecord.voterHash,
            voteRecord.candidateId,
            voteRecord.timestamp
        );
    }
}