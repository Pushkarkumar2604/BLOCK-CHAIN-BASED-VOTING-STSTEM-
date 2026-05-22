// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

contract Voting {
    address public admin;
    
    struct Candidate {
        uint id;
        string name;
        string party;
        uint voteCount;
    }
    
    mapping(uint => Candidate) public candidates;
    mapping(address => bool) public registeredVoters;
    mapping(address => bool) public hasVoted;
    uint public candidatesCount;

    event VoteCasted(address voter, uint candidateId);

    constructor() {
        admin = msg.sender;
    }

    modifier onlyAdmin() {
        require(msg.sender == admin, "Only admin allowed!");
        _;
    }

    function addCandidate(string memory name, string memory party) public onlyAdmin {
        candidatesCount++;
        candidates[candidatesCount] = Candidate(candidatesCount, name, party, 0);
    }

    function registerVoter(address voter) public onlyAdmin {
        registeredVoters[voter] = true;
    }

    function vote(uint candidateId) public {
        require(registeredVoters[msg.sender], "Not a registered voter!");
        require(!hasVoted[msg.sender], "Already voted!");
        require(candidateId > 0 && candidateId <= candidatesCount, "Invalid candidate!");
        hasVoted[msg.sender] = true;
        candidates[candidateId].voteCount++;
        emit VoteCasted(msg.sender, candidateId);
    }

    function getCandidate(uint id) public view returns (string memory, string memory, uint) {
        return (candidates[id].name, candidates[id].party, candidates[id].voteCount);
    }
}