<<<<<<< HEAD
const fs = require("fs");
const path = require("path");

async function main() {
    const VotingStorage = await ethers.getContractFactory("VotingStorage");

    const votingStorage = await VotingStorage.deploy();

    await votingStorage.deployed();

    console.log("VotingStorage deployed to:", votingStorage.address);

    const contractInfo = {
        address: votingStorage.address,
        abi: JSON.parse(
            votingStorage.interface.format("json")
        )
    };

    const outputPath = path.join(
        __dirname,
        "..",
        "contract-info.json"
    );

    fs.writeFileSync(
        outputPath,
        JSON.stringify(contractInfo, null, 4)
    );

    console.log("contract-info.json created successfully");
}

main()
    .then(() => process.exit(0))
    .catch((error) => {
        console.error(error);
        process.exit(1);
    });
=======
const hre = require("hardhat");

async function main() {
  const Voting = await hre.ethers.getContractFactory("Voting");
  const voting = await Voting.deploy();
  await voting.waitForDeployment();
  console.log("Voting contract deployed to:", await voting.getAddress());
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
>>>>>>> d59b451b079f7f1d45c650c89b90cca9a79d3b44
