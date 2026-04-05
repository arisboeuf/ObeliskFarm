/**
 * Fishing upgrade costs (fish) and enhancement costs (gems).
 * Source: https://shminer.miraheze.org/wiki/Fishing#Upgrade_Costs
 *         https://shminer.miraheze.org/wiki/Fishing#Enhancements
 */

import type { EnhanceCostEntry, EnhanceIdT1, EnhanceIdT2, FishingUpgradeId, UpgradeCostEntry } from "./types";

/** Parse wiki cost amount: "10", "4,979", "10.3k", "1.2m" -> number. */
function parseAmount(s: string): number {
  const t = s.replace(/,/g, "").trim();
  if (t.endsWith("k")) return Math.round(parseFloat(t.slice(0, -1)) * 1e3);
  if (t.endsWith("m")) return Math.round(parseFloat(t.slice(0, -1)) * 1e6);
  return Math.round(parseFloat(t) || 0);
}

function cost(level: number, amount: string, fishId: string): UpgradeCostEntry {
  return { level, fishId, amount: parseAmount(amount) };
}

// ——— Tier 1 upgrade costs (fish) ———

const fishing_rod: UpgradeCostEntry[] = [
  cost(1, "10", "guppy"), cost(2, "12", "guppy"), cost(3, "15", "bass"), cost(4, "18", "bass"),
  cost(5, "22", "catfish"), cost(6, "28", "catfish"), cost(7, "34", "golden_trout"), cost(8, "42", "golden_trout"),
  cost(9, "52", "sandscale_carp"), cost(10, "64", "sandscale_carp"), cost(11, "79", "armored_roller"), cost(12, "97", "armored_roller"),
  cost(13, "119", "spiny_puffer"), cost(14, "147", "spiny_puffer"), cost(15, "181", "scarabshoe_crab"), cost(16, "223", "scarabshoe_crab"),
  cost(17, "274", "snow_bellied_swarmer"), cost(18, "337", "snow_bellied_swarmer"), cost(19, "415", "frostshell_crab"), cost(20, "510", "frostshell_crab"),
  cost(21, "628", "frostdrip_spearfish"), cost(22, "772", "frostdrip_spearfish"), cost(23, "950", "auroreel"), cost(24, "1,169", "auroreel"),
  cost(25, "1,437", "coralstar"), cost(26, "1,768", "coralstar"), cost(27, "2,175", "anchorfin_stingray"), cost(28, "2,675", "anchorfin_stingray"),
  cost(29, "3,291", "pearlescent_tetra"), cost(30, "4,048", "pearlescent_tetra"), cost(31, "4,979", "gem_whale"), cost(32, "6,124", "gem_whale"),
  cost(33, "7,532", "ionizing_eel"), cost(34, "9,265", "ionizing_eel"), cost(35, "11.4k", "gammangler_fish"), cost(36, "14.0k", "gammangler_fish"),
  cost(37, "17.2k", "elephants_blob"), cost(38, "21.2k", "elephants_blob"), cost(39, "26.1k", "wastefish"), cost(40, "32.1k", "wastefish"),
  cost(41, "39.5k", "hadal_crusher"), cost(42, "48.5k", "gem_whale"), cost(43, "59.7k", "ionizing_eel"), cost(44, "73.4k", "gammangler_fish"),
  cost(45, "90.3k", "pearlescent_tetra"), cost(46, "111k", "frostdrip_spearfish"), cost(47, "137k", "sandscale_carp"), cost(48, "168k", "gem_whale"),
  cost(49, "207k", "elephants_blob"), cost(50, "254k", "wastefish"), cost(51, "1.56m", "sturgem"), cost(52, "1.92m", "conductive_eel"),
  cost(53, "2.37m", "lava_snail"), cost(54, "2.91m", "obsidian_tooth_barracuda"), cost(55, "3.58m", "cloudcutter_manta"), cost(56, "4.40m", "shocksailfish"),
  cost(57, "5.42m", "ufo"), cost(58, "6.66m", "sub_solar_squid"), cost(59, "8.19m", "gamma_rayburst_shrimp"), cost(60, "10.1m", "galaxia_whale"),
];

const fishing_drone: UpgradeCostEntry[] = [
  cost(1, "12", "bass"), cost(2, "14", "guppy"), cost(3, "17", "bass"), cost(4, "21", "guppy"), cost(5, "26", "catfish"),
  cost(6, "32", "guppy"), cost(7, "39", "catfish"), cost(8, "48", "golden_trout"), cost(9, "58", "sandscale_carp"), cost(10, "71", "armored_roller"),
  cost(11, "87", "bass"), cost(12, "106", "sandscale_carp"), cost(13, "130", "golden_trout"), cost(14, "159", "spiny_puffer"), cost(15, "194", "golden_trout"),
  cost(16, "236", "armored_roller"), cost(17, "289", "scarabshoe_crab"), cost(18, "352", "sandscale_carp"), cost(19, "430", "armored_roller"), cost(20, "524", "spiny_puffer"),
  cost(21, "640", "scarabshoe_crab"), cost(22, "781", "snow_bellied_swarmer"), cost(23, "953", "snow_bellied_swarmer"), cost(24, "1,162", "snow_bellied_swarmer"), cost(25, "1,418", "guppy"),
  cost(26, "1,730", "frostshell_crab"), cost(27, "2,111", "frostshell_crab"), cost(28, "2,575", "frostshell_crab"), cost(29, "3,142", "frostdrip_spearfish"), cost(30, "3,833", "frostdrip_spearfish"),
  cost(31, "4,677", "coralstar"), cost(32, "5,706", "coralstar"), cost(33, "6,961", "coralstar"), cost(34, "8,492", "anchorfin_stingray"), cost(35, "10.4k", "anchorfin_stingray"),
  cost(36, "12.6k", "anchorfin_stingray"), cost(37, "15.4k", "golden_trout"), cost(38, "18.8k", "golden_trout"), cost(39, "23.0k", "golden_trout"), cost(40, "28.0k", "spiny_puffer"),
  cost(41, "34.2k", "spiny_puffer"), cost(42, "41.7k", "spiny_puffer"), cost(43, "50.9k", "ionizing_eel"), cost(44, "62.0k", "golden_trout"), cost(45, "75.7k", "ionizing_eel"),
  cost(46, "92.3k", "scarabshoe_crab"), cost(47, "113k", "ionizing_eel"), cost(48, "137k", "gammangler_fish"), cost(49, "168k", "gammangler_fish"), cost(50, "205k", "gammangler_fish"),
];

const upgrade_boat: UpgradeCostEntry[] = [
  cost(1, "15", "golden_trout"), cost(2, "45", "scarabshoe_crab"), cost(3, "135", "auroreel"), cost(4, "405", "gem_whale"), cost(5, "1,215", "wastefish"),
];

const tick_speed: UpgradeCostEntry[] = [
  cost(1, "40", "bass"), cost(2, "49", "catfish"), cost(3, "61", "golden_trout"), cost(4, "76", "sandscale_carp"), cost(5, "94", "armored_roller"),
  cost(6, "117", "sandscale_carp"), cost(7, "145", "golden_trout"), cost(8, "180", "catfish"), cost(9, "223", "bass"), cost(10, "277", "armored_roller"),
  cost(11, "343", "spiny_puffer"), cost(12, "426", "scarabshoe_crab"), cost(13, "528", "snow_bellied_swarmer"), cost(14, "655", "frostshell_crab"), cost(15, "812", "frostdrip_spearfish"),
  cost(16, "1,007", "frostshell_crab"), cost(17, "1,249", "snow_bellied_swarmer"), cost(18, "1,549", "scarabshoe_crab"), cost(19, "1,921", "frostshell_crab"), cost(20, "2,382", "auroreel"),
  cost(21, "2,954", "coralstar"), cost(22, "3,663", "anchorfin_stingray"), cost(23, "4,542", "pearlescent_tetra"), cost(24, "5,633", "gem_whale"), cost(25, "6,985", "pearlescent_tetra"),
  cost(26, "8,661", "anchorfin_stingray"), cost(27, "10.7k", "coralstar"), cost(28, "13.3k", "auroreel"), cost(29, "16.5k", "frostdrip_spearfish"), cost(30, "20.5k", "frostshell_crab"),
  cost(31, "25.4k", "snow_bellied_swarmer"), cost(32, "31.5k", "scarabshoe_crab"), cost(33, "39.0k", "spiny_puffer"), cost(34, "48.4k", "armored_roller"), cost(35, "60.0k", "sandscale_carp"),
  cost(36, "74.4k", "golden_trout"), cost(37, "92.3k", "catfish"), cost(38, "114k", "bass"), cost(39, "142k", "guppy"), cost(40, "176k", "bass"),
];

const fish_multiplier: UpgradeCostEntry[] = [
  cost(1, "55", "guppy"), cost(2, "68", "bass"), cost(3, "85", "catfish"), cost(4, "107", "golden_trout"), cost(5, "134", "sandscale_carp"),
  cost(6, "167", "armored_roller"), cost(7, "209", "spiny_puffer"), cost(8, "262", "scarabshoe_crab"), cost(9, "327", "guppy"), cost(10, "409", "bass"),
  cost(11, "512", "catfish"), cost(12, "640", "golden_trout"), cost(13, "800", "sandscale_carp"), cost(14, "1,000", "armored_roller"), cost(15, "1,250", "spiny_puffer"),
  cost(16, "1,563", "scarabshoe_crab"), cost(17, "1,953", "guppy"), cost(18, "2,442", "bass"), cost(19, "3,053", "catfish"), cost(20, "3,816", "golden_trout"),
  cost(21, "4,770", "sandscale_carp"), cost(22, "5,963", "armored_roller"), cost(23, "7,453", "spiny_puffer"), cost(24, "9,317", "scarabshoe_crab"), cost(25, "11.6k", "guppy"),
  cost(26, "14.6k", "bass"), cost(27, "18.2k", "catfish"), cost(28, "22.7k", "golden_trout"), cost(29, "28.4k", "sandscale_carp"), cost(30, "35.5k", "armored_roller"),
];

const rod_multiplier: UpgradeCostEntry[] = [
  cost(1, "75", "sandscale_carp"), cost(2, "97", "sandscale_carp"), cost(3, "126", "armored_roller"), cost(4, "164", "armored_roller"), cost(5, "214", "golden_trout"),
  cost(6, "278", "golden_trout"), cost(7, "362", "sandscale_carp"), cost(8, "470", "sandscale_carp"), cost(9, "611", "armored_roller"), cost(10, "795", "armored_roller"),
  cost(11, "1,033", "spiny_puffer"), cost(12, "1,344", "spiny_puffer"), cost(13, "1,747", "snow_bellied_swarmer"), cost(14, "2,271", "snow_bellied_swarmer"), cost(15, "2,953", "snow_bellied_swarmer"),
  cost(16, "3,838", "snow_bellied_swarmer"), cost(17, "4,990", "frostshell_crab"), cost(18, "6,487", "frostshell_crab"), cost(19, "8,434", "frostshell_crab"), cost(20, "11.0k", "frostshell_crab"),
];

const drone_multiplier: UpgradeCostEntry[] = [
  cost(1, "95", "armored_roller"), cost(2, "123", "armored_roller"), cost(3, "160", "spiny_puffer"), cost(4, "208", "spiny_puffer"), cost(5, "271", "snow_bellied_swarmer"),
  cost(6, "352", "snow_bellied_swarmer"), cost(7, "458", "frostshell_crab"), cost(8, "596", "frostshell_crab"), cost(9, "774", "golden_trout"), cost(10, "1,007", "golden_trout"),
  cost(11, "1,309", "scarabshoe_crab"), cost(12, "1,702", "scarabshoe_crab"), cost(13, "2,213", "frostdrip_spearfish"), cost(14, "2,877", "frostdrip_spearfish"), cost(15, "3,740", "snow_bellied_swarmer"),
  cost(16, "4,862", "snow_bellied_swarmer"), cost(17, "6,321", "spiny_puffer"), cost(18, "8,217", "guppy"), cost(19, "10.7k", "golden_trout"), cost(20, "13.9k", "golden_trout"),
];

const double_tick_chance: UpgradeCostEntry[] = [
  cost(1, "125", "snow_bellied_swarmer"), cost(2, "152", "snow_bellied_swarmer"), cost(3, "186", "snow_bellied_swarmer"), cost(4, "226", "frostshell_crab"), cost(5, "276", "frostshell_crab"),
  cost(6, "337", "frostshell_crab"), cost(7, "412", "snow_bellied_swarmer"), cost(8, "502", "snow_bellied_swarmer"), cost(9, "613", "snow_bellied_swarmer"), cost(10, "748", "frostshell_crab"),
  cost(11, "913", "frostshell_crab"), cost(12, "1,113", "frostshell_crab"), cost(13, "1,359", "frostdrip_spearfish"), cost(14, "1,658", "frostdrip_spearfish"), cost(15, "2,022", "frostdrip_spearfish"),
  cost(16, "2,467", "spiny_puffer"), cost(17, "3,010", "spiny_puffer"), cost(18, "3,673", "spiny_puffer"), cost(19, "4,481", "coralstar"), cost(20, "5,466", "coralstar"),
  cost(21, "6,669", "coralstar"), cost(22, "8,137", "anchorfin_stingray"), cost(23, "9,927", "anchorfin_stingray"), cost(24, "12.1k", "anchorfin_stingray"), cost(25, "14.8k", "coralstar"),
  cost(26, "18.0k", "coralstar"), cost(27, "22.0k", "coralstar"), cost(28, "26.8k", "anchorfin_stingray"), cost(29, "32.7k", "guppy"), cost(30, "39.9k", "guppy"),
];

const fishing_drone_2: UpgradeCostEntry[] = [
  cost(1, "145", "guppy"), cost(2, "176", "bass"), cost(3, "215", "catfish"), cost(4, "263", "golden_trout"), cost(5, "321", "sandscale_carp"),
  cost(6, "391", "armored_roller"), cost(7, "478", "spiny_puffer"), cost(8, "583", "scarabshoe_crab"), cost(9, "711", "snow_bellied_swarmer"), cost(10, "868", "frostshell_crab"),
  cost(11, "1,059", "frostdrip_spearfish"), cost(12, "1,292", "auroreel"), cost(13, "1,576", "guppy"), cost(14, "1,923", "bass"), cost(15, "2,346", "catfish"),
  cost(16, "2,862", "golden_trout"), cost(17, "3,492", "sandscale_carp"), cost(18, "4,260", "armored_roller"), cost(19, "5,198", "spiny_puffer"), cost(20, "6,341", "scarabshoe_crab"),
  cost(21, "7,736", "snow_bellied_swarmer"), cost(22, "9,438", "frostshell_crab"), cost(23, "11.5k", "frostdrip_spearfish"), cost(24, "14.0k", "auroreel"), cost(25, "17.1k", "guppy"),
  cost(26, "20.9k", "bass"), cost(27, "25.5k", "catfish"), cost(28, "31.1k", "golden_trout"), cost(29, "38.0k", "sandscale_carp"), cost(30, "46.3k", "armored_roller"),
];

const shiny_fish_chance: UpgradeCostEntry[] = [
  cost(1, "175", "catfish"), cost(2, "215", "spiny_puffer"), cost(3, "264", "frostdrip_spearfish"), cost(4, "325", "catfish"), cost(5, "400", "spiny_puffer"),
  cost(6, "492", "frostdrip_spearfish"), cost(7, "605", "coralstar"), cost(8, "745", "anchorfin_stingray"), cost(9, "916", "frostdrip_spearfish"), cost(10, "1,127", "catfish"),
  cost(11, "1,387", "spiny_puffer"), cost(12, "1,706", "frostdrip_spearfish"), cost(13, "2,098", "spiny_puffer"),
  cost(14, "2,581", "frostdrip_spearfish"), cost(15, "3,174", "pearlescent_tetra"), cost(16, "3,904", "coralstar"), cost(17, "4,803", "guppy"), cost(18, "5,907", "guppy"),
  cost(19, "7,266", "coralstar"), cost(20, "8,937", "frostdrip_spearfish"), cost(21, "11.0k", "pearlescent_tetra"), cost(22, "13.5k", "coralstar"),
  cost(23, "16.6k", "frostdrip_spearfish"), cost(24, "20.5k", "pearlescent_tetra"), cost(25, "25.2k", "coralstar"),
];

const drone_base_power: UpgradeCostEntry[] = [
  cost(1, "205", "guppy"), cost(2, "246", "sandscale_carp"), cost(3, "295", "snow_bellied_swarmer"), cost(4, "354", "coralstar"), cost(5, "425", "guppy"),
  cost(6, "510", "sandscale_carp"), cost(7, "612", "snow_bellied_swarmer"), cost(8, "734", "coralstar"), cost(9, "881", "guppy"), cost(10, "1,057", "sandscale_carp"),
  cost(11, "1,269", "snow_bellied_swarmer"), cost(12, "1,523", "coralstar"), cost(13, "1,827", "guppy"), cost(14, "2,193", "sandscale_carp"), cost(15, "2,632", "snow_bellied_swarmer"),
  cost(16, "3,158", "coralstar"), cost(17, "3,790", "snow_bellied_swarmer"), cost(18, "4,548", "snow_bellied_swarmer"), cost(19, "5,457", "frostshell_crab"), cost(20, "6,549", "frostshell_crab"),
  cost(21, "7,859", "frostdrip_spearfish"), cost(22, "9,431", "frostdrip_spearfish"), cost(23, "11.3k", "auroreel"), cost(24, "13.6k", "auroreel"), cost(25, "16.3k", "coralstar"),
  cost(26, "19.6k", "guppy"), cost(27, "23.5k", "bass"), cost(28, "28.2k", "catfish"), cost(29, "33.8k", "golden_trout"), cost(30, "40.6k", "pearlescent_tetra"),
];

const triple_tick_chance: UpgradeCostEntry[] = [
  cost(1, "245", "golden_trout"), cost(2, "301", "golden_trout"), cost(3, "370", "golden_trout"), cost(4, "455", "scarabshoe_crab"), cost(5, "560", "scarabshoe_crab"),
  cost(6, "689", "scarabshoe_crab"), cost(7, "848", "auroreel"), cost(8, "1,043", "auroreel"), cost(9, "1,283", "auroreel"), cost(10, "1,578", "coralstar"),
  cost(11, "1,941", "coralstar"), cost(12, "2,388", "coralstar"), cost(13, "2,937", "anchorfin_stingray"),
  cost(14, "3,613", "anchorfin_stingray"), cost(15, "4,444", "anchorfin_stingray"), cost(16, "5,466", "pearlescent_tetra"), cost(17, "6,724", "pearlescent_tetra"), cost(18, "8,270", "pearlescent_tetra"),
  cost(19, "10.2k", "ionizing_eel"), cost(20, "12.5k", "ionizing_eel"), cost(21, "15.4k", "gammangler_fish"), cost(22, "18.9k", "gammangler_fish"),
  cost(23, "23.3k", "elephants_blob"), cost(24, "28.6k", "elephants_blob"), cost(25, "35.2k", "elephants_blob"),
];

// ——— Tier 2 upgrade costs ———

const upgrade_t2_boat: UpgradeCostEntry[] = [
  cost(1, "2.00m", "wreckshell_pilferer"), cost(2, "3.00m", "arapaim_al"), cost(3, "4.50m", "basalturtle"), cost(4, "6.75m", "lunar_sunfish"), cost(5, "10.1m", "planetary_jellyfish"),
];

const shiny_multiplier: UpgradeCostEntry[] = [
  cost(1, "215k", "stonescale_carp"), cost(2, "258k", "sturgem"), cost(3, "310k", "conductive_eel"), cost(4, "372k", "arapaim_al"), cost(5, "446k", "stonescale_carp"),
  cost(6, "535k", "sturgem"), cost(7, "642k", "conductive_eel"), cost(8, "770k", "arapaim_al"), cost(9, "924k", "molten_archerfish"), cost(10, "1.11m", "lava_snail"),
  cost(11, "1.33m", "obsidian_tooth_barracuda"), cost(12, "1.60m", "basalturtle"), cost(13, "1.92m", "molten_archerfish"), cost(14, "2.30m", "lava_snail"), cost(15, "2.76m", "obsidian_tooth_barracuda"),
  cost(16, "3.31m", "basalturtle"), cost(17, "3.98m", "cloudcutter_manta"), cost(18, "4.77m", "shocksailfish"), cost(19, "5.72m", "lunar_sunfish"), cost(20, "6.87m", "basalturtle"),
];

const tier2_dock_power: UpgradeCostEntry[] = [
  cost(1, "325k", "molten_archerfish"), cost(2, "390k", "lava_snail"), cost(3, "468k", "obsidian_tooth_barracuda"), cost(4, "562k", "basalturtle"), cost(5, "674k", "stonescale_carp"),
  cost(6, "809k", "sturgem"), cost(7, "970k", "conductive_eel"), cost(8, "1.16m", "arapaim_al"), cost(9, "1.40m", "molten_archerfish"), cost(10, "1.68m", "lava_snail"),
  cost(11, "2.01m", "obsidian_tooth_barracuda"), cost(12, "2.41m", "basalturtle"), cost(13, "2.90m", "sunglazed_flying_fish"), cost(14, "3.48m", "cloudcutter_manta"), cost(15, "4.17m", "shocksailfish"),
  cost(16, "5.01m", "lunar_sunfish"), cost(17, "6.01m", "lanternfish_comet"), cost(18, "7.21m", "ufo"), cost(19, "8.65m", "sub_solar_squid"), cost(20, "10.4m", "planetary_jellyfish"),
];

const super_shiny_chance: UpgradeCostEntry[] = [
  cost(1, "475k", "sunglazed_flying_fish"), cost(2, "570k", "cloudcutter_manta"), cost(3, "684k", "shocksailfish"), cost(4, "821k", "lunar_sunfish"), cost(5, "985k", "sunglazed_flying_fish"),
  cost(6, "1.18m", "cloudcutter_manta"), cost(7, "1.42m", "shocksailfish"), cost(8, "1.70m", "lunar_sunfish"), cost(9, "2.04m", "lanternfish_comet"), cost(10, "2.45m", "ufo"),
  cost(11, "2.94m", "sub_solar_squid"), cost(12, "3.53m", "planetary_jellyfish"), cost(13, "4.24m", "heliocentric_clam"), cost(14, "5.08m", "gamma_rayburst_shrimp"), cost(15, "6.10m", "galaxia_whale"),
  cost(16, "7.32m", "dark_matter_blackdragon"), cost(17, "8.78m", "lunar_sunfish"), cost(18, "10.5m", "lanternfish_comet"), cost(19, "12.6m", "ufo"), cost(20, "15.2m", "sub_solar_squid"),
];

const poly_card_multi: UpgradeCostEntry[] = [
  cost(1, "625k", "lanternfish_comet"), cost(2, "750k", "lanternfish_comet"), cost(3, "900k", "ufo"), cost(4, "1.08m", "ufo"), cost(5, "1.30m", "sub_solar_squid"),
  cost(6, "1.56m", "sub_solar_squid"), cost(7, "1.87m", "planetary_jellyfish"), cost(8, "2.24m", "planetary_jellyfish"), cost(9, "2.69m", "molten_archerfish"), cost(10, "3.22m", "molten_archerfish"),
  cost(11, "3.87m", "lava_snail"), cost(12, "4.64m", "lava_snail"), cost(13, "5.57m", "obsidian_tooth_barracuda"), cost(14, "6.69m", "obsidian_tooth_barracuda"), cost(15, "8.02m", "basalturtle"),
  cost(16, "9.63m", "basalturtle"), cost(17, "11.6m", "planetary_jellyfish"), cost(18, "13.9m", "planetary_jellyfish"), cost(19, "16.6m", "heliocentric_clam"), cost(20, "20.0m", "heliocentric_clam"),
  cost(21, "24.0m", "gamma_rayburst_shrimp"), cost(22, "28.8m", "gamma_rayburst_shrimp"), cost(23, "34.5m", "galaxia_whale"), cost(24, "41.4m", "galaxia_whale"), cost(25, "49.7m", "dark_matter_blackdragon")
];

const drone_cloner: UpgradeCostEntry[] = [
  cost(1, "850k", "lanternfish_comet"), cost(2, "1.02m", "ufo"), cost(3, "1.22m", "sub_solar_squid"), cost(4, "1.47m", "planetary_jellyfish"), cost(5, "1.76m", "sunglazed_flying_fish"),
  cost(6, "2.12m", "cloudcutter_manta"), cost(7, "2.54m", "shocksailfish"), cost(8, "3.05m", "lunar_sunfish"), cost(9, "3.65m", "heliocentric_clam"), cost(10, "4.39m", "gamma_rayburst_shrimp"),
  cost(11, "5.26m", "galaxia_whale"), cost(12, "6.32m", "dark_matter_blackdragon"), cost(13, "7.58m", "heliocentric_clam"), cost(14, "9.09m", "gamma_rayburst_shrimp"), cost(15, "10.9m", "galaxia_whale"),
  cost(16, "13.1m", "dark_matter_blackdragon"), cost(17, "15.7m", "heliocentric_clam"), cost(18, "18.9m", "gamma_rayburst_shrimp"), cost(19, "22.6m", "galaxia_whale"), cost(20, "27.2m", "lunar_sunfish"),
  cost(21, "32.6m", "molten_archerfish"), cost(22, "39.1m", "shocksailfish"), cost(23, "46.9m", "sturgem"), cost(24, "56.3m", "lava_snail"), cost(25, "67.6m", "lunar_sunfish"),
  cost(26, "81.1m", "dark_matter_blackdragon"), cost(27, "97.3m", "heliocentric_clam"), cost(28, "117m", "ufo"), cost(29, "140m", "shocksailfish"), cost(30, "168m", "lanternfish_comet"),
];

/** All upgrade costs by upgrade id (T1 and T2). */
export const UPGRADE_COSTS: Record<FishingUpgradeId, UpgradeCostEntry[]> = {
  fishing_rod,
  fishing_drone,
  upgrade_boat,
  tick_speed,
  fish_multiplier,
  rod_multiplier,
  drone_multiplier,
  double_tick_chance,
  fishing_drone_2,
  shiny_fish_chance,
  drone_base_power,
  triple_tick_chance,
  upgrade_t2_boat,
  shiny_multiplier,
  tier2_dock_power,
  super_shiny_chance,
  poly_card_multi,
  drone_cloner,
};

// ——— Enhancement costs (gems) ———

function gem(level: number, gems: number): EnhanceCostEntry {
  return { level, gems };
}

/** Tier 1 enhance: gem cost per level (wiki tables). */
const enhance_fish_multiplier: EnhanceCostEntry[] = [];
for (let i = 1; i <= 255; i++) enhance_fish_multiplier.push(gem(i, i <= 200 ? 500 + (i - 1) * 500 : 99999));

const enhance_fishing_drone: EnhanceCostEntry[] = [];
for (let i = 1; i <= 25; i++) enhance_fishing_drone.push(gem(i, 750 + (i - 1) * 500));

const enhance_rod_multiplier: EnhanceCostEntry[] = [];
for (let i = 1; i <= 20; i++) enhance_rod_multiplier.push(gem(i, 850 + (i - 1) * 750));

const enhance_tick_speed: EnhanceCostEntry[] = [];
for (let i = 1; i <= 20; i++) enhance_tick_speed.push(gem(i, 1000 + (i - 1) * 750));

const enhance_drone_multiplier: EnhanceCostEntry[] = [];
for (let i = 1; i <= 25; i++) enhance_drone_multiplier.push(gem(i, 1150 + (i - 1) * 850));

const enhance_token_multiplier: EnhanceCostEntry[] = [];
for (let i = 1; i <= 20; i++) enhance_token_multiplier.push(gem(i, 1250 + (i - 1) * 950));

const enhance_double_tick_chance: EnhanceCostEntry[] = [];
for (let i = 1; i <= 20; i++) enhance_double_tick_chance.push(gem(i, 1450 + (i - 1) * 1050));

const enhance_tiny_notice_chance: EnhanceCostEntry[] = [];
for (let i = 1; i <= 20; i++) enhance_tiny_notice_chance.push(gem(i, 1750 + (i - 1) * 1125));

const enhance_shiny_multiplier: EnhanceCostEntry[] = [];
for (let i = 1; i <= 20; i++) enhance_shiny_multiplier.push(gem(i, 1950 + (i - 1) * 1325));

const enhance_fishing_drone_3: EnhanceCostEntry[] = [];
for (let i = 1; i <= 20; i++) enhance_fishing_drone_3.push(gem(i, 2450 + (i - 1) * 1775));

/** Tier 2 enhance. */
const enhance_tier2_dock_ticks: EnhanceCostEntry[] = [];
for (let i = 1; i <= 10; i++) enhance_tier2_dock_ticks.push(gem(i, 15000 + (i - 1) * 5000));

const enhance_triple_tick_chance: EnhanceCostEntry[] = [];
for (let i = 1; i <= 20; i++) enhance_triple_tick_chance.push(gem(i, 4450 + (i - 1) * 3475));

const enhance_super_shiny_multi: EnhanceCostEntry[] = [];
for (let i = 1; i <= 20; i++) enhance_super_shiny_multi.push(gem(i, 5550 + (i - 1) * 4250));

const enhance_tier2_dock_power: EnhanceCostEntry[] = [];
for (let i = 1; i <= 20; i++) enhance_tier2_dock_power.push(gem(i, 7550 + (i - 1) * 4950));

const enhance_poly_card_multi: EnhanceCostEntry[] = [];
for (let i = 1; i <= 20; i++) enhance_poly_card_multi.push(gem(i, 9550 + (i - 1) * 6250));

/** Tier 1 enhancement costs (gems) by enhance id. */
export const ENHANCE_COSTS_T1: Record<EnhanceIdT1, EnhanceCostEntry[]> = {
  enhance_fish_multiplier,
  enhance_fishing_drone,
  enhance_rod_multiplier,
  enhance_tick_speed,
  enhance_drone_multiplier,
  enhance_token_multiplier,
  enhance_double_tick_chance,
  enhance_tiny_notice_chance,
  enhance_shiny_multiplier,
  enhance_fishing_drone_3,
};

/** Tier 2 enhancement costs (gems) by enhance id. */
export const ENHANCE_COSTS_T2: Record<EnhanceIdT2, EnhanceCostEntry[]> = {
  enhance_tier2_dock_ticks,
  enhance_triple_tick_chance,
  enhance_super_shiny_multi,
  enhance_tier2_dock_power,
  enhance_poly_card_multi,
};
