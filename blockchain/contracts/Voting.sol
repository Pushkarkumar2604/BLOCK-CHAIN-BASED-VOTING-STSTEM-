// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract VotingSystem {

    // Admin address
    address public admin;

    // Constructor sets the contract deployer as admin
    constructor() {
        admin = msg.sender;
    }

    // Candidate structure
    struct Candidate {
        string name;
        string partySymbol;
        uint voteCount;
    }

    // Voter structure
    struct Voter {
        bool isRegistered;
        bool hasVoted;
    }

    // Array to store candidates
    Candidate[] public candidates;

    // Mapping to store voter details
    mapping(address => Voter) public voters;

    // Event emitted whenever a vote is cast
    event VoteCast(address voter, uint candidateId);

    // Modifier to allow only admin access
    modifier onlyAdmin() {
        require(msg.sender == admin, "Only admin can perform this action");
        _;
    }

    // -------------------------------
    // 1. Admin adds candidates
    // -------------------------------
    function addCandidate(string memory _name, string memory _partySymbol) public onlyAdmin {
        candidates.push(Candidate({
            name: _name,
            partySymbol: _partySymbol,
            voteCount: 0
        }));
    }

    // -------------------------------
    // 2. Admin registers voters
    // -------------------------------
    function registerVoter(address _voter) public onlyAdmin {
        voters[_voter].isRegistered = true;
    }

    // -------------------------------
    // 3,4,5. Vote function
    // -------------------------------
    function vote(uint _candidateId) public {

        // Check if voter is registered
        require(voters[msg.sender].isRegistered, "Not a registered voter");

        // Check if voter has already voted
        require(!voters[msg.sender].hasVoted, "Already voted");

        require(_candidateId < candidates.length, "Invalid candidate");

        // Mark voter as voted
        voters[msg.sender].hasVoted = true;

        // Increase candidate vote count
        candidates[_candidateId].voteCount++;

        // Emit event
        emit VoteCast(msg.sender, _candidateId);
    }

    // -------------------------------
    // 6. Get total votes per candidate
    // -------------------------------
    function getVotes(uint _candidateId) public view returns (uint) {
        require(_candidateId < candidates.length, "Invalid candidate");
        return candidates[_candidateId].voteCount;
    }

    // -------------------------------
    // 7. Get all candidates
    // -------------------------------
    function getAllCandidates() public view returns (Candidate[] memory) {
        return candidates;
    }
}