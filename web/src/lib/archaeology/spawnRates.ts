import type { BlockType } from "./types";

export const BOSS_FLOORS: Record<number, BlockType> = {
  11: "dirt",
  17: "common",
  23: "dirt",
  25: "rare",
  29: "epic",
  31: "legendary",
  35: "rare",
  41: "epic",
  44: "legendary",
  99: "mythic",
};

export const BLOCK_TYPES: BlockType[] = ["dirt", "common", "rare", "epic", "legendary", "mythic"];

type StageRangeKey = string;
type StageRange = { min: number; max: number };

const RANGES: Array<{ key: StageRangeKey; range: StageRange; rates: Record<BlockType, number> }> = [
  { key: "1-2", range: { min: 1, max: 2 }, rates: { dirt: 28.57, common: 14.29, rare: 0, epic: 0, legendary: 0, mythic: 0 } },
  { key: "3-4", range: { min: 3, max: 4 }, rates: { dirt: 25.4, common: 12.7, rare: 11.11, epic: 0, legendary: 0, mythic: 0 } },
  { key: "5", range: { min: 5, max: 5 }, rates: { dirt: 25.52, common: 10.94, rare: 12.5, epic: 0, legendary: 0, mythic: 0 } },
  { key: "6-9", range: { min: 6, max: 9 }, rates: { dirt: 22.97, common: 9.84, rare: 11.25, epic: 10, legendary: 0, mythic: 0 } },
  { key: "10-11", range: { min: 10, max: 11 }, rates: { dirt: 23.41, common: 8.78, rare: 9.88, epic: 11.11, legendary: 0, mythic: 0 } },
  { key: "12-14", range: { min: 12, max: 14 }, rates: { dirt: 21.74, common: 8.15, rare: 9.17, epic: 10.32, legendary: 7.14, mythic: 0 } },
  { key: "15-19", range: { min: 15, max: 19 }, rates: { dirt: 21.27, common: 7.98, rare: 8.97, epic: 11.54, legendary: 7.69, mythic: 0 } },
  { key: "20-24", range: { min: 20, max: 24 }, rates: { dirt: 19.5, common: 7.31, rare: 8.23, epic: 12.34, legendary: 8.64, mythic: 5.0 } },
  { key: "25-29", range: { min: 25, max: 29 }, rates: { dirt: 18.47, common: 7.92, rare: 9.05, epic: 12.06, legendary: 10.56, mythic: 5.0 } },
  { key: "30-49", range: { min: 30, max: 49 }, rates: { dirt: 18.1, common: 9.05, rare: 7.92, epic: 11.88, legendary: 11.88, mythic: 5.0 } },
  { key: "50-75", range: { min: 50, max: 75 }, rates: { dirt: 16.87, common: 8.43, rare: 9.84, epic: 13.77, legendary: 11.81, mythic: 5.56 } },
  { key: "75+", range: { min: 76, max: Number.POSITIVE_INFINITY }, rates: { dirt: 16.81, common: 10.08, rare: 10.08, epic: 11.76, legendary: 11.76, mythic: 5.88 } },
];

export function getSpawnRatesForStage(stage: number, ignoreBoss = false): Record<BlockType, number> {
  if (!ignoreBoss && BOSS_FLOORS[stage]) {
    const b = BOSS_FLOORS[stage];
    return { dirt: b === "dirt" ? 100 : 0, common: b === "common" ? 100 : 0, rare: b === "rare" ? 100 : 0, epic: b === "epic" ? 100 : 0, legendary: b === "legendary" ? 100 : 0, mythic: b === "mythic" ? 100 : 0 };
  }
  for (const r of RANGES) {
    if (r.range.min <= stage && stage <= r.range.max) return { ...r.rates };
  }
  return { ...RANGES[RANGES.length - 1].rates };
}

export function getTotalSpawnProbability(stage: number): number {
  const raw = getSpawnRatesForStage(stage);
  return Object.values(raw).reduce((a, b) => a + b, 0);
}

export function getNormalizedSpawnRates(stage: number, ignoreBoss = false): Record<BlockType, number> {
  const raw = getSpawnRatesForStage(stage, ignoreBoss);
  const active: Partial<Record<BlockType, number>> = {};
  let total = 0;
  for (const bt of BLOCK_TYPES) {
    const v = raw[bt];
    if (v > 0) {
      active[bt] = v;
      total += v;
    }
  }
  if (total <= 0) return { dirt: 1 } as Record<BlockType, number>;
  const out: Partial<Record<BlockType, number>> = {};
  for (const bt of Object.keys(active) as BlockType[]) {
    out[bt] = (active[bt] ?? 0) / total;
  }
  return out as Record<BlockType, number>;
}

