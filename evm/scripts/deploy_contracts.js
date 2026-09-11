const { deployAll } = require("./deploy_helpers");

async function main() {
  const { payload, outputPath } = await deployAll();
  console.log(JSON.stringify(payload, null, 2));
  console.log(`Deployment record written to: ${outputPath}`);
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
