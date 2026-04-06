/**
 * Fishing Skill Tree (Obelisk skill points).
 * Source: wiki / user-provided data.
 */

import type { FishingSkillDef } from "./types";

export const FISHING_SKILL_TREE: FishingSkillDef[] = [
  {
    id: "fishing_with_friends",
    name: "Fishing With Friends",
    iconFile: "Fishing_With_Friends.png",
    obeliskLevel: 37,
    effectLines: [
      "Fishing Drones +5",
      "Fishing Drone Power +10%",
      "Fish Multiplier +3%",
    ],
    costs: [40, 50, 63],
  },
  {
    id: "friendship_ended_tier1",
    name: "Friendship Ended With Tier 1 Items",
    iconFile: "Friendship_Ended_With_Tier_1_Items.png",
    statIconFile: "Notice_Fish_Requirement.png",
    obeliskLevel: 37,
    effectLines: [
      "Tier 2 Items From Expert Notices +2",
      "Item Duration +15%",
      "Notice Fish Req -10%",
    ],
    costs: [50, 63, 78],
  },
  {
    id: "motley_school",
    name: "Motley School",
    iconFile: "Motley_School.png",
    obeliskLevel: 50,
    effectLines: [
      "Rod Multiplier +10%",
      "Abyss Dock Tick Req -2",
      "Tier 2 Dock Tick Req -1",
      "Fishing Drones +5",
    ],
    costs: [100, 125, 156],
  },
  {
    id: "lets_pick_up_the_pace",
    name: "Let's Pick Up The Pace",
    iconFile: "Let's_Pick_Up_The_Pace.png",
    obeliskLevel: 37,
    effectLines: [
      "Fishing Tick Speed -2s",
      "Fishing Double Tick Chance +2%",
      "Fishing Triple Tick Chance +1%",
    ],
    costs: [40, 50, 63],
  },
  {
    id: "with_this_fish_i_summon_two_more_fish",
    name: "With This Fish I Summon Two More Fish",
    iconFile: "With_This_Fish_I_Summon_Two_More_Fish.png",
    obeliskLevel: 37,
    effectLines: [
      "+1% Fish Multiplier Per Fish Card",
      "+0.1% Shiny Fish Chance Per Fish Card",
      "(Gilded = 2 Cards, Poly = 3 Cards)",
    ],
    costs: [50, 63, 78],
  },
  {
    id: "completionist_gatekeeper",
    name: "Completionist Gatekeeper",
    iconFile: "Completionist_Gatekeeper.png",
    obeliskLevel: 50,
    effectLines: [
      "Per Legendary Fish Found (1-11):",
      "Tier 2 Dock Power +3%",
      "Fishing Drone Power +2%",
      "Super Shiny Fish Chance +1%",
    ],
    costs: [100, 125, 156],
  },
];
