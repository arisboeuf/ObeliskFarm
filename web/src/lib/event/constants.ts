// Ported (minimally) from ObeliskGemEV/event/constants.py

export const UPGRADE_SHORT_NAMES: Record<number, string[]> = {
  1: [
    "ATK +1",
    "HP +2",
    "ASpd +0.02",
    "MSpd +0.03",
    "GSpd +2%",
    "Crit +1%",
    "ATK+1 HP+2",
    "T1 Caps +1",
    "Prestige +1%",
    "ATK+3 HP+3",
  ],
  2: ["HP +3", "E.ASpd -0.02", "E.ATK -1", "E.Crit -1%", "ATK+1 ASpd+0.01", "T2 Caps +1", "Prestige +2%"],
  3: ["ATK +2", "ASpd +0.02", "Crit +1%", "GSpd +3%", "ATK+3 HP+3", "T3 Caps +1", "5x Drop +3%", "HP+5 ASpd+0.03"],
  4: ["Block +1%", "HP +5", "Crit Dmg +0.10", "ASpd+0.02 MSpd+0.02", "HP+4 ATK+4", "T4 Caps +1", "Cap of Caps +1", "HP+10 ASpd+0.05"],
};

export const PRESTIGE_UNLOCKED: Record<number, number[]> = {
  1: [0, 0, 0, 0, 1, 2, 2, 4, 8, 10],
  2: [0, 0, 0, 3, 4, 5, 10],
  3: [1, 1, 2, 3, 4, 6, 8, 10],
  4: [1, 3, 4, 5, 6, 6, 7, 10],
};

export const MAX_LEVELS: Record<number, number[]> = {
  1: [50, 50, 25, 25, 25, 25, 25, 10, 5, 40],
  2: [25, 15, 10, 15, 25, 10, 15],
  3: [20, 20, 20, 20, 10, 10, 10, 40],
  4: [15, 15, 15, 15, 15, 10, 10, 40],
};

// 1-indexed in original docs; stored as 1-indexed here to mirror Python constant usage.
export const CAP_UPGRADES: Record<number, number> = { 1: 8, 2: 6, 3: 6, 4: 6 };

export const COSTS: Record<number, number[]> = {
  1: [5, 6, 8, 10, 12, 20, 75, 2500, 25000, 5000],
  2: [5, 8, 12, 20, 40, 500, 650],
  3: [5, 8, 12, 18, 30, 250, 300, 125],
  4: [10, 12, 15, 20, 50, 250, 500, 150],
};

export const GEM_UPGRADE_NAMES = ["+10% Dmg", "+10% Max HP", "+125% Event Game Spd", "2x Event Currencies"] as const;

export function getPrestigeWaveRequirement(prestige: number): number {
  return (prestige + 1) * 5;
}

