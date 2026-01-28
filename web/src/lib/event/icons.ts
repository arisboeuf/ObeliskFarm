// Mirrors ObeliskGemEV/event/gui_budget.py:_load_upgrade_icons mapping.

export function upgradeIconFilename(tier: number, idx: number): string | null {
  const map: Record<string, string> = {
    // Tier 1
    "1:0": "upgrade_atk_dmg.png",
    "1:1": "upgrade_max_hp.png",
    "1:2": "upgrade_atk_speed.png",
    "1:3": "upgrade_move_speed.png",
    "1:4": "upgrade_event_speed.png",
    "1:5": "upgrade_crit_chance.png",
    "1:6": "upgrade_atk_dmg.png",
    "1:7": "upgrade_caps.png",
    "1:8": "upgrade_prestige_bonus.png",
    "1:9": "upgrade_atk_dmg.png",
    // Tier 2
    "2:0": "upgrade_max_hp.png",
    "2:1": "upgrade_enemy_atk_speed.png",
    "2:2": "upgrade_enemy_atk_dmg.png",
    "2:3": "upgrade_enemy_atk_speed.png",
    "2:4": "upgrade_atk_speed.png",
    "2:5": "upgrade_caps.png",
    "2:6": "upgrade_prestige_bonus.png",
    // Tier 3
    "3:0": "upgrade_atk_dmg.png",
    "3:1": "upgrade_atk_speed.png",
    "3:2": "upgrade_crit_chance.png",
    "3:3": "upgrade_event_speed.png",
    "3:4": "upgrade_atk_dmg.png",
    "3:5": "upgrade_caps.png",
    "3:6": "upgrade_extra_currency.png",
    "3:7": "upgrade_atk_speed.png",
    // Tier 4
    "4:0": "upgrade_block_chance.png",
    "4:1": "upgrade_max_hp.png",
    "4:2": "upgrade_crit_dmg.png",
    "4:3": "upgrade_atk_speed.png",
    "4:4": "upgrade_atk_dmg.png",
    "4:5": "upgrade_caps.png",
    "4:6": "upgrade_caps.png",
    "4:7": "upgrade_atk_speed.png",
  };
  return map[`${tier}:${idx}`] ?? null;
}

export function currencyIconFilename(tier: number): string | null {
  if (tier >= 1 && tier <= 4) return `currency_${tier}.png`;
  return null;
}

export function gemUpgradeIconFilename(idx: number): string | null {
  if (idx >= 0 && idx <= 3) return `gem_upgrade_${idx}.png`;
  return null;
}

