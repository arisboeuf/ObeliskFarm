import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const webRoot = path.resolve(__dirname, "..");
const dstDir = path.join(webRoot, "public", "sprites", "archaeology");

/**
 * Refresh archaeology sprites from the wiki (full size, not thumbnails).
 * Committed copies live in public/sprites/archaeology/; prepare-assets re-downloads to keep them current.
 */
const WIKI_SPRITES = [
  ["fragmentcommon.png", "https://static.wikitide.net/shminerwiki/d/d5/Arch_Fragment_Common.png"],
  ["fragmentrare.png", "https://static.wikitide.net/shminerwiki/a/a5/Arch_Fragment_Rare.png"],
  ["fragmentepic.png", "https://static.wikitide.net/shminerwiki/5/50/Arch_Fragment_Epic.png"],
  ["fragmentlegendary.png", "https://static.wikitide.net/shminerwiki/1/13/Arch_Fragment_Legendary.png"],
  ["fragmentmythic.png", "https://static.wikitide.net/shminerwiki/0/04/Arch_Fragment_Mythic.png"],
  ["fragmentdivine.png", "https://static.wikitide.net/shminerwiki/6/6c/Arch_Fragment_Divine.png"],
  ["Archaeology_Strength.png", "https://static.wikitide.net/shminerwiki/a/a4/Archaeology_Strength.png"],
  ["Archaeology_Agility.png", "https://static.wikitide.net/shminerwiki/5/57/Archaeology_Agility.png"],
  ["Archaeology_Perception.png", "https://static.wikitide.net/shminerwiki/5/52/Archaeology_Perception.png"],
  ["Archaeology_Intellect.png", "https://static.wikitide.net/shminerwiki/8/8d/Archaeology_Intellect.png"],
  ["Archaeology_Luck.png", "https://static.wikitide.net/shminerwiki/b/b1/Archaeology_Luck.png"],
  ["Archaeology_Divinity.png", "https://static.wikitide.net/shminerwiki/3/3f/Archaeology_Divinity.png"],
  ["Archaeology_Corruption.png", "https://static.wikitide.net/shminerwiki/8/87/Archaeology_Corruption.png"],
  ["Archaeology_Ability_Enrage.png", "https://static.wikitide.net/shminerwiki/2/2a/Archaeology_Ability_Enrage.png"],
  ["Archaeology_Ability_Flurry.png", "https://static.wikitide.net/shminerwiki/e/e4/Archaeology_Ability_Flurry.png"],
  ["Archaeology_Ability_Quake.png", "https://static.wikitide.net/shminerwiki/a/ab/Archaeology_Ability_Quake.png"],
  ["avadakeda.png", "https://static.wikitide.net/shminerwiki/0/03/Avada_Keda-.png"],
  ["blockbonker.png", "https://static.wikitide.net/shminerwiki/5/58/Block_Bonker.png"],
  ["cards.png", "https://static.wikitide.net/shminerwiki/b/bc/Cards_Button.png"],
];

async function downloadOne(filename, url) {
  const dst = path.join(dstDir, filename);
  const res = await fetch(url);
  if (!res.ok) throw new Error(`${filename}: HTTP ${res.status} for ${url}`);
  const buf = Buffer.from(await res.arrayBuffer());
  fs.writeFileSync(dst, buf);
}

async function main() {
  fs.mkdirSync(dstDir, { recursive: true });
  let ok = 0;
  let failed = 0;
  for (const [filename, url] of WIKI_SPRITES) {
    try {
      await downloadOne(filename, url);
      ok += 1;
    } catch (err) {
      failed += 1;
      console.warn(`Failed ${filename}: ${err instanceof Error ? err.message : err}`);
    }
  }
  console.log(`Downloaded ${ok}/${WIKI_SPRITES.length} archaeology sprites to ${dstDir}`);
  if (failed > 0) process.exitCode = 1;
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
