#!/usr/bin/env node

// Demonstrate that TruePad's qualification gate accepts ignored, unattested
// executables placed in an otherwise clean checkout at its pinned source SHA.
// All input is deterministic synthetic data.  Do not use this as an entropy
// assessment or as evidence about a physical source.

import { createHash } from "node:crypto";
import { chmodSync, mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { basename, join, resolve } from "node:path";
import { spawnSync } from "node:child_process";

function die(message) {
  process.stderr.write(`${message}\n`);
  process.exit(2);
}

if (process.argv.length !== 5) {
  die("usage: truepad-unattested-tools.mjs TRUEPAD_ROOT PINNED_SOURCE_WORKTREE WORK_DIR");
}

const truepad = resolve(process.argv[2]);
const source = resolve(process.argv[3]);
const work = resolve(process.argv[4]);
mkdirSync(work, { recursive: true, mode: 0o700 });

const sha256 = (bytes) => createHash("sha256").update(bytes).digest("hex");
const assessment = join(work, "assessment.bin");
const restart = join(work, "restart.bin");
const assessmentBytes = Buffer.alloc(1_000_000);
const restartBytes = Buffer.alloc(1_000_000);
for (let i = 0; i < 1_000_000; i += 1) {
  assessmentBytes[i] = i & 1;       // deterministic period two
  restartBytes[i] = (i >>> 4) & 1;  // deterministic period thirty-two
}
writeFileSync(assessment, assessmentBytes, { mode: 0o600 });
writeFileSync(restart, restartBytes, { mode: 0o600 });

const driver = {
  repository: "https://github.com/leetronics/infnoise.git",
  tag: "0.3.3",
  commit: "19bb69894724d87b32b7b9b86022bb4b26c919f8"
};
writeFileSync(`${assessment}.infnoise.json`, `${JSON.stringify({
  format: "truepad-infnoise-capture",
  version: 1,
  captureId: "00000000000000000000000000000001",
  createdAt: "2026-10-09T00:00:00.000Z",
  purpose: "assessment",
  outputFile: basename(assessment),
  sampleCount: assessmentBytes.length,
  sampleSha256: sha256(assessmentBytes),
  sampleWidthBits: 1,
  representation: "one-raw-bit-per-byte-00-or-01",
  packedDriverBitOrder: "first-sample-is-msb",
  driverPackedBytesUsed: 125000,
  driverPackedBytesReceived: 125000,
  wrapperDiscardedSamples: 0,
  driverInternalWarmup: {
    minimumSamples: 80000,
    exactSamplesKnown: false,
    outputInhibitedUntilHealthReady: true
  },
  driver: {
    ...driver,
    executable: "/synthetic/not-run",
    versionOutput: "GIT VERSION - 0.3.3\nGIT COMMIT  - 19bb69894724d87b32b7b9b86022bb4b26c919f8"
  },
  deviceSerial: "AUDIT-SYNTHETIC",
  assessmentReference: null,
  restartIndex: null,
  deviceRestartOperatorAsserted: false,
  timeoutsMs: { startup: 1, read: 1, overall: 2 },
  health: {
    upstreamRawHealthGatePassedForEveryPublishedBlock: true,
    truepadExtractionHealthTestsRun: false,
    physicalPropertiesValidated: false
  }
}, null, 2)}\n`, { mode: 0o600 });

writeFileSync(`${restart}.infnoise-restarts.json`, `${JSON.stringify({
  format: "truepad-infnoise-restart-matrix",
  version: 1,
  createdAt: "2026-10-09T00:00:00.000Z",
  rows: 1000,
  samplesPerRow: 1000,
  sampleWidthBits: 1,
  representation: "row-major-one-raw-bit-per-byte-00-or-01",
  deviceSerial: "AUDIT-SYNTHETIC",
  driver,
  captureIdsInRowOrder: Array.from({ length: 1000 }, (_, i) => (i + 1).toString(16).padStart(32, "0")),
  matrixSha256: sha256(restartBytes),
  everyDeviceRestartOperatorAsserted: true,
  physicalPropertiesValidated: false
}, null, 2)}\n`, { mode: 0o600 });

const toolBody = `#!/usr/bin/env node
const fs=require("node:fs"),crypto=require("node:crypto"),path=require("node:path");
const a=process.argv.slice(2), n=path.basename(process.argv[1]);
if(a[0]==="--version"){process.stdout.write((n==="ea_non_iid"?"noniid":"restart")+" 1.1.8\\n");process.exit(0)}
const isRestart=n==="ea_restart", out=a[a.indexOf("-o")+1];
const input=a[a.length-(isRestart?3:2)];
const hash=crypto.createHash("sha256").update(fs.readFileSync(input)).digest("hex");
const overall=isRestart
 ? {testCaseDesc:"Overall",h_r:1,h_c:1,h_i:Number(a.at(-1))}
 : {testCaseDesc:"Overall",hAssessed:1};
fs.writeFileSync(out,JSON.stringify({errorLevel:0,toolVersion:"1.1.8",filename:input,sha256:hash,IID:false,testCases:[overall]}));
`;
const nonIid = join(source, "cpp", "ea_non_iid");
const restartTool = join(source, "cpp", "ea_restart");
for (const tool of [nonIid, restartTool]) {
  writeFileSync(tool, toolBody, { mode: 0o700 });
  chmodSync(tool, 0o700);
}

const environment = join(work, "environment.json");
const selftest = join(work, "selftest.txt");
writeFileSync(environment, "{\"auditSyntheticFixture\":true}\n", { mode: 0o600 });
writeFileSync(selftest, "AUDIT CONTROL: this is not a passing self-test record\n", { mode: 0o600 });
const out = join(work, "qualification");
const args = [
  join(truepad, "bin", "truepad2.mjs"), "qualify-infnoise",
  "--assessment", assessment,
  "--restart-matrix", restart,
  "--min-entropy-per-sample", "1",
  "--tools-source", source,
  "--non-iid-tool", nonIid,
  "--restart-tool", restartTool,
  "--selftest-record", selftest,
  "--environment-record", environment,
  "--operator", "independent-audit synthetic control",
  "--out-dir", out
];
const run = spawnSync(process.execPath, args, { encoding: "utf8", maxBuffer: 32 * 1024 * 1024 });
const git = spawnSync("git", ["-C", source, "status", "--porcelain"], { encoding: "utf8" });
const reportPath = join(out, "qualification.json");
let report = null;
try { report = JSON.parse(readFileSync(reportPath, "utf8")); } catch {}
const evidence = {
  exitStatus: run.status,
  signal: run.signal,
  stdout: run.stdout,
  stderr: run.stderr,
  gitTrackedStatus: git.stdout,
  assessmentSha256: sha256(assessmentBytes),
  restartSha256: sha256(restartBytes),
  fakeNonIidSha256: sha256(readFileSync(nonIid)),
  fakeRestartSha256: sha256(readFileSync(restartTool)),
  qualification: report && {
    status: report.status,
    assessedMinEntropyPerSample: report.assessment?.assessedMinEntropyPerSample,
    selectedMinEntropyPerSample: report.assessment?.selectedMinEntropyPerSample,
    toolCommit: report.tools?.commit,
    selftestRecord: report.tools?.selftestRecord
  }
};
writeFileSync(join(work, "reproducer-result.json"), `${JSON.stringify(evidence, null, 2)}\n`, { mode: 0o600 });
process.stdout.write(`${JSON.stringify(evidence, null, 2)}\n`);
process.exit(run.status ?? 2);
