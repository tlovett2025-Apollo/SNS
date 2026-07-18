#!/usr/bin/env node
// Rebuild downloadable CSVs from the browser's canonical sample pantry data.

import { execFileSync } from "node:child_process";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import vm from "node:vm";
import { fileURLToPath } from "node:url";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const sourcePath = path.join(root, "web", "public-site", "sample-pantries.js");
const outputPath = path.join(root, "data", "SNS_Regional_Sample_Pantry_CSVs.zip");
const work = fs.mkdtempSync(path.join(os.tmpdir(), "sns-pantries-"));
const csvDir = path.join(work, "csv");
fs.mkdirSync(csvDir);

const context = { window: {} };
vm.createContext(context);
vm.runInContext(fs.readFileSync(sourcePath, "utf8"), context, { filename: sourcePath });
const pantries = context.window.SNS_SAMPLE_PANTRIES;
if (!Array.isArray(pantries) || pantries.length !== 11) {
  throw new Error("Expected 11 regional sample pantries.");
}

const columns = ["name", "form", "storage_location", "quantity", "unit", "quantity_band", "origin", "notes"];
const quote = value => {
  const text = String(value ?? "");
  return /[",\r\n]/.test(text) ? `"${text.replaceAll('"', '""')}"` : text;
};
const csv = (headers, rows) => [headers, ...rows]
  .map(row => row.map(quote).join(","))
  .join("\r\n") + "\r\n";

const combined = [];
for (const pantry of pantries) {
  const rows = pantry.items.map(item => columns.map(column => item[column] ?? ""));
  fs.writeFileSync(path.join(csvDir, `${pantry.id}.csv`), csv(columns, rows));
  for (const item of pantry.items) {
    combined.push([pantry.id, pantry.label, ...columns.map(column => item[column] ?? "")]);
  }
}
fs.writeFileSync(
  path.join(work, "all_regional_sample_pantries.csv"),
  csv(["sample_id", "region", ...columns], combined)
);
try {
  const expansion = execFileSync("unzip", ["-p", outputPath, "regional_expansion_candidates.csv"]);
  fs.writeFileSync(path.join(work, "regional_expansion_candidates.csv"), expansion);
} catch {
  fs.writeFileSync(
    path.join(work, "regional_expansion_candidates.csv"),
    "region_hint,name,reason,priority\r\n"
  );
}
fs.rmSync(outputPath, { force: true });
execFileSync("zip", ["-q", "-r", outputPath, "csv", "all_regional_sample_pantries.csv", "regional_expansion_candidates.csv"], { cwd: work });
console.log(`Exported ${pantries.length} regional pantries to ${outputPath}`);
