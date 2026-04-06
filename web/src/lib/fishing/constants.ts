/**
 * Fishing docks, aquarium fish, upgrades and enhancements (Idle Obelisk Miner).
 * Source: https://shminer.miraheze.org/wiki/Fishing
 */

import type { DockDef, DockFishSet, DockId, EnhanceDef, FishDef, UpgradeDef } from "./types";

/** Wiki image base; use Special:FilePath for redirect to static URL. */
export const FISHING_WIKI_IMAGE_BASE = "https://shminer.miraheze.org/wiki/Special:FilePath";

export function fishIconUrl(iconFile: string): string {
  return `${FISHING_WIKI_IMAGE_BASE}/${encodeURIComponent(iconFile)}`;
}

/** URL for upgrade icon (same wiki File: namespace). */
export function upgradeIconUrl(iconFile: string): string {
  return fishIconUrl(iconFile);
}

/** URL for notice fish requirement icon (same wiki File: namespace). */
export function fishReqIconUrl(iconFile: string): string {
  return fishIconUrl(iconFile);
}

/** URL for enhancement icon (same wiki File: namespace). */
export function enhanceIconUrl(iconFile: string): string {
  return fishIconUrl(iconFile);
}

/**
 * Wiki File names for dock gallery images (Fishing#Gallery).
 * If the wiki uses different names, update this map.
 */
const DOCK_GALLERY_ICON_FILES: Record<DockId, string> = {
  lake: "Fishing_Lake.png",
  desert: "Fishing_Desert.png",
  tundra: "Fishing_Tundra.png",
  ocean: "Fishing_Ocean.png",
  nuclear: "Fishing_Nuclear.png",
  abyss: "Fishing_Abyss.png",
  cave: "Fishing_Cave.png",
  volcano: "Fishing_Volcano.png",
  sky: "Fishing_Sky.png",
  solaris: "Fishing_Solaris.png",
  galaxy: "Fishing_Galaxy.png",
};

/** URL for dock gallery image (wiki Fishing#Gallery). Pass dock id for correct filename. */
export function dockIconUrl(dockId: DockId): string {
  const file = DOCK_GALLERY_ICON_FILES[dockId];
  return `${FISHING_WIKI_IMAGE_BASE}/${encodeURIComponent(file)}`;
}

/** Docks: base and upgraded ticks needed (upgraded with Abyss T1, Motley School, T2 Dock Ticks Enhance). */
export const DOCKS: DockDef[] = [
  { id: "lake", name: "Lake", tier: 1, baseTicksNeeded: 5, upgradedTicksNeeded: 4 },
  { id: "desert", name: "Desert", tier: 1, baseTicksNeeded: 8, upgradedTicksNeeded: 7 },
  { id: "tundra", name: "Tundra", tier: 1, baseTicksNeeded: 12, upgradedTicksNeeded: 10 },
  { id: "ocean", name: "Ocean", tier: 1, baseTicksNeeded: 16, upgradedTicksNeeded: 14 },
  { id: "nuclear", name: "Nuclear", tier: 1, baseTicksNeeded: 22, upgradedTicksNeeded: 19 },
  { id: "abyss", name: "Abyss", tier: 1, baseTicksNeeded: 30, upgradedTicksNeeded: 21 },
  { id: "cave", name: "Cave", tier: 2, baseTicksNeeded: 40, upgradedTicksNeeded: 24 },
  { id: "volcano", name: "Volcano", tier: 2, baseTicksNeeded: 50, upgradedTicksNeeded: 33 },
  { id: "sky", name: "Sky", tier: 2, baseTicksNeeded: 60, upgradedTicksNeeded: 42 },
  { id: "solaris", name: "Solaris", tier: 2, baseTicksNeeded: 70, upgradedTicksNeeded: 51 },
  { id: "galaxy", name: "Galaxy", tier: 2, baseTicksNeeded: 80, upgradedTicksNeeded: 60 },
];

/** All aquarium fish by dock (Tier 1 then Tier 2). Power ratings from wiki. */
export const AQUARIUM: DockFishSet[] = [
  // —— Tier 1 ——
  {
    dockId: "lake",
    fish: [
      { id: "guppy", name: "Guppy", powerRating: 100, iconFile: "Guppy.png", description: "The tin ore of the fishing world. Jealous of the bigger fish." },
      { id: "bass", name: "Bass", powerRating: 170, iconFile: "Bass.png", description: "Inspiration of the biggest freedom pyramid. Covered in a thick layer of slime, careful not to drop it." },
      { id: "catfish", name: "Catfish", powerRating: 290, iconFile: "Catfish.png", description: "Very Photogenic - don't get too close!" },
      { id: "golden_trout", name: "Golden Trout", powerRating: 490, iconFile: "Golden_Trout.png", description: "Is it made of gold? Take a bite and find out!" },
    ],
  },
  {
    dockId: "desert",
    fish: [
      { id: "sandscale_carp", name: "Sandscale Carp", powerRating: 240, iconFile: "Sandscale_Carp.png", description: "It buries itself under a thin layer of sand, waiting for unsuspecting victims to step on its razor-sharp back fin. They are just shy!" },
      { id: "armored_roller", name: "Armored Roller", powerRating: 410, iconFile: "Armored_Roller.png", description: "With its only weak point being its open mouth, it just rolls around and hopes for the best. Is it a sign of ineptitude or genius?" },
      { id: "spiny_puffer", name: "Spiny Puffer", powerRating: 690, iconFile: "Spiny_Puffer.png", description: "A popular companion for playing expert mode volleyball." },
      { id: "scarabshoe_crab", name: "Scarabshoe Crab", powerRating: 1170, iconFile: "Scarabshoe_Crab.png", description: "What's worse than a crab in your shoe? A scarabshoe in your crab." },
    ],
  },
  {
    dockId: "tundra",
    fish: [
      { id: "snow_bellied_swarmer", name: "Snow-bellied Swarmer", powerRating: 570, iconFile: "Snow-bellied_Swarmer.png", description: "A refreshing snack. Monarch Waddle's favorite food." },
      { id: "frostshell_crab", name: "Frostshell Crab", powerRating: 970, iconFile: "Frostshell_Crab.png", description: "Its unique shell is made of ice and harder than diamonds. Mostly desired for its use as an ice cube." },
      { id: "frostdrip_spearfish", name: "Frostdrip Spearfish", powerRating: 1650, iconFile: "Frostdrip_Spearfish.png", description: "The fastest fish in the obelisk expanded universe. It can pierce the thickest hulls with its head." },
      { id: "auroreel", name: "Auroreel", powerRating: 2800, iconFile: "Auroreel.png", description: "Satisfyingly squidgy - nature's fidget spinner." },
    ],
  },
  {
    dockId: "ocean",
    fish: [
      { id: "coralstar", name: "Coralstar", powerRating: 1360, iconFile: "Coralstar.png", description: "We all just want to be big coralstars!" },
      { id: "anchorfin_stingray", name: "Anchorfin Stingray", powerRating: 2310, iconFile: "Anchorfin_Stingray.png", description: "Long hours in the mines weighing you down? Simply try feeling better!" },
      { id: "pearlescent_tetra", name: "Pearlescent Tetra", powerRating: 3930, iconFile: "Pearlescent_Tetra.png", description: "The only fish the Guppy isn't jealous of." },
      { id: "gem_whale", name: "Gem Whale", powerRating: 6680, iconFile: "Gem_Whale.png", description: "Provider of freebie packs, funder of portable independent game development." },
    ],
  },
  {
    dockId: "nuclear",
    fish: [
      { id: "ionizing_eel", name: "Ionizing Eel", powerRating: 3240, iconFile: "Ionizing_Eel.png", description: "Emits a soft radioactive glow. The longer the eel, the shorter your life." },
      { id: "gammangler_fish", name: "Gammangler Fish", powerRating: 5510, iconFile: "Gammangler_Fish.png", description: "This deep-sea dweller's light is RGB and has a stroboscope effect." },
      { id: "elephants_blob", name: "Elephant's Blob", powerRating: 9370, iconFile: "Elephant's_Blob.png", description: "Named after its first 10,000 attempts at painting." },
      { id: "wastefish", name: "Wastefish", powerRating: 15930, iconFile: "Wastefish.png", description: "Feeds off of salty substances, like nuclear material and redditors." },
    ],
  },
  {
    dockId: "abyss",
    fish: [
      { id: "hadal_crusher", name: "Hadal Crusher", powerRating: 7740, iconFile: "Hadal_Crusher.png", description: "In the deepest trenches of the abyss, he dances like no one is watching." },
      { id: "live_sea_mine", name: "Live Sea Mine", powerRating: 13150, iconFile: "Live_Sea_Mine.png", description: "Anything can set it off as it aimlessly drifts through the dark waters. Maybe you should put it back." },
      { id: "ventilator_remora", name: "Ventilator Remora", powerRating: 22360, iconFile: "Ventilator_Remora.png", description: "Ender of bloodlines." },
      { id: "wreckshell_pilferer", name: "Wreckshell Pilferer", powerRating: 38020, iconFile: "Wreckshell_Pilferer.png", description: "They form together in large groups to evict crustaceans from their houses. Pioneer of Seabnb." },
    ],
  },
  // —— Tier 2 ——
  {
    dockId: "cave",
    fish: [
      { id: "stonescale_carp", name: "Stonescale Carp", powerRating: 27700, iconFile: "Stonescale_Carp.png", description: "A close relative of the Sandscale Carp, this one has evolved the ability to eat iron. Don't tell them that most animals can do that." },
      { id: "sturgem", name: "Sturgem", powerRating: 47090, iconFile: "Sturgem.png", description: "This fish is so incredibly lazy, it's grown crystals." },
      { id: "conductive_eel", name: "Conductive Eel", powerRating: 80060, iconFile: "Conductive_Eel.png", description: "A shockingly intelligent electric eel." },
      { id: "arapaim_al", name: "Arapaim-al", powerRating: 136080, iconFile: "Arapaim-al.png", description: "Technically a subspecies of the Piscis Stultus - when paired with the other subspecies, Ti-Lapia, nothing happens. They're both near extinction, but who cares really." },
    ],
  },
  {
    dockId: "volcano",
    fish: [
      { id: "molten_archerfish", name: "Molten Archerfish", powerRating: 66090, iconFile: "Molten_Archerfish.png", description: "Spits molten lava instead of water. Surprisingly ineffective..." },
      { id: "lava_snail", name: "Lava Snail", powerRating: 112360, iconFile: "Lava_Snail.png", description: "Did you know this is loosely based on a real snail of the same name?" },
      { id: "obsidian_tooth_barracuda", name: "Obsidian-Tooth Barracuda", powerRating: 191030, iconFile: "Obsidian-Tooth_Barracuda.png", description: "People like making squares with them and setting ablaze the inside, for some reason." },
      { id: "basalturtle", name: "Basalturtle", powerRating: 324740, iconFile: "Basalturtle.png", description: "It naturally has no shell, but it makes one out of rocks and begging." },
    ],
  },
  {
    dockId: "sky",
    fish: [
      { id: "sunglazed_flying_fish", name: "Sunglazed Flying Fish", powerRating: 157720, iconFile: "Sunglazed_Flying_Fish.png", description: "Can be eaten raw, but it's absolutely disgusting." },
      { id: "cloudcutter_manta", name: "Cloudcutter Manta", powerRating: 268140, iconFile: "Cloudcutter_Manta.png", description: "Causes rain when it flies through clouds. They know when it's most inconvenient." },
      { id: "shocksailfish", name: "Shocksailfish", powerRating: 455830, iconFile: "Shocksailfish.png", description: "Imbued with the power of lightning, these fish move at a blazing 19 kilometers per hour, or roughly 61m hot dogs per quarantine." },
      { id: "lunar_sunfish", name: "Lunar Sunfish", powerRating: 774930, iconFile: "Lunar_Sunfish.png", description: "Surprisingly bright during the night time, and also surprisingly dimwitted." },
    ],
  },
  {
    dockId: "solaris",
    fish: [
      { id: "lanternfish_comet", name: "Lanternfish Comet", powerRating: 376390, iconFile: "Lanternfish_Comet.png", description: "This fish so closely resembles a comet, it's debated if it's actually a comet resembling a fish." },
      { id: "ufo", name: "UFO", powerRating: 639870, iconFile: "UFO.png", description: "Stands for 'unidentified flying organism,' even though it's clearly a fish." },
      { id: "sub_solar_squid", name: "Sub-Solar Squid", powerRating: 1090000, iconFile: "Sub-Solar_Squid.png", description: "Pretty much just a vegan flashbang." },
      { id: "planetary_jellyfish", name: "Planetary Jellyfish", powerRating: 1850000, iconFile: "Planetary_Jellyfish.png", description: "How is this a living thing? You can walk directly through it!" },
    ],
  },
  {
    dockId: "galaxy",
    fish: [
      { id: "heliocentric_clam", name: "Heliocentric Clam", powerRating: 898180, iconFile: "Heliocentric_Clam.png", description: "Instead of forming pearls, these bivalves form miniature stars and planets." },
      { id: "gamma_rayburst_shrimp", name: "Gamma Rayburst Shrimp", powerRating: 1530000, iconFile: "Gamma_Rayburst_Shrimp.png", description: "The snap of its claws emits so much radiation that it was considered for use in an instant microwave- until someone turned the moon into a nuke." },
      { id: "galaxia_whale", name: "Galaxia Whale", powerRating: 2600000, iconFile: "Galaxia_Whale.png", description: "To it, a solar system is little more than an anthill." },
      { id: "dark_matter_blackdragon", name: "Dark Matter Blackdragon", powerRating: 4410000, iconFile: "Dark_Matter_Blackdragon.png", description: "Uses dark matter to hide itself. But what could it be hiding from?" },
    ],
  },
];

/** Lookup dock by id. */
export function getDock(id: DockDef["id"]): DockDef | undefined {
  return DOCKS.find((d) => d.id === id);
}

/** Get the 4 fish for a dock. */
export function getFishForDock(dockId: DockDef["id"]): FishDef[] {
  const set = AQUARIUM.find((s) => s.dockId === dockId);
  return set ? [...set.fish] : [];
}

/** Legendary Fish: one per dock. Caught when all fish in dock are Poly and last fish has 100%+ catch. Chance: min(9, floor(lastCatch%/100))/150k per fill. */
export const LEGENDARY_FISH: { dockId: DockId; id: string; name: string; iconUrl: string }[] = [
  { dockId: "lake", id: "lake_legendary", name: "Rainbow Trout", iconUrl: "https://static.wikitide.net/shminerwiki/thumb/d/da/Lake_Legendary_Fish.png/45px-Lake_Legendary_Fish.png" },
  { dockId: "desert", id: "desert_legendary", name: "Dune's Eelworm", iconUrl: "https://static.wikitide.net/shminerwiki/thumb/4/44/Desert_Legendary_Fish.png/45px-Desert_Legendary_Fish.png" },
  { dockId: "tundra", id: "tundra_legendary", name: "Glacial Shellstealer", iconUrl: "https://static.wikitide.net/shminerwiki/thumb/0/06/Tundra_Legendary_Fish.png/45px-Tundra_Legendary_Fish.png" },
  { dockId: "ocean", id: "ocean_legendary", name: "Megalodon", iconUrl: "https://static.wikitide.net/shminerwiki/thumb/3/34/Ocean_Legendary_Fish.png/45px-Ocean_Legendary_Fish.png" },
  { dockId: "nuclear", id: "nuclear_legendary", name: "Radioactive Slug", iconUrl: "https://static.wikitide.net/shminerwiki/thumb/9/9c/Nuclear_Legendary_Fish.png/45px-Nuclear_Legendary_Fish.png" },
  { dockId: "abyss", id: "abyss_legendary", name: "Cthulhu", iconUrl: "https://static.wikitide.net/shminerwiki/thumb/6/6f/Abyss_Legendary_Fish.png/45px-Abyss_Legendary_Fish.png" },
  { dockId: "cave", id: "cave_legendary", name: "Glimmering Geoduck", iconUrl: "https://static.wikitide.net/shminerwiki/thumb/d/d3/Cave_Legendary_Fish.png/45px-Cave_Legendary_Fish.png" },
  { dockId: "volcano", id: "volcano_legendary", name: "Laviathan", iconUrl: "https://static.wikitide.net/shminerwiki/thumb/8/85/Volcano_Legendary_Fish.png/45px-Volcano_Legendary_Fish.png" },
  { dockId: "sky", id: "sky_legendary", name: "Storm Serpent", iconUrl: "https://static.wikitide.net/shminerwiki/thumb/1/11/Sky_Legendary_Fish.png/45px-Sky_Legendary_Fish.png" },
  { dockId: "solaris", id: "solaris_legendary", name: "Melting Gibbous", iconUrl: "https://static.wikitide.net/shminerwiki/thumb/3/35/Solaris_Legendary_Fish.png/45px-Solaris_Legendary_Fish.png" },
  { dockId: "galaxy", id: "galaxy_legendary", name: "Blackened Basker", iconUrl: "https://static.wikitide.net/shminerwiki/thumb/f/f3/Galaxy_Legendary_Fish.png/45px-Galaxy_Legendary_Fish.png" },
];

/** All fish flattened (for lookup by id). */
export const ALL_FISH: FishDef[] = AQUARIUM.flatMap((s) => s.fish);

/** Gem cost to gild a fish card (Card → Gilded). Order matches ALL_FISH: Guppy 1000, Bass 1250, … */
export function getFishCardGildGemCost(fishId: string): number {
  const idx = ALL_FISH.findIndex((f) => f.id === fishId);
  if (idx < 0) return 0;
  return 1000 + idx * 250;
}

/** Card cost to gild Fishing Rod Power misc (Card → Poly). Gild leads to Poly since Poly can be forced quickly. */
export const FISHING_ROD_GILD_CARD_COST = 1500;

export function getFishById(id: string): FishDef | undefined {
  return ALL_FISH.find((f) => f.id === id);
}

/**
 * Polychrome shard odds for fish cards (Polychrome column).
 * Source: https://shminer.miraheze.org/wiki/Cards#Fish_card_odds
 * Tier 1 & 2: 1 in (15000 × 1.1^n) where n = index in ALL_FISH (Guppy=0, …, Wreckshell=23, Stonescale=24, …).
 * Returns the denominator (e.g. 15000 for Guppy). Legendary fish are not in ALL_FISH; returns Infinity.
 */
export function getFishPolyShardOdds(fishId: string): number {
  const idx = ALL_FISH.findIndex((f) => f.id === fishId);
  if (idx < 0) return Infinity;
  return 15000 * Math.pow(1.1, idx);
}

// ——— Upgrades (bought with fish); wiki order and Boat Level (N/A = 0) ———

export const FISHING_UPGRADES_T1: UpgradeDef[] = [
  { id: "fishing_rod", name: "Fishing Rod", perk: "Fishing Rod", iconFile: "Fishing_Rod_Power.png", increasePerLevel: "x1.16", maxLevel: 60, boatLevelRequired: 0, t2BoatLevelRequired: null },
  { id: "fishing_drone", name: "Fishing Drone", perk: "Fishing Drone", iconFile: "Fishing_Drone_Capacity.png", increasePerLevel: "+1", maxLevel: 50, boatLevelRequired: 0, t2BoatLevelRequired: null },
  { id: "upgrade_boat", name: "Upgrade Boat", perk: "Upgrade Boat", iconFile: "Fishing_Boat_Upgrade.png", increasePerLevel: "+1", maxLevel: 5, boatLevelRequired: 0, t2BoatLevelRequired: null },
  { id: "tick_speed", name: "Tick Speed", perk: "Tick Speed", iconFile: "Fishing_Tick_Reduction.png", increasePerLevel: "+0.50s", maxLevel: 40, boatLevelRequired: 1, t2BoatLevelRequired: null },
  { id: "fish_multiplier", name: "Fish Multiplier", perk: "Fish Multiplier", iconFile: "Fish_Income_Multiplier.png", increasePerLevel: "+0.03x", maxLevel: 30, boatLevelRequired: 1, t2BoatLevelRequired: null },
  { id: "rod_multiplier", name: "Rod Multiplier", perk: "Rod Multiplier", iconFile: "Fishing_Rod_Power.png", increasePerLevel: "+0.04x", maxLevel: 20, boatLevelRequired: 2, t2BoatLevelRequired: null },
  { id: "drone_multiplier", name: "Drone Multiplier", perk: "Drone Multiplier", iconFile: "Drone_Power_Multiplier.png", increasePerLevel: "+0.06x", maxLevel: 20, boatLevelRequired: 2, t2BoatLevelRequired: null },
  { id: "double_tick_chance", name: "Double Tick Chance", perk: "Double Tick Chance", iconFile: "Double_Fish_Tick_Chance.png", increasePerLevel: "+0.50%", maxLevel: 30, boatLevelRequired: 3, t2BoatLevelRequired: null },
  { id: "fishing_drone_2", name: "Fishing Drone", perk: "Fishing Drone", iconFile: "Fishing_Drone_Capacity.png", increasePerLevel: "+2", maxLevel: 30, boatLevelRequired: 3, t2BoatLevelRequired: null },
  { id: "shiny_fish_chance", name: "Shiny Fish Chance", perk: "Shiny Fish Chance", iconFile: "Shiny_Fish_Chance.png", increasePerLevel: "+0.50%", maxLevel: 25, boatLevelRequired: 4, t2BoatLevelRequired: null },
  { id: "drone_base_power", name: "Drone Base Power", perk: "Drone Base Power", iconFile: "Fishing_Drone_Base_Power.png", increasePerLevel: "+0.25", maxLevel: 30, boatLevelRequired: 4, t2BoatLevelRequired: null },
  { id: "triple_tick_chance", name: "Triple Tick Chance", perk: "Triple Tick Chance", iconFile: "Triple_Fish_Tick_Chance.png", increasePerLevel: "+0.35%", maxLevel: 25, boatLevelRequired: 4, t2BoatLevelRequired: null },
];

export const FISHING_UPGRADES_T2: UpgradeDef[] = [
  { id: "upgrade_t2_boat", name: "Upgrade Tier 2 Boat", perk: "Upgrade Tier 2 Boat", iconFile: "Fishing_Boat_Upgrade_T2.png", increasePerLevel: "+1", maxLevel: 5, boatLevelRequired: 5, t2BoatLevelRequired: null },
  { id: "shiny_multiplier", name: "Shiny Multiplier", perk: "Shiny Multiplier", iconFile: "Shiny_Multiplier.png", increasePerLevel: "+0.05x", maxLevel: 20, boatLevelRequired: 5, t2BoatLevelRequired: 1 },
  { id: "tier2_dock_power", name: "Tier 2 Dock Power", perk: "Tier 2 Dock Power", iconFile: "Tier_2_Dock_Power.png", increasePerLevel: "+0.05x", maxLevel: 20, boatLevelRequired: 5, t2BoatLevelRequired: 2 },
  { id: "super_shiny_chance", name: "Super Shiny Chance", perk: "Super Shiny Chance", iconFile: "Super_Shiny_Fish_Chance.png", increasePerLevel: "+1%", maxLevel: 20, boatLevelRequired: 5, t2BoatLevelRequired: 3 },
  { id: "poly_card_multi", name: "Poly Card Multi", perk: "Poly Card Multi", iconFile: "Super_Shiny_Multiplier.png", increasePerLevel: "+0.08x", maxLevel: 25, boatLevelRequired: 5, t2BoatLevelRequired: 4 },
  { id: "drone_cloner", name: "Drone Cloner", perk: "Drone Cloner", iconFile: "Fishing_Drone_Cloner.png", increasePerLevel: "1.05x", maxLevel: 30, boatLevelRequired: 5, t2BoatLevelRequired: 5 },
];

// ——— Enhancements (bought with gems; do not count toward completion). Wiki: Enhancements ———

export const ENHANCEMENTS_T1: EnhanceDef[] = [
  { id: "enhance_fish_multiplier", name: "Fish Multiplier", perk: "Fish Multiplier", iconFile: "Fish_Income_Multiplier.png", increasePerLevel: "+0.05x", maxLevel: 255, boatLevelRequired: 0, t2BoatLevelRequired: null },
  { id: "enhance_fishing_drone", name: "Fishing Drone", perk: "Fishing Drone", iconFile: "Fishing_Drone_Capacity.png", increasePerLevel: "+1", maxLevel: 25, boatLevelRequired: 0, t2BoatLevelRequired: null },
  { id: "enhance_rod_multiplier", name: "Rod Multiplier", perk: "Rod Multiplier", iconFile: "Fishing_Rod_Power.png", increasePerLevel: "+0.05x", maxLevel: 20, boatLevelRequired: 0, t2BoatLevelRequired: null },
  { id: "enhance_tick_speed", name: "Tick Speed", perk: "Tick Speed", iconFile: "Fishing_Tick_Reduction.png", increasePerLevel: "-0.5s", maxLevel: 20, boatLevelRequired: 1, t2BoatLevelRequired: null },
  { id: "enhance_drone_multiplier", name: "Drone Multiplier", perk: "Drone Multiplier", iconFile: "Drone_Power_Multiplier.png", increasePerLevel: "+0.08x", maxLevel: 25, boatLevelRequired: 1, t2BoatLevelRequired: null },
  { id: "enhance_token_multiplier", name: "Token Multiplier", perk: "Token Multiplier", iconFile: "Fish_Token_Gain_Multiplier.png", increasePerLevel: "+0.05x", maxLevel: 20, boatLevelRequired: 1, t2BoatLevelRequired: null },
  { id: "enhance_double_tick_chance", name: "Double Tick Chance", perk: "Double Tick Chance", iconFile: "Double_Fish_Tick_Chance.png", increasePerLevel: "+0.5%", maxLevel: 20, boatLevelRequired: 2, t2BoatLevelRequired: null },
  { id: "enhance_tiny_notice_chance", name: "Tiny Notice Chance", perk: "Tiny Notice Chance", iconFile: "Tiny_Notice_Chance.png", increasePerLevel: "+0.5%", maxLevel: 20, boatLevelRequired: 3, t2BoatLevelRequired: null },
  { id: "enhance_shiny_multiplier", name: "Shiny Multiplier", perk: "Shiny Multiplier", iconFile: "Shiny_Multiplier.png", increasePerLevel: "+0.05x", maxLevel: 20, boatLevelRequired: 4, t2BoatLevelRequired: null },
  { id: "enhance_fishing_drone_3", name: "Fishing Drone +3", perk: "Fishing Drone +3", iconFile: "Fishing_Drone_Capacity.png", increasePerLevel: "+3", maxLevel: 20, boatLevelRequired: 5, t2BoatLevelRequired: null },
];

export const ENHANCEMENTS_T2: EnhanceDef[] = [
  { id: "enhance_tier2_dock_ticks", name: "Tier 2 Dock Ticks", perk: "Tier 2 Dock Ticks", iconFile: "Tier_2_Dock_Ticks.png", increasePerLevel: "-1", maxLevel: 10, boatLevelRequired: 5, t2BoatLevelRequired: 1 },
  { id: "enhance_triple_tick_chance", name: "Triple Tick Chance", perk: "Triple Tick Chance", iconFile: "Triple_Fish_Tick_Chance.png", increasePerLevel: "+0.4%", maxLevel: 20, boatLevelRequired: 5, t2BoatLevelRequired: 2 },
  { id: "enhance_super_shiny_multi", name: "Super Shiny Multi", perk: "Super Shiny Multi", iconFile: "Super_Shiny_Multiplier.png", increasePerLevel: "+0.15x", maxLevel: 20, boatLevelRequired: 5, t2BoatLevelRequired: 3 },
  { id: "enhance_tier2_dock_power", name: "Tier 2 Dock Power", perk: "Tier 2 Dock Power", iconFile: "Tier_2_Dock_Power.png", increasePerLevel: "+0.05x", maxLevel: 20, boatLevelRequired: 5, t2BoatLevelRequired: 4 },
  { id: "enhance_poly_card_multi", name: "Poly Card Multi", perk: "Poly Card Multi", iconFile: "Poly_Card_Multi.png", increasePerLevel: "+0.10x", maxLevel: 20, boatLevelRequired: 5, t2BoatLevelRequired: 5 },
];
