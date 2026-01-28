// Ported from ObeliskGemEV/event/stats.py

export interface PlayerStats {
  defaultAtkTime: number; // seconds
  defaultWalkTime: number; // seconds
  walkSpeed: number;
  atkSpeed: number; // attacks per second
  health: number;
  atk: number;
  crit: number; // percent
  critDmg: number; // multiplier
  blockChance: number; // 0..1
  gameSpeed: number; // multiplier-ish
  prestigeBonusScale: number;
  x2Money: number;
  x5Money: number; // percent
}

export interface EnemyStats {
  defaultAtkTime: number;
  atkSpeed: number;
  baseHealth: number;
  healthScaling: number;
  atk: number;
  atkScaling: number;
  crit: number; // percent base
  critDmg: number;
  critDmgScaling: number;
}

export function createBasePlayerStats(): PlayerStats {
  return {
    defaultAtkTime: 2.0,
    defaultWalkTime: 4.0,
    walkSpeed: 1.0,
    atkSpeed: 1.0,
    health: 100,
    atk: 10,
    crit: 0,
    critDmg: 2.0,
    blockChance: 0.0,
    gameSpeed: 1.0,
    prestigeBonusScale: 0.1,
    x2Money: 0,
    x5Money: 0,
  };
}

export function createBaseEnemyStats(): EnemyStats {
  return {
    defaultAtkTime: 2.0,
    atkSpeed: 0.8,
    baseHealth: 4,
    healthScaling: 7,
    atk: 2.5,
    atkScaling: 0.6,
    crit: 0,
    critDmg: 1.0,
    critDmgScaling: 0.05,
  };
}

