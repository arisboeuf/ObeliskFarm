import type { BlockTier, BlockType } from "./types";

export type BlockData = {
  tier: BlockTier;
  block_type: BlockType;
  health: number;
  xp: number;
  armor: number;
  fragment: number;
  floor_min: number;
  floor_max: number; // Infinity for open-ended
};

export const BLOCK_TYPES: BlockType[] = ["dirt", "common", "rare", "epic", "legendary", "mythic"];

export const BLOCK_DATA: BlockData[] = [
  // Tier 1
  { tier: 1, block_type: "dirt", health: 100, xp: 0.05, armor: 0, fragment: 0.0, floor_min: 1, floor_max: 11 },
  { tier: 1, block_type: "common", health: 250, xp: 0.15, armor: 5, fragment: 0.01, floor_min: 1, floor_max: 17 },
  { tier: 1, block_type: "rare", health: 550, xp: 0.35, armor: 12, fragment: 0.01, floor_min: 3, floor_max: 25 },
  { tier: 1, block_type: "epic", health: 1150, xp: 1.0, armor: 25, fragment: 0.01, floor_min: 6, floor_max: 29 },
  { tier: 1, block_type: "legendary", health: 1950, xp: 3.5, armor: 50, fragment: 0.01, floor_min: 12, floor_max: 31 },
  { tier: 1, block_type: "mythic", health: 3500, xp: 7.5, armor: 150, fragment: 0.01, floor_min: 20, floor_max: 34 },

  // Tier 2
  { tier: 2, block_type: "dirt", health: 300, xp: 0.15, armor: 0, fragment: 0.0, floor_min: 12, floor_max: 23 },
  { tier: 2, block_type: "common", health: 600, xp: 0.45, armor: 9, fragment: 0.02, floor_min: 18, floor_max: 28 },
  { tier: 2, block_type: "rare", health: 1650, xp: 1.05, armor: 21, fragment: 0.02, floor_min: 26, floor_max: 35 },
  { tier: 2, block_type: "epic", health: 3450, xp: 3.0, armor: 44, fragment: 0.02, floor_min: 30, floor_max: 41 },
  { tier: 2, block_type: "legendary", health: 5850, xp: 10.5, armor: 88, fragment: 0.02, floor_min: 32, floor_max: 44 },
  { tier: 2, block_type: "mythic", health: 10500, xp: 22.5, armor: 262, fragment: 0.02, floor_min: 36, floor_max: 49 },

  // Tier 3
  { tier: 3, block_type: "dirt", health: 900, xp: 0.45, armor: 0, fragment: 0.04, floor_min: 24, floor_max: Number.POSITIVE_INFINITY },
  { tier: 3, block_type: "common", health: 2250, xp: 1.35, armor: 15, fragment: 0.04, floor_min: 30, floor_max: Number.POSITIVE_INFINITY },
  { tier: 3, block_type: "rare", health: 4950, xp: 3.15, armor: 37, fragment: 0.04, floor_min: 36, floor_max: Number.POSITIVE_INFINITY },
  { tier: 3, block_type: "epic", health: 10350, xp: 9.0, armor: 77, fragment: 0.04, floor_min: 42, floor_max: Number.POSITIVE_INFINITY },
  { tier: 3, block_type: "legendary", health: 17500, xp: 31.5, armor: 153, fragment: 0.04, floor_min: 45, floor_max: Number.POSITIVE_INFINITY },
  { tier: 3, block_type: "mythic", health: 31500, xp: 67.5, armor: 459, fragment: 0.04, floor_min: 50, floor_max: Number.POSITIVE_INFINITY },
];

function key(tier: number, bt: string) {
  return `${tier}:${bt}`;
}

const INDEX = new Map<string, BlockData>(BLOCK_DATA.map((b) => [key(b.tier, b.block_type), b]));

const BY_TYPE = new Map<BlockType, BlockData[]>();
for (const b of BLOCK_DATA) {
  const arr = BY_TYPE.get(b.block_type) ?? [];
  arr.push(b);
  BY_TYPE.set(b.block_type, arr);
}

export function getBlockData(tier: BlockTier, blockType: BlockType): BlockData | null {
  return INDEX.get(key(tier, blockType)) ?? null;
}

export function getBlockAtFloor(floor: number, blockType: BlockType): BlockData | null {
  const blocks = BY_TYPE.get(blockType) ?? [];
  const valid = blocks.filter((b) => b.floor_min <= floor && floor <= b.floor_max);
  if (!valid.length) return null;
  return valid.reduce((best, cur) => (cur.tier > best.tier ? cur : best), valid[0]);
}

export function getBlockMixForFloor(floor: number): Record<BlockType, BlockData> {
  const out: Partial<Record<BlockType, BlockData>> = {};
  for (const bt of BLOCK_TYPES) {
    const b = getBlockAtFloor(floor, bt);
    if (b) out[bt] = b;
  }
  return out as Record<BlockType, BlockData>;
}

