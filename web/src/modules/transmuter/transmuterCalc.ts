import oreDataJson from "./oreData.json";
import imgUrlsJson from "./imgUrls.json";

export type OreRow = {
  world: number;
  name: string;
  cost: number;
  oreImg: string;
  barImg: string;
};

export const ORE_DATA: readonly OreRow[] = oreDataJson as OreRow[];

const IMG_URLS: readonly string[] = imgUrlsJson as string[];

export function resolveWikiImageUrl(filename: string): string | undefined {
  for (const url of IMG_URLS) {
    const slash = url.lastIndexOf("/");
    const base = slash >= 0 ? url.slice(slash + 1) : url;
    if (base === filename) return `https:${url}`;
  }
  return undefined;
}

export type TransmuterInputs = {
  free: number;
  x2: number;
  x3: number;
  x5: number;
  x10: number;
  x20: number;
  x100: number;
  craftcost: number;
  bop: number;
  trans: number;
  transbop: number;
  bopgold: number;
  goldchance: number;
  goldmult: number;
};

export type TransmuterResult = {
  costTransition: number;
  lowOre: OreRow | null;
  highOre: OreRow | null;
};

function clamp(val: number, lo: number, hi: number): number {
  if (!Number.isFinite(val)) return lo;
  return Math.max(lo, Math.min(hi, val));
}

function toMult(num: number, mult: number): number {
  return 1 + clamp(num / 100, 0, 1) * (mult - 1);
}

function scale(chance: number, pass: number, fail: number): number {
  return chance * pass + (1 - chance) * fail;
}

/** Expected ore value after a possible BoP (matches tabatkins transmuter tool). */
function boppedOre(params: { bopChance: number; bopMult: number; goldChance: number; bopGoldChance: number; goldMult: number }): number {
  const { bopChance, bopMult, goldChance, bopGoldChance, goldMult } = params;
  const fullGoldChance = scale(goldChance, 1, bopGoldChance);
  const fullGoldMult = scale(fullGoldChance, goldMult, 1);
  const bopOre = bopMult * fullGoldMult;
  const missedOre = scale(goldChance, goldMult, 1);
  return scale(bopChance, bopOre, missedOre);
}

export function computeTransmuter(inputs: TransmuterInputs, oreData: readonly OreRow[] = ORE_DATA): TransmuterResult {
  const free = 1 / (1 - clamp(inputs.free / 100, 0, 1));
  const x2 = toMult(inputs.x2, 2);
  const x3 = toMult(inputs.x3, 3);
  const x5 = toMult(inputs.x5, 5);
  const x10 = toMult(inputs.x10, 10);
  const x20 = toMult(inputs.x20, 20);
  const x100 = toMult(inputs.x100, 100);
  const craftCostReduction = clamp(inputs.craftcost, 0, 1);
  const bopMult = clamp(inputs.bop, 1, Infinity);
  const transMult = clamp(inputs.trans, 1, Infinity);
  const transBopChance = clamp(inputs.transbop / 100, 0, 1);
  const bopGoldChance = clamp(inputs.bopgold / 100, 0, 1);
  const goldChance = clamp(inputs.goldchance / 100, 0, 1);
  const goldMult = clamp(inputs.goldmult, 1, Infinity);

  const craftMult = free * x2 * x3 * x5 * x10 * x20 * x100;

  const bopOre = boppedOre({ bopChance: 1, bopMult, goldChance, bopGoldChance, goldMult });
  const bopBars = craftMult * bopOre;

  const transOre = boppedOre({ bopChance: transBopChance, bopMult, goldChance, bopGoldChance, goldMult });
  const craftedTransBars = craftMult * transOre;
  const directTransBars = transMult * transOre;

  const costTransition = (bopBars - craftedTransBars) / directTransBars;

  let i = 0;
  let lowOre: OreRow | null = null;
  let highOre: OreRow | null = null;
  for (const row of oreData) {
    const scaledCraftCost = Math.floor(row.cost * craftCostReduction);
    if (scaledCraftCost > costTransition) {
      highOre = row;
      lowOre = i > 0 ? oreData[i - 1]! : null;
      break;
    }
    i++;
  }

  return { costTransition, lowOre, highOre };
}
