const fs = require("fs");
const path = require("path");

async function main() {
    const VotingStorage = await ethers.getContractFactory("VotingStorage");

    const votingStorage = await VotingStorage.deploy();

    await votingStorage.deployed();

    console.log("VotingStorage deployed to:", votingStorage.address);

    const contractInfo = {
        address: votingStorage.address,
        abi: JSON.parse(votingStorage.interface.format("json"))
    };

    const filePath = path.join(__dirname, "..", "contract-info.json");

    fs.writeFileSync(
        filePath,
        JSON.stringify(contractInfo, null, 4)
    );

    console.log("contract-info.json created successfully");
}

main()
    .then(() => {
        process.exit(0);
    })
    .catch((error) => {
        console.error(error);
        process.exit(1);
    });