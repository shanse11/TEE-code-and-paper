// revision_env.js — shared helpers for the real-blob revision scripts.
//
// SECURITY: this module NEVER prints secret material. It only ever reports booleans
// (whether a variable is set) and, for URLs, the host with any query string / auth stripped.

const fs = require("fs");
const path = require("path");
const dotenv = (() => {
  try {
    return require("dotenv");
  } catch (_e) {
    return null;
  }
})();

const REVISION_RUN = process.env.REVISION_RUN;
const EVM_DIR = path.resolve(__dirname, ".."); // evm/
const CACHE_DIR = REVISION_RUN ? path.join(REVISION_RUN, "cache") : null;

// Load evm/.env if present (does not override already-set process.env by default).
if (dotenv && fs.existsSync(path.join(EVM_DIR, ".env"))) {
  dotenv.config({ path: path.join(EVM_DIR, ".env") });
}

// Only booleans — never the values.
function creds() {
  return {
    SEPOLIA_RPC_URL: !!process.env.SEPOLIA_RPC_URL,
    SEPOLIA_PRIVATE_KEY: !!process.env.SEPOLIA_PRIVATE_KEY,
    BEACON_API_URL: !!process.env.BEACON_API_URL,
  };
}

// Host-only view of a URL (strips query string + auth) — safe to log.
function safeHost(url) {
  if (!url) return "<unset>";
  try {
    const u = new URL(url);
    return u.host || "<invalid-url>";
  } catch (_e) {
    return "<unset-or-invalid>";
  }
}

function preflightOrFail(cond, msg) {
  if (!cond) {
    console.error("PREFLOW FAIL (closed): " + msg);
    console.error(
      "  creds => " + JSON.stringify(creds()) + "  (no transaction/request is sent on preflight failure)"
    );
    process.exit(2);
  }
}

function requireRun() {
  if (!REVISION_RUN || !path.isAbsolute(REVISION_RUN)) {
    console.error("PREFLOW FAIL: REVISION_RUN must be an absolute run directory.");
    process.exit(2);
  }
  fs.mkdirSync(CACHE_DIR, { recursive: true });
  return REVISION_RUN;
}

function statePath(name) {
  return path.join(CACHE_DIR, name + ".json");
}
function readState(name) {
  const p = statePath(name);
  if (!fs.existsSync(p)) return null;
  try {
    return JSON.parse(fs.readFileSync(p, "utf8"));
  } catch (_e) {
    return null;
  }
}
function writeState(name, obj) {
  fs.mkdirSync(CACHE_DIR, { recursive: true });
  fs.writeFileSync(statePath(name), JSON.stringify(obj, null, 2));
}

module.exports = {
  REVISION_RUN,
  EVM_DIR,
  creds,
  safeHost,
  preflightOrFail,
  requireRun,
  readState,
  writeState,
};
