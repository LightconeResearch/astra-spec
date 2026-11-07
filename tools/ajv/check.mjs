// Compiles each JSON Schema named on the command line with the pinned Ajv's
// draft 2019-09 build under `strict: true`, which turns on every strict check
// (strictSchema, strictTypes, strictTuples, strictRequired), with allErrors
// and verbose. Exits non-zero if any fails.
import { readFileSync } from "node:fs";
import Ajv2019 from "ajv/dist/2019.js";

let failed = false;
for (const path of process.argv.slice(2)) {
  const ajv = new Ajv2019({ strict: true, allErrors: true, verbose: true });
  try {
    ajv.compile(JSON.parse(readFileSync(path, "utf8")));
    console.log(`${path}: compiles under strict: true`);
  } catch (error) {
    console.error(`${path}: ${error.message}`);
    failed = true;
  }
}
if (process.argv.length < 3) {
  console.error("usage: node check.mjs <schema.json>...");
  failed = true;
}
process.exit(failed ? 1 : 0);
