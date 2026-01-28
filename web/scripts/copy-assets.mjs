import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const webRoot = path.resolve(__dirname, "..");
const repoRoot = path.resolve(webRoot, "..");

function ensureDir(p) {
  fs.mkdirSync(p, { recursive: true });
}

function copyDir(srcDir, dstDir) {
  ensureDir(dstDir);
  for (const entry of fs.readdirSync(srcDir, { withFileTypes: true })) {
    const src = path.join(srcDir, entry.name);
    const dst = path.join(dstDir, entry.name);
    if (entry.isDirectory()) {
      copyDir(src, dst);
    } else if (entry.isFile()) {
      fs.copyFileSync(src, dst);
    }
  }
}

const srcSprites = path.join(repoRoot, "ObeliskGemEV", "sprites");
const dstSprites = path.join(webRoot, "public", "sprites");

// Only what we currently need for the web UI modules.
copyDir(path.join(srcSprites, "event"), path.join(dstSprites, "event"));
copyDir(path.join(srcSprites, "common"), path.join(dstSprites, "common"));
copyDir(path.join(srcSprites, "archaeology"), path.join(dstSprites, "archaeology"));

console.log("Copied sprites to web/public/sprites/");

