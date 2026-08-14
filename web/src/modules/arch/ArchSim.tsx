import { Fragment, useEffect, useMemo, useRef, useState, type CSSProperties, type ReactNode } from "react";
import { Collapsible } from "../../components/Collapsible";
import { Tooltip, type TooltipContent } from "../../components/Tooltip";
import { assetUrl } from "../../lib/assets";
import { formatInt, formatWithThinSpaces } from "../../lib/format";
import { mulberry32 } from "../../lib/rng";
import { loadJson, saveJson } from "../../lib/storage";
import { BLOCK_COLORS, FRAGMENT_UPGRADES, GEM_COSTS, GEM_UPGRADE_BONUSES, SKILL_BONUSES } from "../../lib/archaeology/constants";
import { archBlockIconPath, BLOCK_CARD_TIERS, BLOCK_TYPES, getBlockData, getCardGemCost } from "../../lib/archaeology/blockStats";
import { computeRunSummary, getBlockBonkerBonus, getCalculationStage, getFragmentUpgradeBonuses, getSkillPointCap, getTotalStats } from "../../lib/archaeology/sim";
import { getGemUpgradeCost, getGemUpgradeMaxLevel, getUpgradeCost } from "../../lib/archaeology/upgradeCosts";
import {
  ascensionLabel,
  buildSkillPointsFromOptimizerDist,
  getBonusSkillPoints,
  getOptimizerSkillBudget,
  getOptimizerStats,
  getTotalSkillPointBudget,
  getUpgradeSnapshotForAscension,
  migrateAscensionUpgradeSnapshots,
  mcOptionsFromBuild,
  normalizeAscensionLevel,
  normalizeOptimizerDistribution,
  optimizerDistArrayToRecord,
  skillPointsFromOptimizerDistRecord,
  switchAscensionUpgrades,
  withSyncedUpgradeSnapshot,
} from "../../lib/archaeology/ascension";
import { formatSkillPointsLine, getSkillDisplay, getVisibleSkills, sanitizeSkillPoints, skillTrimOrder } from "../../lib/archaeology/skills";
import { PERMANENT_SPEED_MOD_INITIAL_HITS } from "../../lib/archaeology/mc/monteCarlo";
import { ARCH_FRAGMENT_TYPES, type ArchBuild, type ArchGemUpgradeKey, type AscensionLevel, type BlockTier, type BlockType, type CardLevel, type Skill } from "../../lib/archaeology/types";

const STORAGE_KEY = "obeliskfarm:web:archaeology_save.json:v1";
const MC_LOG_KEY = "obeliskfarm:web:archaeology_mc_results_log.json:v1";
const MC_SETTINGS_KEY = "obeliskfarm:web:archaeology_mc_settings.json:v1";
const ARCH_EXTERNAL_KEY = "obeliskfarm:web:arch_external.json";

const FRAG_TYPE_SET = new Set<string>(ARCH_FRAGMENT_TYPES);

function emptyFragCounts(): Record<string, number> {
  return Object.fromEntries(ARCH_FRAGMENT_TYPES.map((t) => [t, 0]));
}

function clampInt(n: number, min: number, max: number): number {
  if (!Number.isFinite(n)) return min;
  return Math.max(min, Math.min(max, Math.trunc(n)));
}

/** Standard normal CDF approximation (Abramowitz & Stegun 26.2.17). */
function normalCdf(x: number): number {
  const t = 1 / (1 + 0.2316419 * Math.abs(x));
  const d = 0.3989423 * Math.exp((-x * x) / 2);
  const p = d * t * (0.3193815 + t * (-0.3565638 + t * (1.781478 + t * (-1.821256 + t * 1.330274))));
  return x > 0 ? 1 - p : p;
}

/** Welch t-test two-tailed p-value for H0: μ1 = μ2. Returns p; p < α ⇒ reject (different). */
function welchTTestTwoTailed(
  mean1: number,
  std1: number,
  n1: number,
  mean2: number,
  std2: number,
  n2: number,
): number {
  if (n1 < 2 || n2 < 2 || !Number.isFinite(std1) || !Number.isFinite(std2)) return 1;
  const se1 = std1 / Math.sqrt(n1);
  const se2 = std2 / Math.sqrt(n2);
  const se = Math.sqrt(se1 * se1 + se2 * se2);
  if (se <= 0) return 1;
  const t = Math.abs(mean1 - mean2) / se;
  const v1 = n1 - 1;
  const v2 = n2 - 1;
  const df = (se1 * se1 + se2 * se2) ** 2 / ((se1 * se1 * se1 * se1) / (v1 * v1) + (se2 * se2 * se2 * se2) / (v2 * v2));
  const dfSafe = Math.max(2, Number.isFinite(df) ? df : 100);
  // For large df, t ~ N(0,1). Approximate p ≈ 2*(1 - Φ(t)).
  const p = 2 * (1 - normalCdf(t));
  return Math.max(0, Math.min(1, p));
}

function sampleMeanStd(samples: number[]): { mean: number; std: number; n: number } {
  const n = samples.length;
  if (n === 0) return { mean: 0, std: 0, n: 0 };
  const mean = samples.reduce((a, b) => a + b, 0) / n;
  const variance = samples.reduce((s, x) => s + (x - mean) ** 2, 0) / Math.max(1, n - 1);
  return { mean, std: Math.sqrt(variance), n };
}

type McLogEntry = {
  id: string;
  createdAt: number;
  label: string;
  mcType: "det" | "frag" | "XP" | "stage";
  build: ArchBuild;
  metrics: {
    floorsPerRun: number;
    xpPerRun: number;
    durationSeconds: number;
    fragmentsPerRunTotal: number;
    xpPerHour: number;
    fragmentsPerHour: number;
    /** Std dev of floors/run (final sims). Present when MC computed it. */
    floorsPerRunStd?: number;
    /** Std dev of XP/run (final sims). Present when MC computed it. */
    xpPerRunStd?: number;
    /** Std dev of XP/h (final sims, per-run). Present when MC computed it. */
    xpPerHourStd?: number;
    /** Std dev of Frag/h (final sims, per-run). Present when MC computed it. */
    fragmentsPerHourStd?: number;
    /** Average attacks (hits) per run. Present for MC runs; older saved logs may not have it. */
    attacksPerRun?: number;
    /** Std dev of attacks per run. Present when MC computed it. */
    attacksPerRunStd?: number;
    /** Std dev of run duration (seconds). Present when MC computed it. */
    durationSecondsStd?: number;
    /** Fragments per hour by type (common through divine). Present when MC final sims included per-type data. */
    fragmentsPerHourByType?: Record<string, number>;
    /** Block time distribution (MC only). Time share % per block type, destroyed/run, avg hits/block. */
    blockBreakdown?: import("../../lib/archaeology/mc/monteCarlo").BlockBreakdownAggregate;
  };
  mc?: {
    // Present only for real MC runs
    archLevel: number;
    screeningSims: number;
    refinementSims: number;
    targetFrag?: BlockType;
    objective: "stage" | "XP" | "frag";
    objectiveSamples: number[]; // usually 3000 samples
    /** Avg stamina remaining at end of each stage (stage -> avg). Only for stage objective. */
    avgStaminaAtEndOfStage?: Record<number, number>;
    /** Std dev of stamina at end of each stage (stage -> std). Only for stage objective. */
    stdStaminaAtEndOfStage?: Record<number, number>;
    /** Per-run stamina at end of each stage: staminaAtStageByRun[i] = [stamina at end of stage 1, 2, ..., maxStage[i]]. Used to show stamina for runs that reached a given final stage. */
    staminaAtStageByRun?: number[][];
    tieBreak?: {
      mode: "stage" | "XP" | "frag";
      /** XP optimizer: first tie-break after XP/h is fragments/h vs avg max stage. */
      xpTieBreakSecondary?: "frag_per_hour" | "avg_max_stage";
      epsilon: number;
      primaryMetric: string;
      tiedAtPrimary: number;
      winnerReason: string;
      targetFrag?: BlockType; // for frag mode: primary metric fragment type
      top3: Array<{
        label: string;
        primary: number;
        secondary?: number;
        tertiary?: number;
        /** Frag mode: XP/h for tertiary display. */
        xpPerHour?: number;
        dist: { strength: number; agility: number; perception: number; intellect: number; luck: number; divinity?: number; corruption?: number };
      }>;
    };
  };
};

type TieBreakReport = NonNullable<McLogEntry["mc"]>["tieBreak"];

function winnerStatsFromLogEntry(entry: McLogEntry): Record<Skill, number> {
  const dist = entry.mc?.tieBreak?.top3?.[0]?.dist;
  if (dist) return skillPointsFromOptimizerDistRecord(entry.build, dist);
  return { ...entry.build.skillPoints };
}

export type McComparisonMethodId = "default" | "multiStart3";

type McSettings = {
  targetFrag: BlockType;
  // Developer-only tuning (hidden behind a checkbox in UI)
  devTuning: boolean;
  screeningSims: number;
  refinementSims: number;
  combosMult: number; // multiplier for how many stat distributions are sampled
  // Compare multiple search methods with same budget; each runs in sequence
  comparisonEnabled: boolean;
  comparisonMethods: McComparisonMethodId[];
  // Use statistical tests (Welch t-test, α=0.05) to decide ties instead of fixed 3% threshold
  tieBreakWithSignificance: boolean;
  /** XP optimizer only: first tie-break after XP/h — fragments/h (default) or avg max stage. */
  xpTieBreakSecondary: "frag_per_hour" | "avg_max_stage";
};

function defaultMcSettings(): McSettings {
  return {
    targetFrag: "common",
    devTuning: false,
    screeningSims: 150,
    refinementSims: 150,
    combosMult: 2,
    comparisonEnabled: false,
    comparisonMethods: ["default", "multiStart3"],
    tieBreakWithSignificance: true,
    xpTieBreakSecondary: "frag_per_hour",
  };
}

function Sprite(props: { path: string | null; alt: string; className?: string; label?: string }) {
  const { path, alt, className, label } = props;
  const [ok, setOk] = useState(true);
  if (!path || !ok) return <span className="iconPlaceholder" title={`Missing sprite: ${label ?? alt}`}>?</span>;
  return <img className={className ?? "icon"} src={assetUrl(path)} alt={alt} onError={() => setOk(false)} title={alt} />;
}

function defaultBuild(): ArchBuild {
  const blockCards: Record<string, CardLevel> = {};
  for (const bt of BLOCK_TYPES) {
    for (const tier of BLOCK_CARD_TIERS) {
      if (getBlockData(tier, bt)) blockCards[`${bt},${tier}`] = 0;
    }
  }
  return {
    ascensionLevel: 0,
    goalStage: 1,
    unlockedStage: 1,
    archLevel: 20,
    skillPoints: { strength: 0, agility: 0, perception: 0, intellect: 0, luck: 0, divinity: 0, corruption: 0 },
    gemUpgrades: { stamina: 0, xp: 0, fragment: 0 },
    fragmentUpgradeLevels: {},
    ascensionUpgradeSnapshots: {},
    blockCards,
    miscCardLevel: 0,
    enrageEnabled: true,
    flurryEnabled: true,
    quakeEnabled: true,
    avadaKedaEnabled: false,
    blockBonkerEnabled: false,
    permanentSpeedModEnabled: false,
    axolotlQuestOwned: false,
    axolotlQuestRank: 0,
    level1TributeEnabled: false,
    mythicChestsOwned: 0,
    archBundleEnabled: false,
  };
}

function toggleCardLevel(cur: CardLevel, next: CardLevel): CardLevel {
  return cur === next ? 0 : next;
}

function formatPct(x: number, digits = 2): string {
  return `${(x * 100).toFixed(digits)}%`;
}

/** Format seconds as m:ss (e.g. 272.5 → "4:33"). */
function formatDurationMinSec(sec: number): string {
  const m = Math.floor(sec / 60);
  const s = Math.round(sec % 60);
  return `${m}:${s.toString().padStart(2, "0")}`;
}

function NumberField(props: {
  value: number;
  min: number;
  max: number;
  onCommit: (n: number) => void;
  disabled?: boolean;
  className?: string;
  style?: CSSProperties;
}) {
  const { value, min, max, onCommit, disabled, className, style } = props;
  const [draft, setDraft] = useState<string | null>(null);

  return (
    <input
      className={className ?? "input"}
      type="number"
      inputMode="numeric"
      min={min}
      max={max}
      step={1}
      disabled={disabled}
      style={style}
      value={draft ?? String(value)}
      onChange={(e) => {
        const raw = e.target.value;
        setDraft(raw);
        if (raw.trim() === "") return;
        const n = Number(raw);
        if (Number.isFinite(n)) onCommit(clampInt(n, min, max));
      }}
      onBlur={() => {
        if (draft != null) {
          const n = Number(draft);
          onCommit(draft.trim() === "" || !Number.isFinite(n) ? min : clampInt(n, min, max));
        }
        setDraft(null);
      }}
    />
  );
}

function SkillToggleState({ on }: { on: boolean }) {
  return (
    <span className="mono" style={on ? undefined : { color: "#c62828", fontWeight: 700 }}>
      {on ? "ON" : "OFF"}
    </span>
  );
}

function normalizeSkillsToTotal(sp: Record<Skill, number>, total: number, ascensionLevel: AscensionLevel): Record<Skill, number> {
  const order = skillTrimOrder(ascensionLevel);
  const out: Record<Skill, number> = sanitizeSkillPoints(sp, ascensionLevel);
  let sum = getVisibleSkills(ascensionLevel).reduce((a, k) => a + clampInt(Number(out[k] ?? 0), 0, 999), 0);
  let diff = sum - total;
  let guard = 0;
  while (diff > 0 && guard++ < 10000) {
    let changed = false;
    for (const k of order) {
      if (diff <= 0) break;
      const v = clampInt(Number(out[k] ?? 0), 0, 999);
      if (v > 0) {
        out[k] = v - 1;
        diff -= 1;
        changed = true;
      }
    }
    if (!changed) break;
  }
  return out;
}

export function ArchSim() {
  function sanitizeGemUpgrades(raw: any): ArchBuild["gemUpgrades"] {
    const base = defaultBuild().gemUpgrades;
    const src = (raw && typeof raw === "object") ? raw : {};
    return {
      stamina: clampInt(Number((src as any).stamina ?? base.stamina), 0, 999),
      xp: clampInt(Number((src as any).xp ?? base.xp), 0, 999),
      fragment: clampInt(Number((src as any).fragment ?? base.fragment), 0, 999),
    };
  }

  const [build, setBuild] = useState<ArchBuild>(() => {
    const saved = loadJson<Partial<ArchBuild>>(STORAGE_KEY);
    const base = defaultBuild();
    if (!saved) return base;
    const asc = normalizeAscensionLevel(saved.ascensionLevel, Number(saved.unlockedStage ?? base.unlockedStage));
    const skillPoints = sanitizeSkillPoints({ ...base.skillPoints, ...(saved.skillPoints ?? {}) }, asc);
    const gemUpgrades = sanitizeGemUpgrades(saved.gemUpgrades);
    const ascensionUpgradeSnapshots = migrateAscensionUpgradeSnapshots(saved, asc, gemUpgrades);
    const activeUpgrades = getUpgradeSnapshotForAscension(ascensionUpgradeSnapshots, asc);
    return {
      ...base,
      ...saved,
      ascensionLevel: asc,
      // deep-ish merges:
      skillPoints,
      ascensionUpgradeSnapshots,
      gemUpgrades: { ...activeUpgrades.gemUpgrades },
      fragmentUpgradeLevels: { ...activeUpgrades.fragmentUpgradeLevels },
      blockCards: { ...base.blockCards, ...(saved.blockCards ?? {}) },
    };
  });
  const [mcLog, setMcLog] = useState<McLogEntry[]>(() => loadJson<McLogEntry[]>(MC_LOG_KEY) ?? []);
  const [activeLogId, setActiveLogId] = useState<string | null>(() => {
    const xs = loadJson<McLogEntry[]>(MC_LOG_KEY) ?? [];
    return xs.find((e) => e.mcType !== "det")?.id ?? null;
  });
  const [openLogId, setOpenLogId] = useState<string | null>(null);
  const [mcWindowOpen, setMcWindowOpen] = useState(false);
  const [resetAllArmed, setResetAllArmed] = useState(false);
  const [resetMcLogArmed, setResetMcLogArmed] = useState(false);
  const [deleteLogArmedId, setDeleteLogArmedId] = useState<string | null>(null);
  const [staminaOverviewOpen, setStaminaOverviewOpen] = useState(false);
  const [staminaOverviewStage, setStaminaOverviewStage] = useState<number | null>(null);
  const [mcRunning, setMcRunning] = useState(false);
  const [mcProgress, setMcProgress] = useState<string | null>(null);
  const [mcActiveMode, setMcActiveMode] = useState<null | "frag" | "XP" | "stage">(null);
  const [mcCalibrationMsPer100Sims, setMcCalibrationMsPer100Sims] = useState<number | null>(null);
  const [mcCalibrating, setMcCalibrating] = useState(false);
  const [buildMcN, setBuildMcN] = useState(5000);
  const [buildMcRunning, setBuildMcRunning] = useState(false);
  const [buildMcProgress, setBuildMcProgress] = useState<string | null>(null);
  const [comparisonResult, setComparisonResult] = useState<null | {
    mode: "stage" | "XP" | "frag";
    methodResults: Array<{ methodId: McComparisonMethodId; label: string; build: ArchBuild; primary: number }>;
    winnerId: McComparisonMethodId;
  }>(null);
  const cancelRef = useRef<{ cancelled: boolean; pool: WorkerPool | null }>({ cancelled: false, pool: null });
  const mcCalibratedThisOpenRef = useRef(false);
  const [upgradeNextRefId, setUpgradeNextRefId] = useState<string | null>(null);
  const [upgradeNextRunning, setUpgradeNextRunning] = useState(false);
  const [upgradeNextProgress, setUpgradeNextProgress] = useState<string | null>(null);
  const [upgradeNextResults, setUpgradeNextResults] = useState<Array<{
    key: string;
    displayName: string;
    costType: string;
    meanFloors: number;
    growthPct: number;
    cost: number | null;
    perCost: number | null;
    significant: boolean;
  }> | null>(null);
  const upgradeNextCancelRef = useRef(false);
  const [gemCardSkillNextRunning, setGemCardSkillNextRunning] = useState(false);
  const [gemCardSkillNextProgress, setGemCardSkillNextProgress] = useState<string | null>(null);
  const [gemCardSkillNextResults, setGemCardSkillNextResults] = useState<Array<{
    source: "gem" | "card" | "skill";
    costClass: "gem" | "skill";
    key: string;
    displayName: string;
    meanFloors: number;
    growthPct: number;
    cost: number | undefined;
    perCost: number;
    significant: boolean;
  }> | null>(null);
  const gemCardSkillNextCancelRef = useRef(false);
  const [gemCardSkillNextRefId, setGemCardSkillNextRefId] = useState<string | null>(null);
  const [gemFragNextRunning, setGemFragNextRunning] = useState(false);
  const [gemFragNextProgress, setGemFragNextProgress] = useState<string | null>(null);
  type GemFragCostClass = "gem" | "skill" | "common" | "rare" | "epic" | "legendary" | "mythic" | "divine";
  const [gemFragNextResults, setGemFragNextResults] = useState<Array<{
    source: "gem" | "card" | "skill" | "fragment";
    costClass: GemFragCostClass;
    key: string;
    displayName: string;
    meanFrags: number;
    growthPct: number;
    cost: number | undefined;
    perCost: number;
    allFragmentsGrowthPct: number;
    perCostAllFragments: number;
    significant: boolean;
  }> | null>(null);

  const COLLAPSED_FRAGMENT_GROUPS_KEY = "obeliskfarm:web:arch:collapsedFragmentGroups";
  type FragmentGroupType = "common" | "rare" | "epic" | "legendary" | "mythic" | "divine";
  const [collapsedFragmentGroups, setCollapsedFragmentGroups] = useState<Set<FragmentGroupType>>(() => {
    try {
      const raw = localStorage.getItem(COLLAPSED_FRAGMENT_GROUPS_KEY);
      if (raw) {
        const arr = JSON.parse(raw) as unknown;
        if (Array.isArray(arr) && arr.every((x) => typeof x === "string" && FRAG_TYPE_SET.has(x))) return new Set(arr as FragmentGroupType[]);
      }
    } catch {
      // ignore
    }
    return new Set();
  });
  useEffect(() => {
    try {
      localStorage.setItem(COLLAPSED_FRAGMENT_GROUPS_KEY, JSON.stringify([...collapsedFragmentGroups]));
    } catch {
      // ignore
    }
  }, [collapsedFragmentGroups]);
  function toggleCollapsedFragmentGroup(ct: FragmentGroupType) {
    setCollapsedFragmentGroups((prev) => {
      const next = new Set(prev);
      if (next.has(ct)) next.delete(ct);
      else next.add(ct);
      return next;
    });
  }
  const gemFragNextCancelRef = useRef(false);
  const [gemFragNextRefId, setGemFragNextRefId] = useState<string | null>(null);
  const [mcSettings, setMcSettings] = useState<McSettings>(() => {
    const raw = (loadJson<any>(MC_SETTINGS_KEY) ?? null) as any;
    const base = defaultMcSettings();
    if (!raw) return base;
    return {
      targetFrag: (raw.targetFrag as BlockType) ?? base.targetFrag,
      devTuning: Boolean(raw.devTuning ?? base.devTuning),
      screeningSims: clampInt(Number(raw.screeningSims ?? base.screeningSims), 0, 999999),
      refinementSims: clampInt(Number(raw.refinementSims ?? base.refinementSims), 0, 999999),
      combosMult: clampInt(Number(raw.combosMult ?? base.combosMult), 1, 50),
      comparisonEnabled: Boolean(raw.comparisonEnabled ?? base.comparisonEnabled),
      comparisonMethods: Array.isArray(raw.comparisonMethods)
        ? (raw.comparisonMethods as McComparisonMethodId[]).filter((m) => m === "default" || m === "multiStart3")
        : base.comparisonMethods,
      tieBreakWithSignificance: true, // hidden UI; significance flow always on
      xpTieBreakSecondary:
        raw?.xpTieBreakSecondary === "avg_max_stage" ? "avg_max_stage" : "frag_per_hour",
    };
  });
  function confirmDanger(message: string): boolean {
    try {
      return window.confirm(message);
    } catch {
      return false;
    }
  }

  const TIEBREAK_TOOLTIP = useMemo(
    () => ({
      title: "Tie-break (how ties are resolved)",
      sections: [
        {
          heading: "When scores are considered tied",
          lines: [
            "Statistical tests (Welch t-test, α=0.05) decide who counts as tied: candidates not significantly worse than the best on the primary metric.",
            "No fixed percentage threshold; variance comes from the same MC runs used in screening and refinement.",
          ],
        },
        {
          heading: "Tie-break order",
          lines: ["Primary → Secondary → Tertiary (same logic at each step)."],
        },
        {
          heading: "Metrics by MC mode",
          lines: [
            "Max stage: primary = avg max stage, secondary = fragments/hour, tertiary = XP/hour.",
            "XP/hour: primary = XP/hour. Tie-break order is chosen next to Run MC: fragments/h first then avg max stage, or avg max stage first then fragments/h.",
            "Fragments/hour: primary = target fragment/h. Secondary = next-smaller fragment/h (or next-higher if none). Tertiary = next fragment/h when available; for Mythic only, XP/h is used as tertiary.",
          ],
        },
        {
          heading: "What you see here",
          lines: ["“Tied at primary” = number of candidates not significantly worse than the best on primary.", "“Winner” = why #1 won (tie-break step)."],
        },
      ],
    }),
    [],
  );

  useEffect(() => {
    if (!resetAllArmed) return;
    const t = window.setTimeout(() => setResetAllArmed(false), 4500);
    return () => window.clearTimeout(t);
  }, [resetAllArmed]);

  useEffect(() => {
    if (!resetMcLogArmed) return;
    const t = window.setTimeout(() => setResetMcLogArmed(false), 4500);
    return () => window.clearTimeout(t);
  }, [resetMcLogArmed]);

  useEffect(() => {
    if (openLogId != null) return;
    setStaminaOverviewOpen(false);
    setStaminaOverviewStage(null);
  }, [openLogId]);

  useEffect(() => {
    if (!mcRunning) return;
    setResetAllArmed(false);
    setResetMcLogArmed(false);
    setDeleteLogArmedId(null);
  }, [mcRunning]);

  useEffect(() => {
    if (!deleteLogArmedId) return;
    const t = window.setTimeout(() => setDeleteLogArmedId(null), 4500);
    return () => window.clearTimeout(t);
  }, [deleteLogArmedId]);

  /** Heat relative to own cap: 0/cap = red, cap/cap = green. Same green for 5/5 and 25/25. */
  function heatStyle(level: number, cap: number): CSSProperties {
    const lvl = Math.max(0, Math.trunc(level));
    const capSafe = Math.max(0, Math.trunc(cap));
    const t = capSafe > 0 ? Math.min(1, lvl / capSafe) : 0;
    if (t <= 0) return {};
    const a = Math.max(0.06, Math.min(0.28, 0.06 + t * 0.22));
    const hue = t < 0.5 ? 30 + (60 - 30) * (t / 0.5) : 60 + (120 - 60) * ((t - 0.5) / 0.5);
    const bg = `hsla(${hue.toFixed(1)}, 85%, 70%, ${a.toFixed(3)})`;
    const border = `hsla(${hue.toFixed(1)}, 85%, 38%, 0.35)`;
    return { backgroundColor: bg, borderColor: border };
  }

  /** Red (bad) to green (good) heatmap for pct 0..100 */
  function heatStyleRedGreen(pct: number): CSSProperties {
    const t = Math.max(0, Math.min(100, pct)) / 100;
    const hue = t * 120;
    const bg = `hsla(${hue.toFixed(1)}, 85%, 70%, 0.25)`;
    const border = `hsla(${hue.toFixed(1)}, 85%, 38%, 0.35)`;
    return { backgroundColor: bg, borderColor: border };
  }

  /** Glow relative to own cap: 0/cap = red, cap/cap = green. Pass cap for ratio; if cap <= 0 uses level-only (e.g. skills). */
  function heatGlowStyle(level: number, cap?: number): CSSProperties {
    const lvl = Math.max(0, Math.trunc(level));
    if (lvl <= 0) return { color: "rgba(15,23,42,0.6)" };
    const capSafe = cap != null && cap > 0 ? Math.max(0, Math.trunc(cap)) : 0;
    const t = capSafe > 0 ? Math.min(1, lvl / capSafe) : Math.max(0, Math.min(1, Math.log1p(lvl) / Math.log1p(50)));
    const hue = t < 0.5 ? 30 + (60 - 30) * (t / 0.5) : 60 + (120 - 60) * ((t - 0.5) / 0.5);
    const color = `hsl(${hue.toFixed(1)}, 75%, 35%)`;
    const glow = `0 0 8px hsla(${hue.toFixed(1)}, 75%, 45%, 0.9), 0 0 14px hsla(${hue.toFixed(1)}, 75%, 50%, 0.5), 0 0 22px hsla(${hue.toFixed(1)}, 70%, 55%, 0.3)`;
    return { color, textShadow: glow };
  }

  useEffect(() => {
    const t = window.setTimeout(() => {
      saveJson(STORAGE_KEY, build);
    }, 250);
    return () => window.clearTimeout(t);
  }, [build]);

  useEffect(() => {
    const t = window.setTimeout(() => {
      saveJson(MC_LOG_KEY, mcLog);
    }, 250);
    return () => window.clearTimeout(t);
  }, [mcLog]);

  useEffect(() => {
    const t = window.setTimeout(() => {
      saveJson(MC_SETTINGS_KEY, mcSettings);
    }, 250);
    return () => window.clearTimeout(t);
  }, [mcSettings]);

  const calcStage = useMemo(() => getCalculationStage(build), [build]);
  const computed = useMemo(() => computeRunSummary(build), [build]);
  const stats = computed.stats;
  const summary = computed.summary;
  void summary; // MC-only UI: keep deterministic summary internal, but do not render it.

  const skillPointBudget = useMemo(() => getTotalSkillPointBudget(build), [build.archLevel, build.fragmentUpgradeLevels, build.ascensionLevel, build.ascensionUpgradeSnapshots]);
  const totalSkillPoints = useMemo(
    () => getVisibleSkills(build.ascensionLevel ?? 0).reduce((sum, k) => sum + clampInt(Number(build.skillPoints[k] ?? 0), 0, 999), 0),
    [build.skillPoints, build.ascensionLevel],
  );

  const PLAYER_STATS_TOOLTIP = useMemo(
    () => ({
      title: "Player stats (optional)",
      sections: [
        {
          heading: "What this is",
          lines: ["A read-only view of the build you configured above."],
        },
        {
          heading: "Why it’s optional",
          lines: ["If you only care about the optimizers, you can ignore this section."],
        },
      ],
    }),
    [],
  );

  const SKILLS_TOOLTIP = useMemo(
    () => ({
      title: "Skills",
      sections: [
        {
          heading: "Effect",
          lines: ["These toggles affect the Monte Carlo simulation results."],
        },
        {
          heading: "Avada Keda",
          lines: [
            "Skill tree skill (Obelisk 30, 50 points). When ON: Ability Duration +5 (Enrage/Quake charges), Flurry stamina on cast +5, Ability Cooldown −10 s (Enrage/Flurry/Quake), Ability Instacharge Chance +3%. Instacharge can proc on any ability use and refund it immediately.",
          ],
        },
        {
          heading: "Block Bonker",
          lines: [
            "Skill tree skill. When ON: +N% damage, +N% max stamina, and +N extra speed-mod hits when it procs, where N = Unlocked stage (1–100). Set Unlocked stage to match your in-game unlock.",
          ],
        },
        {
          heading: "Cooldown behavior in MC",
          lines: ["Ability cooldown state can persist between simulated runs inside a batch (cooldowns carry over between successive sims)."],
        },
      ],
    }),
    [],
  );

  const STAT_TOOLTIPS: Record<Skill, TooltipContent> = useMemo(() => {
    const frag = getFragmentUpgradeBonuses(build.fragmentUpgradeLevels);
    const agiSkillBuffLvl = Math.trunc(Number(build.fragmentUpgradeLevels["agi_skill_buff"] ?? 0));
    const perSkillBuffLvl = Math.trunc(Number(build.fragmentUpgradeLevels["per_skill_buff"] ?? 0));
    const intSkillBuffLvl = Math.trunc(Number(build.fragmentUpgradeLevels["int_skill_buff"] ?? 0));

    const modChanceAgi = Number(FRAGMENT_UPGRADES.agi_skill_buff?.mod_chance_skill ?? 0);
    const modChancePer = Number(FRAGMENT_UPGRADES.per_skill_buff?.mod_chance_skill ?? 0);
    const modChanceInt = Number(FRAGMENT_UPGRADES.int_skill_buff?.mod_chance_skill ?? 0);

    function fmtPct(x: number, decimals = 2): string {
      const v = x * 100;
      return decimals <= 0 || v === Math.round(v) ? String(Math.round(v)) : v.toFixed(decimals);
    }
    const boostedByFrag = (
      <>
        {" "}
        <span className="archStatTooltipFrag">
          * Boosted by <Sprite path="sprites/archaeology/fragmentcommon.png" alt="Fragment" className="iconSmall" /> Upgrade
        </span>
      </>
    );
    const strFlatBase = SKILL_BONUSES.strength.flat_damage ?? 0;
    const strFlatActual = strFlatBase + (frag.flat_damage_skill ?? 0);
    const strPctBase = SKILL_BONUSES.strength.percent_damage ?? 0;
    const strPctActual = strPctBase + (frag.percent_damage_skill ?? 0);
    const strCritBase = SKILL_BONUSES.strength.crit_damage ?? 0;

    const agiStamBase = SKILL_BONUSES.agility.max_stamina ?? 0;
    const agiStamActual = agiStamBase + (frag.max_stamina_skill ?? 0);
    const agiCritBase = SKILL_BONUSES.agility.crit_chance ?? 0;
    const agiSpeedBase = SKILL_BONUSES.agility.speed_mod_chance ?? 0;
    const agiSpeedActual = agiSpeedBase + agiSkillBuffLvl * modChanceAgi;

    const perFragBase = SKILL_BONUSES.perception.fragment_gain ?? 0;
    const perLootBase = SKILL_BONUSES.perception.loot_mod_chance ?? 0;
    const perLootActual = perLootBase + perSkillBuffLvl * modChancePer;
    const perArmorBase = SKILL_BONUSES.perception.armor_pen ?? 0;
    const perArmorActual = perArmorBase + (frag.armor_pen_skill ?? 0);

    const intXpBase = SKILL_BONUSES.intellect.xp_bonus ?? 0;
    const intXpActual = intXpBase + (frag.xp_bonus_skill ?? 0);
    const intExpModBase = SKILL_BONUSES.intellect.exp_mod_chance ?? 0;
    const intExpModActual = intExpModBase + intSkillBuffLvl * modChanceInt;
    const intArmorMultBase = SKILL_BONUSES.intellect.armor_pen_mult ?? 0;

    return {
      strength: {
        title: "STR",
        sections: [
          {
            heading: "Per point (actual)",
            lines: [
              <>Damage: +{strFlatActual} flat{strFlatActual !== strFlatBase ? boostedByFrag : null}</>,
              <>Damage: +{fmtPct(strPctActual, 0)}%{strPctActual !== strPctBase ? boostedByFrag : null}</>,
              `Crit Damage: +${fmtPct(strCritBase, 0)}%`,
            ],
          },
        ],
      },
      agility: {
        title: "AGI",
        sections: [
          {
            heading: "Per point (actual)",
            lines: [
              <>Max Stamina: +{agiStamActual}{agiStamActual !== agiStamBase ? boostedByFrag : null}</>,
              `Crit Chance: +${fmtPct(agiCritBase, 0)}%`,
              <>Speed Mod Chance: +{fmtPct(agiSpeedActual)}%{agiSpeedActual !== agiSpeedBase ? boostedByFrag : null}</>,
            ],
          },
        ],
      },
      perception: {
        title: "PER",
        sections: [
          {
            heading: "Per point (actual)",
            lines: [
              `Fragment Gain: +${fmtPct(perFragBase, 0)}%`,
              <>Loot Mod Chance: +{fmtPct(perLootActual)}%{perLootActual !== perLootBase ? boostedByFrag : null}</>,
              <>Armor Penetration: +{perArmorActual}{perArmorActual !== perArmorBase ? boostedByFrag : null}</>,
            ],
          },
        ],
      },
      intellect: {
        title: "INT",
        sections: [
          {
            heading: "Per point (actual)",
            lines: [
              <>Exp Gain: +{fmtPct(intXpActual, 0)}%{intXpActual !== intXpBase ? boostedByFrag : null}</>,
              <>EXP Mod Chance: +{fmtPct(intExpModActual)}%{intExpModActual !== intExpModBase ? boostedByFrag : null}</>,
              `Armor Pen multiplier: ×(1 + ${fmtPct(intArmorMultBase, 0)}% per point)`,
            ],
          },
        ],
      },
      luck: {
        title: "LCK",
        sections: [
          {
            heading: "Per point (actual)",
            lines: [
              `Crit Chance: +${fmtPct(SKILL_BONUSES.luck.crit_chance ?? 0, 0)}%`,
              `All Mod Chances (EXP, Loot, Speed, Stamina): +${fmtPct(SKILL_BONUSES.luck.all_mod_chance ?? 0)}%`,
              "Golden crosshair (active gameplay) is not modeled here.",
            ],
          },
        ],
      },
      divinity: {
        title: "Divinity",
        sections: [
          {
            heading: "Per point",
            lines: [
              `Flat Damage: +${SKILL_BONUSES.divinity.flat_damage ?? 0}`,
              `Super Crit Chance: +${fmtPct(SKILL_BONUSES.divinity.super_crit_chance ?? 0, 0)}%`,
              "Crosshair Auto-Tap is not modeled in the simulator.",
            ],
          },
        ],
      },
      corruption: {
        title: "Corruption",
        sections: [
          {
            heading: "Per point",
            lines: [
              `Damage: +${fmtPct(SKILL_BONUSES.corruption.percent_damage ?? 0, 0)}%`,
              `Max Stamina: ${fmtPct(SKILL_BONUSES.corruption.max_stamina_percent ?? 0, 0)}%`,
              `All Mod Multipliers: +${fmtPct(SKILL_BONUSES.corruption.mod_mult_bonus ?? 0, 0)}%`,
            ],
          },
        ],
      },
    };
  }, [build.fragmentUpgradeLevels]);

  const sortedFragmentUpgrades = useMemo(() => {
    const entries = Object.entries(FRAGMENT_UPGRADES);
    entries.sort((a, b) => {
      const ai = a[1];
      const bi = b[1];
      const sa = Number(ai.stage_unlock ?? 0);
      const sb = Number(bi.stage_unlock ?? 0);
      if (sa !== sb) return sa - sb;
      const ca = String(ai.cost_type ?? "");
      const cb = String(bi.cost_type ?? "");
      if (ca !== cb) return ca.localeCompare(cb);
      return String(ai.display_name ?? a[0]).localeCompare(String(bi.display_name ?? b[0]));
    });
    return entries;
  }, []);

  const fragmentGroups = useMemo(() => {
    const asc = build.ascensionLevel ?? 0;
    const groups: Record<string, Array<[string, any]>> = {};
    for (const [k, info] of sortedFragmentUpgrades) {
      const tier = Number((info as { ascension_tier?: number }).ascension_tier ?? 0);
      if (tier > asc) continue;
      const ct = String((info as any)?.cost_type ?? "misc");
      if (!groups[ct]) groups[ct] = [];
      groups[ct]!.push([k, info]);
    }
    return groups;
  }, [sortedFragmentUpgrades, build.ascensionLevel]);

  // Deterministic recommendation panels removed (MC-only UI).

  function setSkill(skill: Skill, delta: number) {
    setBuild((s) => {
      const visible = getVisibleSkills(s.ascensionLevel ?? 0);
      if (!visible.includes(skill)) return s;
      const cap = getSkillPointCap(s, skill);
      const cur = clampInt(Number(s.skillPoints[skill] ?? 0), 0, cap);
      const otherSum = visible
        .filter((k) => k !== skill)
        .reduce((acc, k) => acc + clampInt(Number(s.skillPoints[k] ?? 0), 0, 999), 0);
      const totalCap = getTotalSkillPointBudget(s);
      const maxForSkillByTotal = Math.max(0, totalCap - otherSum);
      const maxAllowed = Math.min(cap, maxForSkillByTotal);
      const next = clampInt(cur + delta, 0, maxAllowed);
      return { ...s, skillPoints: { ...s.skillPoints, [skill]: next } };
    });
  }

  function setGemUpgrade(key: ArchGemUpgradeKey, delta: number) {
    setBuild((s) => {
      const cur = s.gemUpgrades[key] ?? 0;
      const max = getGemUpgradeMaxLevel(key, s.ascensionLevel ?? 0);
      const next = clampInt(cur + delta, 0, max);
      return withSyncedUpgradeSnapshot(s, { gemUpgrades: { ...s.gemUpgrades, [key]: next } });
    });
  }

  function setFragmentUpgrade(key: string, delta: number) {
    setBuild((s) => {
      const info = FRAGMENT_UPGRADES[key];
      const max = clampInt(Number(info?.max_level ?? 0), 0, 999);
      const cur = clampInt(Number(s.fragmentUpgradeLevels[key] ?? 0), 0, max);
      const next = clampInt(cur + delta, 0, max);
      const copy = { ...s.fragmentUpgradeLevels };
      if (next <= 0) delete copy[key];
      else copy[key] = next;
      return withSyncedUpgradeSnapshot(s, { fragmentUpgradeLevels: copy });
    });
  }

  function setBlockCard(blockType: BlockType, tier: BlockTier, level: CardLevel) {
    const k = `${blockType},${tier}`;
    setBuild((s) => {
      const cur = (s.blockCards[k] ?? 0) as CardLevel;
      return { ...s, blockCards: { ...s.blockCards, [k]: toggleCardLevel(cur, level) } };
    });
  }

  function setMiscCard(level: CardLevel) {
    setBuild((s) => ({ ...s, miscCardLevel: toggleCardLevel(s.miscCardLevel, level) }));
  }

  function setArchLevel(nextLevel: number) {
    setBuild((s) => {
      const lvl = clampInt(nextLevel, 0, 999);
      const normalized = normalizeSkillsToTotal(s.skillPoints, getTotalSkillPointBudget({ ...s, archLevel: lvl }), s.ascensionLevel ?? 0);
      return { ...s, archLevel: lvl, skillPoints: normalized };
    });
  }

  function setAscensionLevel(next: AscensionLevel) {
    setBuild((s) => {
      const asc = normalizeAscensionLevel(next, s.unlockedStage);
      if ((s.ascensionLevel ?? 0) === asc) return s;
      const upgradeSwitch = switchAscensionUpgrades(s, asc);
      const sp = sanitizeSkillPoints({ ...s.skillPoints }, asc);
      const normalized = normalizeSkillsToTotal(
        sp,
        getTotalSkillPointBudget({ ...s, ...upgradeSwitch, ascensionLevel: asc, skillPoints: sp }),
        asc,
      );
      return { ...s, ...upgradeSwitch, ascensionLevel: asc, skillPoints: normalized };
    });
  }

  type WorkerMsg =
    | { type: "stageSummary"; payload: any }
    | { type: "stageSummaryWithVariance"; payload: any }
    | { type: "fragmentSummary"; payload: any }
    | { type: "fragmentSummaryWithVariance"; payload: any }
    | { type: "stageLite"; payload: any }
    | { type: "blockBreakdown"; payload: any };

  type WorkerPool = {
    run: (msg: WorkerMsg) => Promise<any>;
    terminate: () => void;
    size: number;
  };

  function createWorkerPool(size: number): WorkerPool {
    const workers = Array.from({ length: Math.max(1, size) }, () => new Worker(new URL("../../workers/arch_mc.worker.ts", import.meta.url), { type: "module" }));

    type Pending = { msg: WorkerMsg; resolve: (v: any) => void; reject: (e: any) => void };
    const queues: Pending[] = [];
    const busy = new Array(workers.length).fill(false);

    function dispatch() {
      for (let i = 0; i < workers.length; i += 1) {
        if (busy[i]) continue;
        const next = queues.shift();
        if (!next) return;
        busy[i] = true;
        const w = workers[i]!;

        const onMsg = (ev: MessageEvent<any>) => {
          const data = ev.data;
          w.removeEventListener("message", onMsg);
          w.removeEventListener("messageerror", onErr);
          busy[i] = false;
          if (data?.type === "ok") next.resolve(data.payload);
          else next.reject(new Error(data?.payload?.message ?? "Worker error"));
          dispatch();
        };
        const onErr = (ev: MessageEvent<any>) => {
          w.removeEventListener("message", onMsg);
          w.removeEventListener("messageerror", onErr);
          busy[i] = false;
          next.reject(new Error(String(ev?.data ?? "Worker messageerror")));
          dispatch();
        };

        w.addEventListener("message", onMsg);
        w.addEventListener("messageerror", onErr);
        w.postMessage(next.msg);
      }
    }

    return {
      size: workers.length,
      run: (msg) =>
        new Promise((resolve, reject) => {
          queues.push({ msg, resolve, reject });
          dispatch();
        }),
      terminate: () => {
        for (const w of workers) w.terminate();
      },
    };
  }

  function cancelMc() {
    cancelRef.current.cancelled = true;
    cancelRef.current.pool?.terminate();
    cancelRef.current.pool = null;
    setMcRunning(false);
    setMcActiveMode(null);
    setMcProgress("Cancelled.");
  }

  function getPolychromeBonus(): number {
    const lvl = clampInt(Number(build.fragmentUpgradeLevels["polychrome_bonus"] ?? 0), 0, 1);
    return 0.15 * lvl;
  }

  /** Approximate total sim count for current MC params (used for duration estimate). */
  function getEstimatedTotalSims(
    archLevel: number,
    screeningSims: number,
    refinementSims: number,
    combosMult: number,
  ): number {
    const baseSamples = Math.max(500, Math.max(1, archLevel) * 20);
    const nSamples = Math.max(1, Math.trunc(baseSamples * 4 * combosMult));
    const phase1Sims = screeningSims > 0 ? screeningSims : Math.max(1, refinementSims);
    const phase1Total = nSamples * phase1Sims;
    const numAnchorsRaw = Math.max(1, Math.trunc(nSamples * 0.05));
    const perAnchor = clampInt(Math.trunc(refinementSims / 50), 5, 15);
    const phase2Total = numAnchorsRaw * perAnchor * refinementSims;
    return phase1Total + phase2Total + 3100;
  }

  useEffect(() => {
    if (!mcWindowOpen) {
      mcCalibratedThisOpenRef.current = false;
      return;
    }
    if (mcRunning || mcCalibratedThisOpenRef.current) return;
    mcCalibratedThisOpenRef.current = true;
    setMcCalibrating(true);
    const hc = typeof navigator !== "undefined" ? Number((navigator as any).hardwareConcurrency ?? 4) : 4;
    const workerCount = clampInt(Math.max(1, hc - 1), 1, 8);
    const pool = createWorkerPool(workerCount);
    const stats = getTotalStats(build);
    const options = mcOptionsFromBuild(build);
    const cardCfg = { blockCards: build.blockCards, polychromeBonus: getPolychromeBonus() };
    const run100 = () =>
      pool.run({
        type: "stageSummaryWithVariance",
        payload: { stats, starting_floor: 1, n_sims: 100, options, cardCfg, seed: 0 },
      });
    run100()
      .then(() => {
        const t0 = performance.now();
        return run100().then(() => {
          const elapsed = performance.now() - t0;
          pool.terminate();
          setMcCalibrationMsPer100Sims(elapsed);
        });
      })
      .catch(() => {
        pool.terminate();
      })
      .finally(() => {
        setMcCalibrating(false);
      });
  }, [mcWindowOpen, mcRunning]);

  const mcEstimateLabel = useMemo(() => {
    const defaultScreening = 100;
    const defaultRefinement = 200;
    const screeningN = mcSettings.devTuning ? clampInt(Number(mcSettings.screeningSims ?? defaultScreening), 0, 999999) : defaultScreening;
    const refinementN = mcSettings.devTuning ? clampInt(Number(mcSettings.refinementSims ?? defaultRefinement), 0, 999999) : defaultRefinement;
    const combosN = mcSettings.devTuning ? clampInt(Number(mcSettings.combosMult ?? 1), 1, 50) : 1;
    const totalSims = getEstimatedTotalSims(
      clampInt(getOptimizerSkillBudget(build), 0, 999),
      screeningN,
      refinementN,
      combosN,
    );
    const hc = typeof navigator !== "undefined" ? Number((navigator as any).hardwareConcurrency ?? 4) : 4;
    const workerCount = clampInt(Math.max(1, hc - 1), 1, 8);
    const estimateSec =
      mcCalibrationMsPer100Sims != null ? (totalSims * mcCalibrationMsPer100Sims) / (100 * 1000 * workerCount) : null;
    return mcCalibrating ? "Calibrating…" : estimateSec != null ? `Est. ~${Math.round(estimateSec)} s` : "Est. —";
  }, [
    build.ascensionLevel,
    build.fragmentUpgradeLevels,
    mcSettings.devTuning,
    mcSettings.screeningSims,
    mcSettings.refinementSims,
    mcSettings.combosMult,
    mcCalibrationMsPer100Sims,
    mcCalibrating,
  ]);

  function sampleDirichletInteger(args: {
    optimizerSkills: Skill[];
    numPoints: number;
    caps: Partial<Record<Skill, number>>;
    requireStr: boolean;
    rng: () => number;
  }): number[] {
    const { optimizerSkills, numPoints, caps, requireStr, rng } = args;
    // Exponential trick (Dirichlet with alpha=1): sample w_i ~ Exp(1), normalize.
    const w = optimizerSkills.map(() => -Math.log(Math.max(1e-12, rng())));
    const sumW = w.reduce((a, b) => a + b, 0) || 1;
    const raw = w.map((x) => (x / sumW) * numPoints);
    const base = raw.map((x, i) => Math.min(caps[optimizerSkills[i]!] ?? numPoints, Math.max(0, Math.trunc(x))));
    let used = base.reduce((a, b) => a + b, 0);
    let remaining = numPoints - used;

    const frac = raw.map((x, i) => ({ i, f: x - Math.trunc(x) })).sort((a, b) => b.f - a.f);
    let guard = 0;
    while (remaining > 0 && guard++ < 1000) {
      let placed = false;
      for (const it of frac) {
        const sk = optimizerSkills[it.i]!;
        if (base[it.i] < (caps[sk] ?? numPoints)) {
          base[it.i] += 1;
          remaining -= 1;
          placed = true;
          if (remaining <= 0) break;
        }
      }
      if (!placed) break;
    }

    if (requireStr) {
      const strIdx = optimizerSkills.indexOf("strength");
      if (strIdx >= 0 && base[strIdx] <= 0) {
        for (const it of frac) {
          if (it.i === strIdx) continue;
          if (base[it.i] > 0) {
            base[it.i] -= 1;
            base[strIdx] = Math.min(caps.strength ?? numPoints, base[strIdx] + 1);
            break;
          }
        }
      }
    }
    return normalizeOptimizerDistribution({ optimizerSkills, dist: base, numPoints, caps, requireStr, rng });
  }

  function refineAroundAnchor(args: {
    optimizerSkills: Skill[];
    anchor: number[];
    numPoints: number;
    caps: Partial<Record<Skill, number>>;
    radius: number;
    requireStr: boolean;
    rng: () => number;
  }): number[] {
    const { optimizerSkills, anchor, numPoints, caps, radius, requireStr, rng } = args;
    const v = anchor.slice();
    for (let i = 0; i < v.length; i += 1) {
      const d = Math.trunc((rng() * (radius * 2 + 1)) - radius);
      const sk = optimizerSkills[i]!;
      v[i] = clampInt(v[i] + d, 0, caps[sk] ?? numPoints);
    }
    // Fix sum
    let sum = v.reduce((a, b) => a + b, 0);
    let diff = numPoints - sum;
    let guard = 0;
    while (diff !== 0 && guard++ < 5000) {
      const i = Math.trunc(rng() * v.length);
      const sk = optimizerSkills[i]!;
      if (diff > 0) {
        if (v[i] < (caps[sk] ?? numPoints)) {
          v[i] += 1;
          diff -= 1;
        }
      } else {
        if (requireStr && sk === "strength" && v[i] <= 1) continue;
        if (v[i] > 0) {
          v[i] -= 1;
          diff += 1;
        }
      }
    }
    return normalizeOptimizerDistribution({ optimizerSkills, dist: v, numPoints, caps, requireStr, rng });
  }

  type RunMcOpts = { returnResult?: boolean; seedOffset?: number };

  async function runMcOptimizer(mode: "frag" | "XP" | "stage", opts?: RunMcOpts): Promise<null | {
    bestBuild: ArchBuild;
    metrics: McLogEntry["metrics"];
    objectiveSamples: number[];
    tieBreak?: TieBreakReport;
    primary: number;
  }> {
    if (mcRunning && !opts?.returnResult) return null;
    if (!opts?.returnResult) {
      cancelRef.current.cancelled = false;
      setMcActiveMode(mode);
    }
    const hc = typeof navigator !== "undefined" ? Number((navigator as any).hardwareConcurrency ?? 4) : 4;
    const workerCount = clampInt(Math.max(1, hc - 1), 1, 8);
    const pool = createWorkerPool(workerCount);
    cancelRef.current.pool = pool;
    if (!opts?.returnResult) {
      setMcRunning(true);
      setMcProgress("Starting…");
    }

    const statsBudget = getOptimizerSkillBudget(build);
    const optimizerSkills = getOptimizerStats(build.ascensionLevel ?? 0);
    // Always enabled (matches desktop; user should not toggle)
    const defaultScreening = 100;
    const defaultRefinement = 200;
    const screeningSims = mcSettings.devTuning ? clampInt(Number(mcSettings.screeningSims ?? defaultScreening), 0, 999999) : defaultScreening;
    const refinementSims = mcSettings.devTuning ? clampInt(Number(mcSettings.refinementSims ?? defaultRefinement), 0, 999999) : defaultRefinement;
    const combosMult = mcSettings.devTuning ? clampInt(Number(mcSettings.combosMult ?? 1), 1, 50) : 1;
    const targetFrag = mcSettings.targetFrag;
    const FRAG_ORDER: readonly BlockType[] = ARCH_FRAGMENT_TYPES;
    /** For frag mode tie-break: secondary = next-smaller (or next-higher if none); tertiary = next-higher (or over-next-higher if no smaller). */
    function getFragTieBreakFragments(target: BlockType): { secFrag: BlockType | null; terFrag: BlockType | null } {
      const L = FRAG_ORDER.length;
      const idx = FRAG_ORDER.indexOf(target);
      if (idx < 0) return { secFrag: null, terFrag: null };
      const secFrag = idx > 0 ? FRAG_ORDER[idx - 1]! : (idx + 1 < L ? FRAG_ORDER[idx + 1]! : null);
      const terFrag = idx > 0 ? (idx + 1 < L ? FRAG_ORDER[idx + 1]! : null) : (idx + 2 < L ? FRAG_ORDER[idx + 2]! : null);
      return { secFrag, terFrag };
    }

    const caps: Partial<Record<Skill, number>> = {};
    for (const sk of optimizerSkills) {
      caps[sk] = Math.min(statsBudget, getSkillPointCap(build, sk));
    }

    const baseSamples = Math.max(500, Math.max(1, statsBudget) * 20);
    const nSamples = Math.max(1, Math.trunc(baseSamples * 4 * combosMult));
    const topRatio = 0.05;
    const requireStr = true;

    const seedBase = ((Date.now() & 0x7fffffff) >>> 0) + (opts?.seedOffset ?? 0);
    const rng = mulberry32(seedBase);

    const cardCfg = { blockCards: build.blockCards, polychromeBonus: getPolychromeBonus() };
    const options = mcOptionsFromBuild(build);

    type Cand = {
      dist: number[];
      primary: number;
      secondary: number | null;
      tertiary: number | null;
      /** Frag mode: XP/h for tie-break tertiary display. */
      xpPerHour?: number;
      primaryStd?: number;
      primaryN?: number;
      secondaryStd?: number;
      tertiaryStd?: number;
    };
    const scores: Cand[] = [];
    const useSignificance = mcSettings.tieBreakWithSignificance;
    /** XP: after XP/h, compare fragments/h before stage (default) or stage before fragments/h. */
    const xpTieFragFirst = mcSettings.xpTieBreakSecondary !== "avg_max_stage";
    function xpTieMetrics(
      fragsPerHour: number,
      avgMaxStage: number,
      stdFrag?: number,
      stdStage?: number,
    ): { secondary: number; tertiary: number; secondaryStd?: number; tertiaryStd?: number } {
      if (xpTieFragFirst) {
        return { secondary: fragsPerHour, tertiary: avgMaxStage, secondaryStd: stdFrag, tertiaryStd: stdStage };
      }
      return { secondary: avgMaxStage, tertiary: fragsPerHour, secondaryStd: stdStage, tertiaryStd: stdFrag };
    }

    const maxPending = Math.max(2, pool.size * 2);
    let completed = 0;

    const submitCandidate = async (rawDist: number[], simN: number, seed: number) => {
      const dist = normalizeOptimizerDistribution({ optimizerSkills, dist: rawDist, numPoints: statsBudget, caps, requireStr, rng });
      const b2: ArchBuild = { ...build, skillPoints: buildSkillPointsFromOptimizerDist(build, dist) };
      const stats2 = getTotalStats(b2);
      if (mode === "frag") {
        if (useSignificance) {
          const out = await pool.run({
            type: "fragmentSummaryWithVariance",
            payload: { stats: stats2, starting_floor: 1, n_sims: simN, options, cardCfg, seed, target_frag: targetFrag },
          });
          const n = out.n ?? 0;
          const byType = out.frag_per_hour_by_type ?? {};
          const stdByType = (out as { std_by_type?: Record<string, number> }).std_by_type ?? {};
          const { secFrag, terFrag } = getFragTieBreakFragments(targetFrag);
          const secondary = secFrag != null ? (byType[secFrag] ?? 0) : null;
          const tertiary = terFrag != null ? (byType[terFrag] ?? 0) : null;
          scores.push({
            dist,
            primary: out.avg_frag_per_hour ?? 0,
            secondary: secondary ?? null,
            tertiary: tertiary ?? null,
            xpPerHour: out.xp_per_hour ?? 0,
            primaryStd: out.std_frag_per_hour,
            primaryN: n,
            secondaryStd: secFrag != null ? stdByType[secFrag] : undefined,
            tertiaryStd: terFrag != null ? stdByType[terFrag] : undefined,
          });
        } else {
          const out = await pool.run({
            type: "fragmentSummary",
            payload: { stats: stats2, starting_floor: 1, n_sims: simN, options, cardCfg, seed, target_frag: targetFrag },
          });
          const fragPerH = Number(out.avg_frag_per_hour ?? 0);
          const byType = (out as { frag_per_hour_by_type?: Record<string, number> }).frag_per_hour_by_type ?? {};
          const { secFrag, terFrag } = getFragTieBreakFragments(targetFrag);
          const secondary = secFrag != null ? (byType[secFrag] ?? 0) : null;
          const tertiary = terFrag != null ? (byType[terFrag] ?? 0) : null;
          scores.push({
            dist,
            primary: fragPerH,
            secondary: secondary ?? null,
            tertiary: tertiary ?? null,
            xpPerHour: (out as { xp_per_hour?: number }).xp_per_hour ?? 0,
          });
        }
        return;
      }
      if (useSignificance) {
        const out = await pool.run({
          type: "stageSummaryWithVariance",
          payload: { stats: stats2, starting_floor: 1, n_sims: simN, options, cardCfg, seed },
        });
        const avgMaxStage = out.avg_max_stage ?? 0;
        const fragsPerHour = out.fragments_per_hour ?? 0;
        const xpPerHour = out.xp_per_hour ?? 0;
        const n = out.n ?? 0;
        if (mode === "XP") {
          const xm = xpTieMetrics(fragsPerHour, avgMaxStage, out.std_fragments_per_hour, out.std_max_stage);
          scores.push({
            dist,
            primary: xpPerHour,
            secondary: xm.secondary,
            tertiary: xm.tertiary,
            primaryStd: out.std_xp_per_hour,
            primaryN: n,
            secondaryStd: xm.secondaryStd,
            tertiaryStd: xm.tertiaryStd,
          });
        } else {
          scores.push({
            dist,
            primary: avgMaxStage,
            secondary: fragsPerHour,
            tertiary: xpPerHour,
            primaryStd: out.std_max_stage,
            primaryN: n,
            secondaryStd: out.std_fragments_per_hour,
            tertiaryStd: out.std_xp_per_hour,
          });
        }
        return;
      }
      const out = await pool.run({
        type: "stageSummary",
        payload: { stats: stats2, starting_floor: 1, n_sims: simN, options, cardCfg, seed },
      });
      const avgMaxStage = Number(out.avg_max_stage ?? 0);
      const fragsPerHour = Number(out.fragments_per_hour ?? 0);
      const xpPerHour = Number(out.xp_per_hour ?? 0);
      if (mode === "XP") {
        const xm = xpTieMetrics(fragsPerHour, avgMaxStage);
        scores.push({ dist, primary: xpPerHour, secondary: xm.secondary, tertiary: xm.tertiary });
      } else {
        scores.push({ dist, primary: avgMaxStage, secondary: fragsPerHour, tertiary: xpPerHour });
      }
    };

    const EPSILON_PCT = 0.03;
    const epsPct = EPSILON_PCT;

    function makeCompareCand(pool: Cand[]): (a: Cand, b: Cand) => number {
      const maxP = Math.max(0, ...pool.map((c) => c.primary));
      const maxS = Math.max(0, ...pool.map((c) => c.secondary ?? 0));
      const epsP = Math.max(0.01, epsPct * maxP);
      const epsS = maxS > 0 ? Math.max(0.01, epsPct * maxS) : 0.01;
      return (a: Cand, b: Cand) => {
        if (Math.abs(a.primary - b.primary) >= epsP) return b.primary - a.primary;
        const as = a.secondary ?? -Infinity;
        const bs = b.secondary ?? -Infinity;
        if (Math.abs(as - bs) >= epsS) return bs - as;
        const at = a.tertiary ?? -Infinity;
        const bt = b.tertiary ?? -Infinity;
        if (Math.abs(at - bt) >= epsS) return bt - at;
        const aXp = a.xpPerHour ?? -Infinity;
        const bXp = b.xpPerHour ?? -Infinity;
        if (mode === "frag" && (targetFrag === "mythic" || targetFrag === "divine") && (Math.abs(aXp - bXp) >= epsS)) return bXp - aXp;
        return b.primary - a.primary;
      };
    }

    function candToDistMap(dist: number[]) {
      return optimizerDistArrayToRecord(build, dist);
    }

    function makeTieBreakReport(cands: Cand[], best: Cand): TieBreakReport {
      const maxP = Math.max(0, ...cands.map((c) => c.primary));
      const eps = Math.max(0.01, epsPct * maxP);
      const tiedAtPrimary = cands.filter((c) => Math.abs(c.primary - best.primary) < eps).length;
      const hasSecondary = (best.secondary ?? 0) > 0 || cands.some((c) => (c.secondary ?? 0) !== 0);
      const hasTertiary = (best.tertiary ?? 0) > 0 || cands.some((c) => (c.tertiary ?? 0) !== 0);
      const primaryMetric = mode === "stage" ? "avg_max_stage" : mode === "XP" ? "xp_per_hour" : "frag_per_hour";
      let winnerReason = "highest primary score";
      if (tiedAtPrimary > 1 && mode === "XP") {
        const tail = xpTieFragFirst
          ? hasTertiary
            ? "tie-break by fragments/h then avg max stage"
            : hasSecondary
              ? "tie-break by fragments/h"
              : "tie-break (lexicographic)"
          : hasTertiary
            ? "tie-break by avg max stage then fragments/h"
            : hasSecondary
              ? "tie-break by avg max stage"
              : "tie-break (lexicographic)";
        winnerReason = `primary tied → ${tail}`;
      } else if (tiedAtPrimary > 1 && mode === "stage") {
        const tail = hasTertiary ? "tie-break by secondary then tertiary" : hasSecondary ? "tie-break by secondary" : "tie-break (lexicographic)";
        winnerReason = `primary tied → ${tail}`;
      } else if (tiedAtPrimary > 1 && mode === "frag") {
        const { secFrag, terFrag } = getFragTieBreakFragments(targetFrag);
        const secLabel = secFrag != null ? secFrag.toUpperCase() : null;
        const terLabel = terFrag != null ? terFrag.toUpperCase() : null;
        const hasXp =
          (targetFrag === "mythic" || targetFrag === "divine") && ((best.xpPerHour ?? 0) > 0 || cands.some((c) => (c.xpPerHour ?? 0) > 0));
        const tail =
          hasTertiary && secLabel && terLabel
            ? `tie-break by ${secLabel}/h then ${terLabel}/h`
            : hasSecondary && secLabel
              ? hasXp
                ? `tie-break by ${secLabel}/h then XP/h`
                : `tie-break by ${secLabel}/h`
              : hasXp
                ? "tie-break by XP/h"
                : "tie-break (lexicographic)";
        winnerReason = `primary tied → ${tail}`;
      }
      const top3 = cands.slice(0, 3).map((c, i) => ({
        label: `#${i + 1}`,
        primary: c.primary,
        secondary: c.secondary ?? undefined,
        tertiary: c.tertiary ?? undefined,
        ...(mode === "frag" ? { xpPerHour: c.xpPerHour ?? undefined } : {}),
        dist: candToDistMap(c.dist),
      }));
      return {
        mode,
        epsilon: eps,
        primaryMetric,
        tiedAtPrimary,
        winnerReason,
        ...(mode === "frag" ? { targetFrag } : {}),
        ...(mode === "XP" ? { xpTieBreakSecondary: xpTieFragFirst ? ("frag_per_hour" as const) : ("avg_max_stage" as const) } : {}),
        top3,
      };
    }

    try {
      if (statsBudget <= 0) throw new Error("Arch level must be >= 1.");

      // If both screening+refinement are off, just run final sims on current build.
      if (screeningSims <= 0 && refinementSims <= 0) {
        setMcProgress("Final sims (3000) on current build…");

        const bestBuild = build;
        const bestStats = getTotalStats(bestBuild);
        const totalFinal = 3000;
        const chunkSize = clampInt(Math.trunc(totalFinal / Math.max(1, pool.size * 4)), 10, 100);
        let remaining = totalFinal;
        let done = 0;

        const objectiveSamples: number[] = [];
        let sumFloors = 0;
        let sumFloorsSq = 0;
        let sumXp = 0;
        let sumXpSq = 0;
        let sumTotalFrags = 0;
        let sumDur = 0;
        let sumDurSq = 0;
        let sumHits = 0;
        let sumHitsSq = 0;
        let sumXph = 0;
        let sumXphSq = 0;
        let sumFph = 0;
        let sumFphSq = 0;
        let sampleCount = 0;
        const sumFragsByType: Record<string, number> = emptyFragCounts();
        const FRAG_TYPES_STAGE = ARCH_FRAGMENT_TYPES;
        const staminaAtStageSum: Record<number, number> = {};
        const staminaAtStageSumSq: Record<number, number> = {};
        const staminaAtStageCount: Record<number, number> = {};

        const tasks: Promise<void>[] = [];
        let submitted = 0;
        while (remaining > 0) {
          if (cancelRef.current.cancelled) throw new Error("cancelled");
          const n = Math.min(chunkSize, remaining);
          submitted += 1;
          const seed = seedBase + 1_000_000 + submitted;
          const t = pool
            .run({
              type: "stageLite",
              payload: { stats: bestStats, starting_floor: 1, n_sims: n, options, cardCfg, seed, targetFrag: mode === "frag" ? targetFrag : null, initialSpeedModHits: build.permanentSpeedModEnabled ? PERMANENT_SPEED_MOD_INITIAL_HITS : undefined },
            })
            .then((out) => {
              const dur: number[] = out.run_duration_seconds_samples ?? [];
              const xp: number[] = out.xp_per_run_samples ?? [];
              const maxs: number[] = out.max_stage_samples ?? [];
              const floors: number[] = out.floors_cleared_samples ?? [];
              const totals: number[] = out.total_fragments_samples ?? [];
              const hits: number[] = (out as { total_hits_samples?: number[] }).total_hits_samples ?? [];
              const targ: number[] = out.target_frag_samples ?? [];
              const runFragsByType = (out as { run_fragments_by_type?: Record<string, number[]> }).run_fragments_by_type ?? {};
              for (let i = 0; i < dur.length; i += 1) {
                const d = Number(dur[i] ?? 1);
                const runsPerHour = d > 0 ? 3600.0 / d : 0;
                if (mode === "XP") objectiveSamples.push(Number(xp[i] ?? 0) * runsPerHour);
                else if (mode === "frag") objectiveSamples.push(Number(targ[i] ?? 0) * runsPerHour);
                else objectiveSamples.push(Number(maxs[i] ?? 0));

                sumDur += d;
                sumDurSq += d * d;
                const xpVal = Number(xp[i] ?? 0);
                const flVal = Number(floors[i] ?? 0);
                const totVal = Number(totals[i] ?? 0);
                sumXp += xpVal;
                sumXpSq += xpVal * xpVal;
                sumFloors += flVal;
                sumFloorsSq += flVal * flVal;
                sumTotalFrags += totVal;
                const xph = xpVal * runsPerHour;
                const fph = totVal * runsPerHour;
                sumXph += xph;
                sumXphSq += xph * xph;
                sumFph += fph;
                sumFphSq += fph * fph;
                const h = Number(hits[i] ?? 0);
                sumHits += h;
                sumHitsSq += h * h;
                for (const k of FRAG_TYPES_STAGE) sumFragsByType[k] += Number(runFragsByType[k]?.[i] ?? 0);
                sampleCount += 1;
              }
              if (mode === "stage") {
                const sum = (out as { stamina_at_stage_sum?: Record<number, number> }).stamina_at_stage_sum;
                const sumSq = (out as { stamina_at_stage_sum_sq?: Record<number, number> }).stamina_at_stage_sum_sq;
                const cnt = (out as { stamina_at_stage_count?: Record<number, number> }).stamina_at_stage_count;
                if (sum) for (const [s, v] of Object.entries(sum)) { const k = Math.trunc(Number(s)); staminaAtStageSum[k] = (staminaAtStageSum[k] ?? 0) + Number(v); }
                if (sumSq) for (const [s, v] of Object.entries(sumSq)) { const k = Math.trunc(Number(s)); staminaAtStageSumSq[k] = (staminaAtStageSumSq[k] ?? 0) + Number(v); }
                if (cnt) for (const [s, v] of Object.entries(cnt)) { const k = Math.trunc(Number(s)); staminaAtStageCount[k] = (staminaAtStageCount[k] ?? 0) + Number(v); }
              }
              done += n;
              setMcProgress(`Final sims (${done}/${totalFinal})`);
            });
          tasks.push(t);
          remaining -= n;
        }
        await Promise.all(tasks);
        if (cancelRef.current.cancelled) throw new Error("cancelled");

        let blockBreakdownEarly: McLogEntry["metrics"]["blockBreakdown"] = undefined;
        try {
          setMcProgress("Block breakdown…");
          const bb = await pool.run({
            type: "blockBreakdown",
            payload: { stats: bestStats, starting_floor: 1, n_sims: 100, options, cardCfg, seed: seedBase + 999_999 },
          });
          if (bb?.by_type && Object.keys(bb.by_type).length > 0) blockBreakdownEarly = bb;
        } catch {
          /* non-fatal */
        }

        if (cancelRef.current.cancelled) throw new Error("cancelled");

        const avgFloors = sampleCount > 0 ? sumFloors / sampleCount : 0;
        const avgXp = sampleCount > 0 ? sumXp / sampleCount : 0;
        const avgTotalFrags = sampleCount > 0 ? sumTotalFrags / sampleCount : 0;
        const avgDur = sampleCount > 0 ? sumDur / sampleCount : 1;
        const avgAttacksPerRun = sampleCount > 0 ? sumHits / sampleCount : 0;
        const varianceDur = sampleCount > 1 ? Math.max(0, sumDurSq / sampleCount - avgDur * avgDur) : 0;
        const durationSecondsStd = sampleCount > 1 ? Math.sqrt(varianceDur) : undefined;
        const varianceHits = sampleCount > 1 ? Math.max(0, sumHitsSq / sampleCount - avgAttacksPerRun * avgAttacksPerRun) : 0;
        const attacksPerRunStd = sampleCount > 1 ? Math.sqrt(varianceHits) : undefined;
        const meanFloors = sampleCount > 0 ? sumFloors / sampleCount : 0;
        const varianceFloors = sampleCount > 1 ? Math.max(0, sumFloorsSq / sampleCount - meanFloors * meanFloors) : 0;
        const floorsPerRunStd = sampleCount > 1 ? Math.sqrt(varianceFloors) : undefined;
        const varianceXp = sampleCount > 1 ? Math.max(0, sumXpSq / sampleCount - avgXp * avgXp) : 0;
        const xpPerRunStd = sampleCount > 1 ? Math.sqrt(varianceXp) : undefined;
        const meanXph = sampleCount > 0 ? sumXph / sampleCount : 0;
        const varianceXph = sampleCount > 1 ? Math.max(0, sumXphSq / sampleCount - meanXph * meanXph) : 0;
        const xpPerHourStd = sampleCount > 1 ? Math.sqrt(varianceXph) : undefined;
        const meanFph = sampleCount > 0 ? sumFph / sampleCount : 0;
        const varianceFph = sampleCount > 1 ? Math.max(0, sumFphSq / sampleCount - meanFph * meanFph) : 0;
        const fragmentsPerHourStd = sampleCount > 1 ? Math.sqrt(varianceFph) : undefined;
        let xpPerHour = avgDur > 0 ? (avgXp * 3600.0) / avgDur : 0;
        let fragmentsPerHour = avgDur > 0 ? (avgTotalFrags * 3600.0) / avgDur : 0;
        const fragmentsPerHourByType: Record<string, number> = {};
        if (sumDur > 0) for (const k of FRAG_TYPES_STAGE) fragmentsPerHourByType[k] = (sumFragsByType[k] ?? 0) * (3600.0 / sumDur);
        const archExt = loadJson<{ lootbugArch600AttacksPerHour?: number }>(ARCH_EXTERNAL_KEY) ?? {};
        const lootbugAttacks = typeof archExt?.lootbugArch600AttacksPerHour === "number" ? archExt.lootbugArch600AttacksPerHour : 0;
        if (lootbugAttacks > 0 && bestStats.max_stamina > 0) {
          const extraRunsPerHour = lootbugAttacks / bestStats.max_stamina;
          xpPerHour += extraRunsPerHour * avgXp;
          fragmentsPerHour += extraRunsPerHour * avgTotalFrags;
          if (sampleCount > 0) for (const k of FRAG_TYPES_STAGE) fragmentsPerHourByType[k] = (fragmentsPerHourByType[k] ?? 0) + extraRunsPerHour * ((sumFragsByType[k] ?? 0) / sampleCount);
        }

        const avgStaminaAtEndOfStage: Record<number, number> = {};
        const stdStaminaAtEndOfStage: Record<number, number> = {};
        if (mode === "stage") {
          for (const s of Object.keys(staminaAtStageSum)) {
            const stage = Math.trunc(Number(s));
            const cnt = staminaAtStageCount[stage] ?? 0;
            if (cnt > 0) {
              const sum = staminaAtStageSum[stage] ?? 0;
              const sumSq = staminaAtStageSumSq[stage] ?? 0;
              avgStaminaAtEndOfStage[stage] = sum / cnt;
              if (cnt > 1) {
                const variance = Math.max(0, sumSq / cnt - (sum / cnt) ** 2);
                stdStaminaAtEndOfStage[stage] = Math.sqrt(variance);
              }
            }
          }
        }
        const entry: McLogEntry = {
          id: `mc_${Date.now()}_${Math.random().toString(16).slice(2)}`,
          createdAt: Date.now(),
          label:
            mode === "frag"
              ? `MC Fragment Farmer (${targetFrag.toUpperCase()})`
              : mode === "XP"
                ? "MC XP Optimizer"
                : "MC Stage Push Optimizer",
          mcType: mode,
          build: bestBuild,
          metrics: {
            floorsPerRun: avgFloors,
            xpPerRun: avgXp,
            durationSeconds: avgDur,
            durationSecondsStd,
            fragmentsPerRunTotal: avgTotalFrags,
            xpPerHour,
            fragmentsPerHour,
            floorsPerRunStd,
            xpPerRunStd,
            xpPerHourStd,
            fragmentsPerHourStd,
            attacksPerRun: avgAttacksPerRun,
            attacksPerRunStd,
            fragmentsPerHourByType,
            blockBreakdown: blockBreakdownEarly,
          },
          mc: {
            archLevel: statsBudget,
            screeningSims,
            refinementSims,
            targetFrag: mode === "frag" ? targetFrag : undefined,
            objective: mode,
            objectiveSamples,
            ...(Object.keys(avgStaminaAtEndOfStage).length > 0
              ? { avgStaminaAtEndOfStage, stdStaminaAtEndOfStage: Object.keys(stdStaminaAtEndOfStage).length > 0 ? stdStaminaAtEndOfStage : undefined }
              : {}),
          },
        };
        if (opts?.returnResult) {
          const primary =
            objectiveSamples.length > 0 ? objectiveSamples.reduce((a, b) => a + b, 0) / objectiveSamples.length : 0;
          return { bestBuild: entry.build, metrics: entry.metrics, objectiveSamples, primary };
        }
        setMcLog((xs) => [entry, ...xs]);
        setActiveLogId(entry.id);
        setMcProgress("Done.");
        return null;
      }

      const phase1Sims = screeningSims > 0 ? screeningSims : Math.max(1, refinementSims);
      setMcProgress(`Phase 1: Search (${nSamples} samples, N=${phase1Sims})…`);
      const inFlight = new Set<Promise<void>>();
      for (let i = 0; i < nSamples; i += 1) {
        if (cancelRef.current.cancelled) throw new Error("cancelled");
        const dist = sampleDirichletInteger({ optimizerSkills, numPoints: statsBudget, caps, requireStr, rng });
        const p = submitCandidate(dist, phase1Sims, seedBase + i).then(() => {
          completed += 1;
          if (completed % 10 === 0 || completed === nSamples) setMcProgress(`Phase 1: Search (${completed}/${nSamples})`);
        });
        inFlight.add(p);
        p.finally(() => inFlight.delete(p)).catch(() => {});
        if (inFlight.size >= maxPending) await Promise.race(inFlight);
      }
      await Promise.allSettled(Array.from(inFlight));

      if (cancelRef.current.cancelled) throw new Error("cancelled");
      scores.sort(makeCompareCand(scores));
      const numAnchorsRaw = Math.max(1, Math.trunc(scores.length * topRatio));
      let anchors: Cand[];
      if (useSignificance && scores[0]) {
        const bestScore = scores[0];
        const advance = scores.filter(
          (c) =>
            c.primaryStd != null &&
            c.primaryN != null &&
            bestScore.primaryStd != null &&
            bestScore.primaryN != null &&
            welchTTestTwoTailed(
              bestScore.primary,
              bestScore.primaryStd,
              bestScore.primaryN,
              c.primary,
              c.primaryStd,
              c.primaryN,
            ) >= 0.05,
        );
        anchors = advance.slice(0, numAnchorsRaw);
      } else {
        anchors = scores.slice(0, numAnchorsRaw);
      }
      const numAnchors = anchors.length;

      let best: Cand | undefined = scores[0];
      let bestPool: Cand[] = scores;
      if (refinementSims > 0) {
        setMcProgress(`Phase 2: Refinement (${numAnchors} anchors, N=${refinementSims})…`);
        const refined: Cand[] = [];
        const perAnchor = clampInt(Math.trunc(refinementSims / 50), 5, 15);
        const radius = 2;
        completed = 0;
        const totalRef = numAnchors * perAnchor;
        const inFlight2 = new Set<Promise<void>>();
        for (let a = 0; a < anchors.length; a += 1) {
          for (let j = 0; j < perAnchor; j += 1) {
            if (cancelRef.current.cancelled) throw new Error("cancelled");
            const dist = refineAroundAnchor({ optimizerSkills, anchor: anchors[a]!.dist, numPoints: statsBudget, caps, radius, requireStr, rng });
            const p = (async () => {
              const b2: ArchBuild = { ...build, skillPoints: buildSkillPointsFromOptimizerDist(build, dist) };
              const stats2 = getTotalStats(b2);
              const seedRef = seedBase + 100_000 + a * 100 + j;
              if (mode === "frag") {
                if (useSignificance) {
                  const out = await pool.run({
                    type: "fragmentSummaryWithVariance",
                    payload: { stats: stats2, starting_floor: 1, n_sims: refinementSims, options, cardCfg, seed: seedRef, target_frag: targetFrag },
                  });
                  const n = out.n ?? 0;
                  const byType = out.frag_per_hour_by_type ?? {};
                  const stdByType = (out as { std_by_type?: Record<string, number> }).std_by_type ?? {};
                  const { secFrag, terFrag } = getFragTieBreakFragments(targetFrag);
                  const secondary = secFrag != null ? (byType[secFrag] ?? 0) : null;
                  const tertiary = terFrag != null ? (byType[terFrag] ?? 0) : null;
                  refined.push({
                    dist,
                    primary: out.avg_frag_per_hour ?? 0,
                    secondary: secondary ?? null,
                    tertiary: tertiary ?? null,
                    xpPerHour: out.xp_per_hour ?? 0,
                    primaryStd: out.std_frag_per_hour,
                    primaryN: n,
                    secondaryStd: secFrag != null ? stdByType[secFrag] : undefined,
                    tertiaryStd: terFrag != null ? stdByType[terFrag] : undefined,
                  });
                } else {
                  const out = await pool.run({
                    type: "fragmentSummary",
                    payload: { stats: stats2, starting_floor: 1, n_sims: refinementSims, options, cardCfg, seed: seedRef, target_frag: targetFrag },
                  });
                  const fragPerH = Number(out.avg_frag_per_hour ?? 0);
                  const byType = (out as { frag_per_hour_by_type?: Record<string, number> }).frag_per_hour_by_type ?? {};
                  const { secFrag, terFrag } = getFragTieBreakFragments(targetFrag);
                  const secondary = secFrag != null ? (byType[secFrag] ?? 0) : null;
                  const tertiary = terFrag != null ? (byType[terFrag] ?? 0) : null;
                  refined.push({
                    dist,
                    primary: fragPerH,
                    secondary: secondary ?? null,
                    tertiary: tertiary ?? null,
                    xpPerHour: (out as { xp_per_hour?: number }).xp_per_hour ?? 0,
                  });
                }
                return;
              }
              if (useSignificance) {
                const out = await pool.run({
                  type: "stageSummaryWithVariance",
                  payload: { stats: stats2, starting_floor: 1, n_sims: refinementSims, options, cardCfg, seed: seedRef },
                });
                const avgMaxStage = out.avg_max_stage ?? 0;
                const fragsPerHour = out.fragments_per_hour ?? 0;
                const xpPerHour = out.xp_per_hour ?? 0;
                const n = out.n ?? 0;
                if (mode === "XP") {
                  const xm = xpTieMetrics(fragsPerHour, avgMaxStage, out.std_fragments_per_hour, out.std_max_stage);
                  refined.push({
                    dist,
                    primary: xpPerHour,
                    secondary: xm.secondary,
                    tertiary: xm.tertiary,
                    primaryStd: out.std_xp_per_hour,
                    primaryN: n,
                    secondaryStd: xm.secondaryStd,
                    tertiaryStd: xm.tertiaryStd,
                  });
                } else {
                  refined.push({
                    dist,
                    primary: avgMaxStage,
                    secondary: fragsPerHour,
                    tertiary: xpPerHour,
                    primaryStd: out.std_max_stage,
                    primaryN: n,
                    secondaryStd: out.std_fragments_per_hour,
                    tertiaryStd: out.std_xp_per_hour,
                  });
                }
                return;
              }
              const out = await pool.run({
                type: "stageSummary",
                payload: { stats: stats2, starting_floor: 1, n_sims: refinementSims, options, cardCfg, seed: seedRef },
              });
              const avgMaxStage = Number(out.avg_max_stage ?? 0);
              const fragsPerHour = Number(out.fragments_per_hour ?? 0);
              const xpPerHour = Number(out.xp_per_hour ?? 0);
              if (mode === "XP") {
                const xm = xpTieMetrics(fragsPerHour, avgMaxStage);
                refined.push({ dist, primary: xpPerHour, secondary: xm.secondary, tertiary: xm.tertiary });
              } else refined.push({ dist, primary: avgMaxStage, secondary: fragsPerHour, tertiary: xpPerHour });
            })().then(() => {
              completed += 1;
              if (completed % 10 === 0 || completed === totalRef) setMcProgress(`Phase 2: Refinement (${completed}/${totalRef})`);
            });
            inFlight2.add(p);
            p.finally(() => inFlight2.delete(p)).catch(() => {});
            if (inFlight2.size >= maxPending) await Promise.race(inFlight2);
          }
        }
        await Promise.allSettled(Array.from(inFlight2));

        if (cancelRef.current.cancelled) throw new Error("cancelled");
        refined.sort(makeCompareCand(refined));
        const bestRefined = refined[0] ?? null;
        const bestScreen = scores[0] ?? null;
        const compareCombined = makeCompareCand([...refined, ...scores]);
        best = bestRefined && bestScreen ? (compareCombined(bestRefined, bestScreen) <= 0 ? bestRefined : bestScreen) : bestRefined ?? bestScreen ?? undefined;
        bestPool = bestRefined && bestScreen ? (compareCombined(bestRefined, bestScreen) <= 0 ? refined : scores) : refined.length ? refined : scores;
      }
      if (!best) throw new Error("No candidates");

      let tieBreakReport: TieBreakReport;
      if (useSignificance && best.primaryStd != null && best.primaryN != null) {
        // Use variance from screening/refinement; no extra runs
        const topCands = [...bestPool].sort(makeCompareCand(bestPool)).slice(0, 20);
        let tiedAtPrimary = 1;
        for (let i = 1; i < topCands.length; i += 1) {
          const c = topCands[i]!;
          if (c.primaryStd == null || c.primaryN == null) continue;
          const p = welchTTestTwoTailed(
            best.primary,
            best.primaryStd,
            best.primaryN,
            c.primary,
            c.primaryStd,
            c.primaryN,
          );
          if (p >= 0.05) tiedAtPrimary += 1;
        }
        const hasSecondary = (best.secondary ?? 0) > 0 || topCands.some((c) => (c.secondary ?? 0) !== 0);
        const hasTertiary = (best.tertiary ?? 0) > 0 || topCands.some((c) => (c.tertiary ?? 0) !== 0);
        const primaryMetric = mode === "stage" ? "avg_max_stage" : mode === "XP" ? "xp_per_hour" : "frag_per_hour";
        let winnerReason = "highest primary score";
        if (tiedAtPrimary > 1) {
          const tail =
            mode === "frag"
              ? (() => {
                  const { secFrag, terFrag } = getFragTieBreakFragments(targetFrag);
                  const secLabel = secFrag != null ? secFrag.toUpperCase() : null;
                  const terLabel = terFrag != null ? terFrag.toUpperCase() : null;
                  if (hasTertiary && secLabel && terLabel) return `tie-break by ${secLabel}/h then ${terLabel}/h`;
                  if (hasSecondary && secLabel) return `tie-break by ${secLabel}/h`;
                  return "tie-break (lexicographic)";
                })()
              : mode === "XP"
                ? xpTieFragFirst
                  ? hasTertiary
                    ? "tie-break by fragments/h then avg max stage"
                    : hasSecondary
                      ? "tie-break by fragments/h"
                      : "tie-break (lexicographic)"
                  : hasTertiary
                    ? "tie-break by avg max stage then fragments/h"
                    : hasSecondary
                      ? "tie-break by avg max stage"
                      : "tie-break (lexicographic)"
                : hasTertiary
                  ? "tie-break by secondary then tertiary"
                  : hasSecondary
                    ? "tie-break by secondary"
                    : "tie-break (lexicographic)";
          winnerReason = `primary not significantly different (α=0.05) → ${tail}`;
        }
        const top3 = topCands.slice(0, 3).map((c, i) => ({
          label: `#${i + 1}`,
          primary: c.primary,
          secondary: c.secondary ?? undefined,
          tertiary: c.tertiary ?? undefined,
          ...(mode === "frag" ? { xpPerHour: c.xpPerHour ?? undefined } : {}),
          dist: candToDistMap(c.dist),
        }));
        tieBreakReport = {
          mode,
          epsilon: 0,
          primaryMetric,
          tiedAtPrimary,
          winnerReason,
          ...(mode === "frag" ? { targetFrag } : {}),
          ...(mode === "XP" ? { xpTieBreakSecondary: xpTieFragFirst ? ("frag_per_hour" as const) : ("avg_max_stage" as const) } : {}),
          top3,
        };
      } else {
        tieBreakReport = makeTieBreakReport(bestPool, best);
      }

      const bestBuild: ArchBuild = {
        ...build,
        skillPoints: buildSkillPointsFromOptimizerDist(
          build,
          normalizeOptimizerDistribution({ optimizerSkills, dist: best.dist, numPoints: statsBudget, caps, requireStr, rng }),
        ),
      };
      const bestStats = getTotalStats(bestBuild);

      // Phase 3: final 3000 sims (histogram = #1 winner)
      const totalFinal = 3000;
      setMcProgress(`Phase 3: Final sims (${totalFinal})…`);
      const chunkSize = clampInt(Math.trunc(totalFinal / Math.max(1, pool.size * 4)), 10, 100);
      let remaining = totalFinal;
      let done = 0;

      const objectiveSamples: number[] = [];
      let sumFloors = 0;
      let sumFloorsSq = 0;
      let sumXp = 0;
      let sumXpSq = 0;
      let sumTotalFrags = 0;
      let sumDur = 0;
      let sumDurSq = 0;
      let sumHits = 0;
      let sumHitsSq = 0;
      let sumXph = 0;
      let sumXphSq = 0;
      let sumFph = 0;
      let sumFphSq = 0;
      let sampleCount = 0;
      const sumFragsByTypeRef: Record<string, number> = emptyFragCounts();
      const FRAG_TYPES_REF = ARCH_FRAGMENT_TYPES;
      const staminaAtStageSumRef: Record<number, number> = {};
      const staminaAtStageSumSqRef: Record<number, number> = {};
      const staminaAtStageCountRef: Record<number, number> = {};
      const staminaAtStageByRunRef: number[][] = [];

      const tasks: Promise<void>[] = [];
      let submitted = 0;
      while (remaining > 0) {
        if (cancelRef.current.cancelled) throw new Error("cancelled");
        const n = Math.min(chunkSize, remaining);
        submitted += 1;
        const seed = seedBase + 1_000_000 + submitted;
        const t = pool
          .run({
            type: "stageLite",
            payload: { stats: bestStats, starting_floor: 1, n_sims: n, options, cardCfg, seed, targetFrag: mode === "frag" ? targetFrag : null, initialSpeedModHits: build.permanentSpeedModEnabled ? PERMANENT_SPEED_MOD_INITIAL_HITS : undefined },
          })
          .then((out) => {
            const dur: number[] = out.run_duration_seconds_samples ?? [];
            const xp: number[] = out.xp_per_run_samples ?? [];
            const maxs: number[] = out.max_stage_samples ?? [];
            const floors: number[] = out.floors_cleared_samples ?? [];
            const totals: number[] = out.total_fragments_samples ?? [];
            const hits: number[] = (out as { total_hits_samples?: number[] }).total_hits_samples ?? [];
            const targ: number[] = out.target_frag_samples ?? [];
            const runFragsByType = (out as { run_fragments_by_type?: Record<string, number[]> }).run_fragments_by_type ?? {};
            for (let i = 0; i < dur.length; i += 1) {
              const d = Number(dur[i] ?? 1);
              const runsPerHour = d > 0 ? 3600.0 / d : 0;
              if (mode === "XP") objectiveSamples.push(Number(xp[i] ?? 0) * runsPerHour);
              else if (mode === "frag") objectiveSamples.push(Number(targ[i] ?? 0) * runsPerHour);
              else objectiveSamples.push(Number(maxs[i] ?? 0));

              sumDur += d;
              sumDurSq += d * d;
              const xpVal = Number(xp[i] ?? 0);
              const flVal = Number(floors[i] ?? 0);
              const totVal = Number(totals[i] ?? 0);
              sumXp += xpVal;
              sumXpSq += xpVal * xpVal;
              sumFloors += flVal;
              sumFloorsSq += flVal * flVal;
              sumTotalFrags += totVal;
              const xph = xpVal * runsPerHour;
              const fph = totVal * runsPerHour;
              sumXph += xph;
              sumXphSq += xph * xph;
              sumFph += fph;
              sumFphSq += fph * fph;
              const h = Number(hits[i] ?? 0);
              sumHits += h;
              sumHitsSq += h * h;
              for (const k of FRAG_TYPES_REF) sumFragsByTypeRef[k] += Number(runFragsByType[k]?.[i] ?? 0);
              sampleCount += 1;
            }
            if (mode === "stage") {
              const sum = (out as { stamina_at_stage_sum?: Record<number, number> }).stamina_at_stage_sum;
              const sumSq = (out as { stamina_at_stage_sum_sq?: Record<number, number> }).stamina_at_stage_sum_sq;
              const cnt = (out as { stamina_at_stage_count?: Record<number, number> }).stamina_at_stage_count;
              const byRun = (out as { stamina_at_stage_by_run?: number[][] }).stamina_at_stage_by_run;
              if (sum) for (const [s, v] of Object.entries(sum)) { const k = Math.trunc(Number(s)); staminaAtStageSumRef[k] = (staminaAtStageSumRef[k] ?? 0) + Number(v); }
              if (sumSq) for (const [s, v] of Object.entries(sumSq)) { const k = Math.trunc(Number(s)); staminaAtStageSumSqRef[k] = (staminaAtStageSumSqRef[k] ?? 0) + Number(v); }
              if (cnt) for (const [s, v] of Object.entries(cnt)) { const k = Math.trunc(Number(s)); staminaAtStageCountRef[k] = (staminaAtStageCountRef[k] ?? 0) + Number(v); }
              if (byRun && Array.isArray(byRun)) staminaAtStageByRunRef.push(...byRun);
            }
            done += n;
            setMcProgress(`Phase 3: Final sims (${done}/${totalFinal})`);
          });
        tasks.push(t);
        remaining -= n;
      }
      await Promise.all(tasks);

      if (cancelRef.current.cancelled) throw new Error("cancelled");

      // Block breakdown (100 sims for time distribution per block type)
      let blockBreakdown: McLogEntry["metrics"]["blockBreakdown"] = undefined;
      try {
        setMcProgress("Block breakdown…");
        const bb = await pool.run({
          type: "blockBreakdown",
          payload: {
            stats: bestStats,
            starting_floor: 1,
            n_sims: 100,
            options,
            cardCfg,
            seed: seedBase + 999_999,
          },
        });
        if (bb?.by_type && Object.keys(bb.by_type).length > 0) blockBreakdown = bb;
      } catch {
        // Non-fatal; continue without block breakdown
      }

      if (cancelRef.current.cancelled) throw new Error("cancelled");

      // Save entry (MC averages from final samples)
      const avgFloors = sampleCount > 0 ? sumFloors / sampleCount : 0;
      const avgXp = sampleCount > 0 ? sumXp / sampleCount : 0;
      const avgTotalFrags = sampleCount > 0 ? sumTotalFrags / sampleCount : 0;
      const avgDur = sampleCount > 0 ? sumDur / sampleCount : 1;
      const avgAttacksPerRun = sampleCount > 0 ? sumHits / sampleCount : 0;
      const varianceDurRef = sampleCount > 1 ? Math.max(0, sumDurSq / sampleCount - avgDur * avgDur) : 0;
      const durationSecondsStdRef = sampleCount > 1 ? Math.sqrt(varianceDurRef) : undefined;
      const varianceHitsRef = sampleCount > 1 ? Math.max(0, sumHitsSq / sampleCount - avgAttacksPerRun * avgAttacksPerRun) : 0;
      const attacksPerRunStdRef = sampleCount > 1 ? Math.sqrt(varianceHitsRef) : undefined;
      const meanFloorsRef = sampleCount > 0 ? sumFloors / sampleCount : 0;
      const varianceFloorsRef = sampleCount > 1 ? Math.max(0, sumFloorsSq / sampleCount - meanFloorsRef * meanFloorsRef) : 0;
      const floorsPerRunStdRef = sampleCount > 1 ? Math.sqrt(varianceFloorsRef) : undefined;
      const varianceXpRef = sampleCount > 1 ? Math.max(0, sumXpSq / sampleCount - avgXp * avgXp) : 0;
      const xpPerRunStdRef = sampleCount > 1 ? Math.sqrt(varianceXpRef) : undefined;
      const meanXphRef = sampleCount > 0 ? sumXph / sampleCount : 0;
      const varianceXphRef = sampleCount > 1 ? Math.max(0, sumXphSq / sampleCount - meanXphRef * meanXphRef) : 0;
      const xpPerHourStdRef = sampleCount > 1 ? Math.sqrt(varianceXphRef) : undefined;
      const meanFphRef = sampleCount > 0 ? sumFph / sampleCount : 0;
      const varianceFphRef = sampleCount > 1 ? Math.max(0, sumFphSq / sampleCount - meanFphRef * meanFphRef) : 0;
      const fragmentsPerHourStdRef = sampleCount > 1 ? Math.sqrt(varianceFphRef) : undefined;
      let xpPerHour = avgDur > 0 ? (avgXp * 3600.0) / avgDur : 0;
      let fragmentsPerHour = avgDur > 0 ? (avgTotalFrags * 3600.0) / avgDur : 0;
      const fragmentsPerHourByTypeRef: Record<string, number> = {};
      if (sumDur > 0) for (const k of FRAG_TYPES_REF) fragmentsPerHourByTypeRef[k] = (sumFragsByTypeRef[k] ?? 0) * (3600.0 / sumDur);
      const archExtRef = loadJson<{ lootbugArch600AttacksPerHour?: number }>(ARCH_EXTERNAL_KEY) ?? {};
      const lootbugAttacksRef = typeof archExtRef?.lootbugArch600AttacksPerHour === "number" ? archExtRef.lootbugArch600AttacksPerHour : 0;
      if (lootbugAttacksRef > 0 && bestStats.max_stamina > 0) {
        const extraRunsPerHour = lootbugAttacksRef / bestStats.max_stamina;
        xpPerHour += extraRunsPerHour * avgXp;
        fragmentsPerHour += extraRunsPerHour * avgTotalFrags;
        if (sampleCount > 0) for (const k of FRAG_TYPES_REF) fragmentsPerHourByTypeRef[k] = (fragmentsPerHourByTypeRef[k] ?? 0) + extraRunsPerHour * ((sumFragsByTypeRef[k] ?? 0) / sampleCount);
      }
      const avgStaminaAtEndOfStageRef: Record<number, number> = {};
      const stdStaminaAtEndOfStageRef: Record<number, number> = {};
      if (mode === "stage") {
        for (const s of Object.keys(staminaAtStageSumRef)) {
          const stage = Math.trunc(Number(s));
          const cnt = staminaAtStageCountRef[stage] ?? 0;
          if (cnt > 0) {
            const sum = staminaAtStageSumRef[stage] ?? 0;
            const sumSq = staminaAtStageSumSqRef[stage] ?? 0;
            avgStaminaAtEndOfStageRef[stage] = sum / cnt;
            if (cnt > 1) {
              const variance = Math.max(0, sumSq / cnt - (sum / cnt) ** 2);
              stdStaminaAtEndOfStageRef[stage] = Math.sqrt(variance);
            }
          }
        }
      }
      const entry: McLogEntry = {
        id: `mc_${Date.now()}_${Math.random().toString(16).slice(2)}`,
        createdAt: Date.now(),
        label:
          mode === "frag"
            ? `MC Fragment Farmer (${targetFrag.toUpperCase()})`
            : mode === "XP"
              ? "MC XP Optimizer"
              : "MC Stage Push Optimizer",
        mcType: mode,
        build: bestBuild,
        metrics: {
          floorsPerRun: avgFloors,
          xpPerRun: avgXp,
          durationSeconds: avgDur,
          durationSecondsStd: durationSecondsStdRef,
          fragmentsPerRunTotal: avgTotalFrags,
          xpPerHour,
          fragmentsPerHour,
          floorsPerRunStd: floorsPerRunStdRef,
          xpPerRunStd: xpPerRunStdRef,
          xpPerHourStd: xpPerHourStdRef,
          fragmentsPerHourStd: fragmentsPerHourStdRef,
          attacksPerRun: avgAttacksPerRun,
          attacksPerRunStd: attacksPerRunStdRef,
          fragmentsPerHourByType: fragmentsPerHourByTypeRef,
          blockBreakdown,
        },
        mc: {
          archLevel: statsBudget,
          screeningSims,
          refinementSims,
          targetFrag: mode === "frag" ? targetFrag : undefined,
          objective: mode,
          objectiveSamples,
          ...(Object.keys(avgStaminaAtEndOfStageRef).length > 0
            ? {
                avgStaminaAtEndOfStage: avgStaminaAtEndOfStageRef,
                stdStaminaAtEndOfStage: Object.keys(stdStaminaAtEndOfStageRef).length > 0 ? stdStaminaAtEndOfStageRef : undefined,
                staminaAtStageByRun: staminaAtStageByRunRef.length > 0 ? staminaAtStageByRunRef : undefined,
              }
            : {}),
          tieBreak: tieBreakReport,
        },
      };
      if (opts?.returnResult) {
        const primary =
          objectiveSamples.length > 0 ? objectiveSamples.reduce((a, b) => a + b, 0) / objectiveSamples.length : 0;
        return { bestBuild: entry.build, metrics: entry.metrics, objectiveSamples, tieBreak: tieBreakReport, primary };
      }
      setMcLog((xs) => [entry, ...xs]);
      setActiveLogId(entry.id);
      setMcProgress("Done.");
    } catch (e) {
      if (String(e).includes("cancelled")) {
        setMcProgress("Cancelled.");
      } else {
        setMcProgress(e instanceof Error ? e.message : String(e));
      }
    } finally {
      pool.terminate();
      cancelRef.current.pool = null;
      if (!opts?.returnResult) {
        setMcRunning(false);
        setMcActiveMode(null);
      }
    }
    return null;
  }

  async function runBuildMc() {
    if (mcRunning || buildMcRunning) return;
    setBuildMcRunning(true);
    setBuildMcProgress("Starting…");
    const N = clampInt(buildMcN, 100, 500000);
    const hc = typeof navigator !== "undefined" ? Number((navigator as any).hardwareConcurrency ?? 4) : 4;
    const workerCount = clampInt(Math.max(1, hc - 1), 1, 8);
    const pool = createWorkerPool(workerCount);
    const seedBase = (Date.now() & 0x7fffffff) >>> 0;
    const currentBuild = build;
    const bestStats = getTotalStats(currentBuild);
    const options = mcOptionsFromBuild(currentBuild);
    const cardCfg = { blockCards: currentBuild.blockCards, polychromeBonus: getPolychromeBonus() };
    const FRAG_TYPES_REF = ARCH_FRAGMENT_TYPES;
    try {
      setBuildMcProgress(`Final sims (0/${N})…`);
      const chunkSize = clampInt(Math.trunc(N / Math.max(1, pool.size * 4)), 10, 500);
      let remaining = N;
      let done = 0;
      const objectiveSamples: number[] = [];
      let sumFloors = 0,
        sumFloorsSq = 0,
        sumXp = 0,
        sumXpSq = 0,
        sumTotalFrags = 0,
        sumDur = 0,
        sumDurSq = 0,
        sumHits = 0,
        sumHitsSq = 0,
        sumXph = 0,
        sumXphSq = 0,
        sumFph = 0,
        sumFphSq = 0;
      let sampleCount = 0;
      const sumFragsByTypeRef: Record<string, number> = emptyFragCounts();
      const staminaAtStageSumRef: Record<number, number> = {};
      const staminaAtStageSumSqRef: Record<number, number> = {};
      const staminaAtStageCountRef: Record<number, number> = {};
      const staminaAtStageByRunRef: number[][] = [];
      let submitted = 0;
      const tasks: Promise<void>[] = [];
      while (remaining > 0) {
        const n = Math.min(chunkSize, remaining);
        submitted += 1;
        const seed = seedBase + 1_000_000 + submitted;
        const t = pool
          .run({
            type: "stageLite",
            payload: {
              stats: bestStats,
              starting_floor: 1,
              n_sims: n,
              options,
              cardCfg,
              seed,
              targetFrag: null,
              initialSpeedModHits: currentBuild.permanentSpeedModEnabled ? PERMANENT_SPEED_MOD_INITIAL_HITS : undefined,
            },
          })
          .then((out) => {
            const dur: number[] = out.run_duration_seconds_samples ?? [];
            const xp: number[] = out.xp_per_run_samples ?? [];
            const maxs: number[] = out.max_stage_samples ?? [];
            const floors: number[] = out.floors_cleared_samples ?? [];
            const totals: number[] = out.total_fragments_samples ?? [];
            const hits: number[] = (out as { total_hits_samples?: number[] }).total_hits_samples ?? [];
            const runFragsByType = (out as { run_fragments_by_type?: Record<string, number[]> }).run_fragments_by_type ?? {};
            for (let i = 0; i < dur.length; i += 1) {
              const d = Number(dur[i] ?? 1);
              const runsPerHour = d > 0 ? 3600.0 / d : 0;
              objectiveSamples.push(Number(maxs[i] ?? 0));
              sumDur += d;
              sumDurSq += d * d;
              const xpVal = Number(xp[i] ?? 0);
              const flVal = Number(floors[i] ?? 0);
              const totVal = Number(totals[i] ?? 0);
              sumXp += xpVal;
              sumXpSq += xpVal * xpVal;
              sumFloors += flVal;
              sumFloorsSq += flVal * flVal;
              sumTotalFrags += totVal;
              const xph = xpVal * runsPerHour;
              const fph = totVal * runsPerHour;
              sumXph += xph;
              sumXphSq += xph * xph;
              sumFph += fph;
              sumFphSq += fph * fph;
              const h = Number(hits[i] ?? 0);
              sumHits += h;
              sumHitsSq += h * h;
              for (const k of FRAG_TYPES_REF) sumFragsByTypeRef[k] += Number(runFragsByType[k]?.[i] ?? 0);
              sampleCount += 1;
            }
            const sum = (out as { stamina_at_stage_sum?: Record<number, number> }).stamina_at_stage_sum;
            const sumSq = (out as { stamina_at_stage_sum_sq?: Record<number, number> }).stamina_at_stage_sum_sq;
            const cnt = (out as { stamina_at_stage_count?: Record<number, number> }).stamina_at_stage_count;
            const byRun = (out as { stamina_at_stage_by_run?: number[][] }).stamina_at_stage_by_run;
            if (sum) for (const [s, v] of Object.entries(sum)) { const k = Math.trunc(Number(s)); staminaAtStageSumRef[k] = (staminaAtStageSumRef[k] ?? 0) + Number(v); }
            if (sumSq) for (const [s, v] of Object.entries(sumSq)) { const k = Math.trunc(Number(s)); staminaAtStageSumSqRef[k] = (staminaAtStageSumSqRef[k] ?? 0) + Number(v); }
            if (cnt) for (const [s, v] of Object.entries(cnt)) { const k = Math.trunc(Number(s)); staminaAtStageCountRef[k] = (staminaAtStageCountRef[k] ?? 0) + Number(v); }
            if (byRun && Array.isArray(byRun)) staminaAtStageByRunRef.push(...byRun);
            done += n;
            setBuildMcProgress(`Final sims (${done}/${N})…`);
          });
        tasks.push(t);
        remaining -= n;
      }
      await Promise.all(tasks);

      setBuildMcProgress("Block breakdown…");
      let blockBreakdown: McLogEntry["metrics"]["blockBreakdown"] = undefined;
      try {
        const bb = await pool.run({
          type: "blockBreakdown",
          payload: { stats: bestStats, starting_floor: 1, n_sims: 100, options, cardCfg, seed: seedBase + 999_999 },
        });
        if (bb?.by_type && Object.keys(bb.by_type).length > 0) blockBreakdown = bb;
      } catch {
        // non-fatal
      }

      const avgFloors = sampleCount > 0 ? sumFloors / sampleCount : 0;
      const avgXp = sampleCount > 0 ? sumXp / sampleCount : 0;
      const avgTotalFrags = sampleCount > 0 ? sumTotalFrags / sampleCount : 0;
      const avgDur = sampleCount > 0 ? sumDur / sampleCount : 1;
      const avgAttacksPerRun = sampleCount > 0 ? sumHits / sampleCount : 0;
      const durationSecondsStdRef = sampleCount > 1 ? Math.sqrt(Math.max(0, sumDurSq / sampleCount - avgDur * avgDur)) : undefined;
      const attacksPerRunStdRef = sampleCount > 1 ? Math.sqrt(Math.max(0, sumHitsSq / sampleCount - avgAttacksPerRun * avgAttacksPerRun)) : undefined;
      const floorsPerRunStdRef = sampleCount > 1 ? Math.sqrt(Math.max(0, sumFloorsSq / sampleCount - avgFloors * avgFloors)) : undefined;
      const xpPerRunStdRef = sampleCount > 1 ? Math.sqrt(Math.max(0, sumXpSq / sampleCount - avgXp * avgXp)) : undefined;
      const meanXphRef = sampleCount > 0 ? sumXph / sampleCount : 0;
      const xpPerHourStdRef = sampleCount > 1 ? Math.sqrt(Math.max(0, sumXphSq / sampleCount - meanXphRef * meanXphRef)) : undefined;
      const meanFphRef = sampleCount > 0 ? sumFph / sampleCount : 0;
      const fragmentsPerHourStdRef = sampleCount > 1 ? Math.sqrt(Math.max(0, sumFphSq / sampleCount - meanFphRef * meanFphRef)) : undefined;
      let xpPerHour = avgDur > 0 ? (avgXp * 3600.0) / avgDur : 0;
      let fragmentsPerHour = avgDur > 0 ? (avgTotalFrags * 3600.0) / avgDur : 0;
      const fragmentsPerHourByTypeRef: Record<string, number> = {};
      if (sumDur > 0) for (const k of FRAG_TYPES_REF) fragmentsPerHourByTypeRef[k] = (sumFragsByTypeRef[k] ?? 0) * (3600.0 / sumDur);
      const archExtRef = loadJson<{ lootbugArch600AttacksPerHour?: number }>(ARCH_EXTERNAL_KEY) ?? {};
      const lootbugAttacksRef = typeof archExtRef?.lootbugArch600AttacksPerHour === "number" ? archExtRef.lootbugArch600AttacksPerHour : 0;
      if (lootbugAttacksRef > 0 && bestStats.max_stamina > 0) {
        const extraRunsPerHour = lootbugAttacksRef / bestStats.max_stamina;
        xpPerHour += extraRunsPerHour * avgXp;
        fragmentsPerHour += extraRunsPerHour * avgTotalFrags;
        if (sampleCount > 0) for (const k of FRAG_TYPES_REF) fragmentsPerHourByTypeRef[k] = (fragmentsPerHourByTypeRef[k] ?? 0) + extraRunsPerHour * ((sumFragsByTypeRef[k] ?? 0) / sampleCount);
      }
      const avgStaminaAtEndOfStageRef: Record<number, number> = {};
      const stdStaminaAtEndOfStageRef: Record<number, number> = {};
      for (const s of Object.keys(staminaAtStageSumRef)) {
        const stage = Math.trunc(Number(s));
        const cnt = staminaAtStageCountRef[stage] ?? 0;
        if (cnt > 0) {
          const sum = staminaAtStageSumRef[stage] ?? 0;
          const sumSq = staminaAtStageSumSqRef[stage] ?? 0;
          avgStaminaAtEndOfStageRef[stage] = sum / cnt;
          if (cnt > 1) stdStaminaAtEndOfStageRef[stage] = Math.sqrt(Math.max(0, sumSq / cnt - (sum / cnt) ** 2));
        }
      }
      const entry: McLogEntry = {
        id: `mc_${Date.now()}_${Math.random().toString(16).slice(2)}`,
        createdAt: Date.now(),
        label: `Build MC (N=${N})`,
        mcType: "stage",
        build: currentBuild,
        metrics: {
          floorsPerRun: avgFloors,
          xpPerRun: avgXp,
          durationSeconds: avgDur,
          durationSecondsStd: durationSecondsStdRef,
          fragmentsPerRunTotal: avgTotalFrags,
          xpPerHour,
          fragmentsPerHour,
          floorsPerRunStd: floorsPerRunStdRef,
          xpPerRunStd: xpPerRunStdRef,
          xpPerHourStd: xpPerHourStdRef,
          fragmentsPerHourStd: fragmentsPerHourStdRef,
          attacksPerRun: avgAttacksPerRun,
          attacksPerRunStd: attacksPerRunStdRef,
          fragmentsPerHourByType: fragmentsPerHourByTypeRef,
          blockBreakdown,
        },
        mc: {
          archLevel: clampInt(Number(currentBuild.archLevel ?? 0), 0, 999),
          screeningSims: 0,
          refinementSims: N,
          objective: "stage",
          objectiveSamples,
          ...(Object.keys(avgStaminaAtEndOfStageRef).length > 0
            ? {
                avgStaminaAtEndOfStage: avgStaminaAtEndOfStageRef,
                stdStaminaAtEndOfStage: Object.keys(stdStaminaAtEndOfStageRef).length > 0 ? stdStaminaAtEndOfStageRef : undefined,
                staminaAtStageByRun: staminaAtStageByRunRef.length > 0 ? staminaAtStageByRunRef : undefined,
              }
            : {}),
        },
      };
      setMcLog((xs) => [entry, ...xs]);
      setActiveLogId(entry.id);
      setOpenLogId(entry.id);
    } catch (e) {
      setBuildMcProgress(e instanceof Error ? e.message : String(e));
    } finally {
      pool.terminate();
      setBuildMcRunning(false);
      setBuildMcProgress(null);
    }
  }

  async function runComparison(mode: "frag" | "XP" | "stage") {
    if (mcRunning) return;
    cancelRef.current.cancelled = false;
    setComparisonResult(null);
    setMcActiveMode(mode);
    setMcRunning(true);
    const methods = mcSettings.comparisonMethods;
    if (!methods.length) {
      setMcProgress("No methods selected for comparison.");
      setMcRunning(false);
      setMcActiveMode(null);
      return;
    }
    const methodResults: Array<{ methodId: McComparisonMethodId; label: string; build: ArchBuild; primary: number }> = [];
    try {
      for (const methodId of methods) {
        if (cancelRef.current.cancelled) break;
        if (methodId === "default") {
          setMcProgress("Comparison: Default 2-phase…");
          const r = await runMcOptimizer(mode, { returnResult: true, seedOffset: 0 });
          if (r) methodResults.push({ methodId: "default", label: "Default 2-phase", build: r.bestBuild, primary: r.primary });
        } else if (methodId === "multiStart3") {
          const runs: Array<{ bestBuild: ArchBuild; primary: number }> = [];
          for (let i = 0; i < 3; i += 1) {
            if (cancelRef.current.cancelled) break;
            setMcProgress(`Comparison: Multi-start (${i + 1}/3)…`);
            const r = await runMcOptimizer(mode, { returnResult: true, seedOffset: (i + 1) * 1_000_000 });
            if (r) runs.push({ bestBuild: r.bestBuild, primary: r.primary });
          }
          if (runs.length > 0) {
            const best = runs.reduce((a, b) => (a.primary >= b.primary ? a : b));
            methodResults.push({ methodId: "multiStart3", label: "Multi-start (3 seeds)", build: best.bestBuild, primary: best.primary });
          }
        }
      }
      if (cancelRef.current.cancelled) throw new Error("cancelled");
      if (methodResults.length === 0) {
        setMcProgress("No results from comparison.");
        return;
      }
      const winner = methodResults.reduce((a, b) => (a.primary >= b.primary ? a : b));
      setComparisonResult({ mode, methodResults, winnerId: winner.methodId });
      setMcProgress("Done.");
    } catch (e) {
      if (String(e).includes("cancelled")) setMcProgress("Cancelled.");
      else setMcProgress(e instanceof Error ? e.message : String(e));
    } finally {
      setMcRunning(false);
      setMcActiveMode(null);
    }
  }

  function applyBuildToCurrent(b: ArchBuild) {
    setBuild((prev) => ({ ...prev, skillPoints: { ...b.skillPoints } }));
  }

  async function runUpgradeNext() {
    const refEntry = upgradeNextRefId ? stageLogEntries.find((e) => e.id === upgradeNextRefId) ?? null : stageLogEntries[0] ?? null;
    if (!refEntry) {
      setUpgradeNextProgress("No Stage MC result to use. Run a Stage Push MC first.");
      return;
    }
    const winnerDist = winnerStatsFromLogEntry(refEntry);
    const baseBuild: ArchBuild = {
      ...refEntry.build,
      skillPoints: winnerDist,
    };
    const unlockedUpgrades = sortedFragmentUpgrades.filter(([key, info]) => {
      const stageUnlock = clampInt(Number(info.stage_unlock ?? 0), 0, 999);
      const maxLvl = clampInt(Number(info.max_level ?? 0), 0, 999);
      const ascTier = Number((info as { ascension_tier?: number }).ascension_tier ?? 0);
      const lvl = clampInt(Number(baseBuild.fragmentUpgradeLevels[key] ?? 0), 0, maxLvl);
      return ascTier <= (baseBuild.ascensionLevel ?? 0) && baseBuild.unlockedStage >= stageUnlock && lvl < maxLvl;
    });
    if (unlockedUpgrades.length === 0) {
      setUpgradeNextProgress("No upgrades to evaluate (all maxed or locked).");
      return;
    }
    setUpgradeNextRunning(true);
    setUpgradeNextProgress(null);
    setUpgradeNextResults(null);
    upgradeNextCancelRef.current = false;
    const hc = typeof navigator !== "undefined" ? navigator.hardwareConcurrency : 4;
    const pool = createWorkerPool(clampInt(Math.max(1, hc - 1), 1, 8));
    const options = mcOptionsFromBuild(baseBuild);
    const seedBase = (Date.now() & 0x7fffffff) >>> 0;
    const N_SIMS = 3000;
    type UpgradeResult = { key: string; displayName: string; costType: string; meanFloors: number; growthPct: number; cost: number | null; perCost: number | null; significant: boolean };
    const results: UpgradeResult[] = [];
    try {
      setUpgradeNextProgress("Which Fragment Upgrade next to maximize Stage Push: Baseline (no upgrade)…");
      const baseStats = getTotalStats(baseBuild);
      const polychromeBase = clampInt(Number(baseBuild.fragmentUpgradeLevels["polychrome_bonus"] ?? 0), 0, 1);
      const cardCfgBase = { blockCards: baseBuild.blockCards, polychromeBonus: 0.15 * polychromeBase };
      const baseOut = await pool.run({
        type: "stageLite",
        payload: { stats: baseStats, starting_floor: 1, n_sims: N_SIMS, options, cardCfg: cardCfgBase, seed: seedBase, targetFrag: null, initialSpeedModHits: baseBuild.permanentSpeedModEnabled ? PERMANENT_SPEED_MOD_INITIAL_HITS : undefined },
      });
      const baseFloors = (baseOut as { floors_cleared_samples?: number[] }).floors_cleared_samples ?? [];
      const baseStatsRes = baseFloors.length > 0 ? sampleStats(baseFloors) : { mean: 0, std: 0, min: 0, max: 0 };
      const baseMeanFloors = baseStatsRes.mean;
      const baseStd = baseStatsRes.std;

      for (let i = 0; i < unlockedUpgrades.length; i += 1) {
        if (upgradeNextCancelRef.current) break;
        const [key, info] = unlockedUpgrades[i]!;
        setUpgradeNextProgress(`Which Fragment Upgrade next to maximize Stage Push: ${i + 1}/${unlockedUpgrades.length} — ${(info as any).display_name ?? key}`);
        const curLvl = clampInt(Number(baseBuild.fragmentUpgradeLevels[key] ?? 0), 0, 999);
        const cost = getUpgradeCost(key, curLvl, baseBuild.ascensionLevel ?? 0);
        const variantBuild: ArchBuild = {
          ...baseBuild,
          fragmentUpgradeLevels: { ...baseBuild.fragmentUpgradeLevels, [key]: curLvl + 1 },
        };
        const stats = getTotalStats(variantBuild);
        const polychromeLvl = clampInt(Number(variantBuild.fragmentUpgradeLevels["polychrome_bonus"] ?? 0), 0, 1);
        const cardCfg = { blockCards: variantBuild.blockCards, polychromeBonus: 0.15 * polychromeLvl };
        const out = await pool.run({
          type: "stageLite",
          payload: { stats, starting_floor: 1, n_sims: N_SIMS, options, cardCfg, seed: seedBase + i + 1, targetFrag: null, initialSpeedModHits: baseBuild.permanentSpeedModEnabled ? PERMANENT_SPEED_MOD_INITIAL_HITS : undefined },
        });
        const floors = (out as { floors_cleared_samples?: number[] }).floors_cleared_samples ?? [];
        const varStats = floors.length > 0 ? sampleStats(floors) : { mean: 0, std: 0, min: 0, max: 0 };
        const meanFloors = varStats.mean;
        const growthPct = baseMeanFloors > 0 ? ((meanFloors - baseMeanFloors) / baseMeanFloors) * 100 : 0;
        const perCost = cost != null && cost > 0 ? growthPct / cost : null;
        const costType = String((info as any)?.cost_type ?? "misc");
        const seBase = baseStd / Math.sqrt(N_SIMS);
        const seVar = varStats.std / Math.sqrt(N_SIMS);
        const seDiff = Math.sqrt(seBase * seBase + seVar * seVar);
        const seGrowthPct = baseMeanFloors > 0 ? (seDiff / baseMeanFloors) * 100 : 0;
        const significant = seGrowthPct > 0 && Math.abs(growthPct) > 1.96 * seGrowthPct;
        results.push({
          key,
          displayName: (info as any).display_name ?? key,
          costType,
          meanFloors,
          growthPct,
          cost,
          perCost,
          significant,
        });
      }
      results.sort((a, b) => b.growthPct - a.growthPct);
      setUpgradeNextResults(results);
      setUpgradeNextProgress(upgradeNextCancelRef.current ? "Cancelled." : "Done.");
    } catch (e) {
      setUpgradeNextProgress(e instanceof Error ? e.message : String(e));
    } finally {
      pool.terminate();
      setUpgradeNextRunning(false);
    }
  }

  async function runGemCardSkillNext() {
    const refEntry = gemCardSkillNextRefId ? stageLogEntries.find((e) => e.id === gemCardSkillNextRefId) ?? null : stageLogEntries[0] ?? null;
    if (!refEntry) {
      setGemCardSkillNextProgress("No Stage MC result to use. Run a Stage Push MC first.");
      return;
    }
    const winnerDist = winnerStatsFromLogEntry(refEntry);
    const baseBuild: ArchBuild = {
      ...refEntry.build,
      skillPoints: winnerDist,
    };
    const GEM_KEYS: ArchGemUpgradeKey[] = ["stamina", "xp", "fragment"];
    const GEM_LABELS: Record<ArchGemUpgradeKey, string> = {
      stamina: "Max Stamina / Stam mod chance",
      xp: "Archaeology Exp / Exp mod chance",
      fragment: "Fragment Gain / Loot mod chance",
    };
    const eligibleGems: Array<{ key: ArchGemUpgradeKey; displayName: string }> = [];
    for (const key of GEM_KEYS) {
      const maxLvl = GEM_UPGRADE_BONUSES[key].max_level ?? 0;
      const curLvl = clampInt(Number(baseBuild.gemUpgrades[key] ?? 0), 0, maxLvl);
      if (curLvl < maxLvl) eligibleGems.push({ key, displayName: GEM_LABELS[key] });
    }
    const eligibleCards: Array<{ key: string; blockType: BlockType; tier: BlockTier; displayName: string }> = [];
    for (const bt of BLOCK_TYPES) {
      for (const t of BLOCK_CARD_TIERS) {
        if (!getBlockData(t, bt)) continue;
        const key = `${bt},${t}`;
        const cur = (baseBuild.blockCards[key] ?? 0) as CardLevel;
        if (cur === 1) eligibleCards.push({ key, blockType: bt, tier: t, displayName: `${bt} T${t}` });
      }
    }
    const eligibleSkills: Array<{ key: "avadaKeda" | "blockBonker"; displayName: string }> = [];
    if (!baseBuild.avadaKedaEnabled) eligibleSkills.push({ key: "avadaKeda", displayName: "Avada Keda" });
    if (!baseBuild.blockBonkerEnabled) eligibleSkills.push({ key: "blockBonker", displayName: "Block Bonker" });
    const totalOptions = eligibleGems.length + eligibleCards.length + eligibleSkills.length;
    if (totalOptions === 0) {
      setGemCardSkillNextProgress("No gem, card, or skill tree upgrades to evaluate (all maxed or skills already ON).");
      return;
    }
    setGemCardSkillNextRunning(true);
    setGemCardSkillNextProgress(null);
    setGemCardSkillNextResults(null);
    gemCardSkillNextCancelRef.current = false;
    const hc = typeof navigator !== "undefined" ? navigator.hardwareConcurrency : 4;
    const pool = createWorkerPool(clampInt(Math.max(1, hc - 1), 1, 8));
    const options = mcOptionsFromBuild(baseBuild);
    const seedBase = (Date.now() & 0x7fffffff) >>> 0;
    const N_SIMS = 3000;
    type StagePushResult = { source: "gem" | "card" | "skill"; costClass: "gem" | "skill"; key: string; displayName: string; meanFloors: number; growthPct: number; cost: number | undefined; perCost: number; significant: boolean };
    const results: StagePushResult[] = [];
    try {
      setGemCardSkillNextProgress("Which Gem/Card/Skill Tree next (Stage Push): Baseline…");
      const baseStats = getTotalStats(baseBuild);
      const polychromeBase = clampInt(Number(baseBuild.fragmentUpgradeLevels["polychrome_bonus"] ?? 0), 0, 1);
      const cardCfgBase = { blockCards: baseBuild.blockCards, polychromeBonus: 0.15 * polychromeBase };
      const baseOut = await pool.run({
        type: "stageLite",
        payload: { stats: baseStats, starting_floor: 1, n_sims: N_SIMS, options, cardCfg: cardCfgBase, seed: seedBase, targetFrag: null, initialSpeedModHits: baseBuild.permanentSpeedModEnabled ? PERMANENT_SPEED_MOD_INITIAL_HITS : undefined },
      });
      const baseFloors = (baseOut as { floors_cleared_samples?: number[] }).floors_cleared_samples ?? [];
      const baseStatsRes = baseFloors.length > 0 ? sampleStats(baseFloors) : { mean: 0, std: 0, min: 0, max: 0 };
      const baseMeanFloors = baseStatsRes.mean;
      const baseStd = baseStatsRes.std;
      let idx = 0;
      for (let i = 0; i < eligibleGems.length; i += 1) {
        if (gemCardSkillNextCancelRef.current) break;
        const { key, displayName } = eligibleGems[i]!;
        idx += 1;
        setGemCardSkillNextProgress(`Which Gem/Card/Skill Tree next (Stage Push): ${idx}/${totalOptions} — Gem: ${displayName}`);
        const curLvl = clampInt(Number(baseBuild.gemUpgrades[key] ?? 0), 0, 999);
        const cost = getGemUpgradeCost(key, curLvl, baseBuild.ascensionLevel ?? 0);
        const variantBuild: ArchBuild = { ...baseBuild, gemUpgrades: { ...baseBuild.gemUpgrades, [key]: curLvl + 1 } };
        const stats = getTotalStats(variantBuild);
        const polychromeLvl = clampInt(Number(variantBuild.fragmentUpgradeLevels["polychrome_bonus"] ?? 0), 0, 1);
        const cardCfg = { blockCards: variantBuild.blockCards, polychromeBonus: 0.15 * polychromeLvl };
        const out = await pool.run({
          type: "stageLite",
          payload: { stats, starting_floor: 1, n_sims: N_SIMS, options, cardCfg, seed: seedBase + 10000 + idx, targetFrag: null, initialSpeedModHits: baseBuild.permanentSpeedModEnabled ? PERMANENT_SPEED_MOD_INITIAL_HITS : undefined },
        });
        const floors = (out as { floors_cleared_samples?: number[] }).floors_cleared_samples ?? [];
        const varStats = floors.length > 0 ? sampleStats(floors) : { mean: 0, std: 0, min: 0, max: 0 };
        const growthPct = baseMeanFloors > 0 ? ((varStats.mean - baseMeanFloors) / baseMeanFloors) * 100 : 0;
        const perCost = cost > 0 ? growthPct / cost : 0;
        const seBase = baseStd / Math.sqrt(N_SIMS);
        const seVar = varStats.std / Math.sqrt(N_SIMS);
        const seDiff = Math.sqrt(seBase * seBase + seVar * seVar);
        const seGrowthPct = baseMeanFloors > 0 ? (seDiff / baseMeanFloors) * 100 : 0;
        const significant = seGrowthPct > 0 && Math.abs(growthPct) > 1.96 * seGrowthPct;
        results.push({ source: "gem", costClass: "gem", key, displayName, meanFloors: varStats.mean, growthPct, cost, perCost, significant });
      }
      for (let i = 0; i < eligibleCards.length; i += 1) {
        if (gemCardSkillNextCancelRef.current) break;
        const { key, blockType, tier, displayName } = eligibleCards[i]!;
        idx += 1;
        setGemCardSkillNextProgress(`Which Gem/Card/Skill Tree next (Stage Push): ${idx}/${totalOptions} — Card: ${displayName}`);
        const cost = getCardGemCost(blockType, tier);
        const variantBuild: ArchBuild = { ...baseBuild, blockCards: { ...baseBuild.blockCards, [key]: 2 } };
        const stats = getTotalStats(variantBuild);
        const polychromeLvl = clampInt(Number(variantBuild.fragmentUpgradeLevels["polychrome_bonus"] ?? 0), 0, 1);
        const cardCfg = { blockCards: variantBuild.blockCards, polychromeBonus: 0.15 * polychromeLvl };
        const out = await pool.run({
          type: "stageLite",
          payload: { stats, starting_floor: 1, n_sims: N_SIMS, options, cardCfg, seed: seedBase + 20000 + idx, targetFrag: null, initialSpeedModHits: baseBuild.permanentSpeedModEnabled ? PERMANENT_SPEED_MOD_INITIAL_HITS : undefined },
        });
        const floors = (out as { floors_cleared_samples?: number[] }).floors_cleared_samples ?? [];
        const varStats = floors.length > 0 ? sampleStats(floors) : { mean: 0, std: 0, min: 0, max: 0 };
        const growthPct = baseMeanFloors > 0 ? ((varStats.mean - baseMeanFloors) / baseMeanFloors) * 100 : 0;
        const perCost = cost > 0 ? growthPct / cost : 0;
        const seBase = baseStd / Math.sqrt(N_SIMS);
        const seVar = varStats.std / Math.sqrt(N_SIMS);
        const seDiff = Math.sqrt(seBase * seBase + seVar * seVar);
        const seGrowthPct = baseMeanFloors > 0 ? (seDiff / baseMeanFloors) * 100 : 0;
        const significant = seGrowthPct > 0 && Math.abs(growthPct) > 1.96 * seGrowthPct;
        results.push({ source: "card", costClass: "gem", key, displayName, meanFloors: varStats.mean, growthPct, cost, perCost, significant });
      }
      for (let i = 0; i < eligibleSkills.length; i += 1) {
        if (gemCardSkillNextCancelRef.current) break;
        const { key, displayName } = eligibleSkills[i]!;
        idx += 1;
        setGemCardSkillNextProgress(`Which Gem/Card/Skill Tree next (Stage Push): ${idx}/${totalOptions} — Skill: ${displayName}`);
        const variantBuild: ArchBuild = {
          ...baseBuild,
          ...(key === "avadaKeda" ? { avadaKedaEnabled: true } : { blockBonkerEnabled: true }),
        };
        const stats = getTotalStats(variantBuild);
        const polychromeLvl = clampInt(Number(variantBuild.fragmentUpgradeLevels["polychrome_bonus"] ?? 0), 0, 1);
        const cardCfg = { blockCards: variantBuild.blockCards, polychromeBonus: 0.15 * polychromeLvl };
        const out = await pool.run({
          type: "stageLite",
          payload: { stats, starting_floor: 1, n_sims: N_SIMS, options, cardCfg, seed: seedBase + 30000 + idx, targetFrag: null, initialSpeedModHits: baseBuild.permanentSpeedModEnabled ? PERMANENT_SPEED_MOD_INITIAL_HITS : undefined },
        });
        const floors = (out as { floors_cleared_samples?: number[] }).floors_cleared_samples ?? [];
        const varStats = floors.length > 0 ? sampleStats(floors) : { mean: 0, std: 0, min: 0, max: 0 };
        const growthPct = baseMeanFloors > 0 ? ((varStats.mean - baseMeanFloors) / baseMeanFloors) * 100 : 0;
        const seBase = baseStd / Math.sqrt(N_SIMS);
        const seVar = varStats.std / Math.sqrt(N_SIMS);
        const seDiff = Math.sqrt(seBase * seBase + seVar * seVar);
        const seGrowthPct = baseMeanFloors > 0 ? (seDiff / baseMeanFloors) * 100 : 0;
        const significant = seGrowthPct > 0 && Math.abs(growthPct) > 1.96 * seGrowthPct;
        results.push({ source: "skill", costClass: "skill", key, displayName, meanFloors: varStats.mean, growthPct, cost: undefined, perCost: 0, significant });
      }
      results.sort((a, b) => b.growthPct - a.growthPct);
      setGemCardSkillNextResults(results);
      setGemCardSkillNextProgress(gemCardSkillNextCancelRef.current ? "Cancelled." : "Done.");
    } catch (e) {
      setGemCardSkillNextProgress(e instanceof Error ? e.message : String(e));
    } finally {
      pool.terminate();
      setGemCardSkillNextRunning(false);
    }
  }

  async function runGemFragNext() {
    const refEntry = gemFragNextRefId ? fragmentLogEntries.find((e) => e.id === gemFragNextRefId) ?? null : fragmentLogEntries[0] ?? null;
    if (!refEntry) {
      setGemFragNextProgress("No Fragment MC result to use. Run a Fragment MC first and pick it as template.");
      return;
    }
    const targetFrag: BlockType = refEntry.mc?.targetFrag ?? mcSettings.targetFrag;
    const winnerDist = winnerStatsFromLogEntry(refEntry);
    const baseBuild: ArchBuild = {
      ...refEntry.build,
      skillPoints: winnerDist,
    };
    const GEM_KEYS: ArchGemUpgradeKey[] = ["stamina", "xp", "fragment"];
    const GEM_LABELS: Record<ArchGemUpgradeKey, string> = {
      stamina: "Max Stamina / Stam mod chance",
      xp: "Archaeology Exp / Exp mod chance",
      fragment: "Fragment Gain / Loot mod chance",
    };
    const eligibleGems: Array<{ key: ArchGemUpgradeKey; displayName: string }> = [];
    for (const key of GEM_KEYS) {
      const maxLvl = GEM_UPGRADE_BONUSES[key].max_level ?? 0;
      const curLvl = clampInt(Number(baseBuild.gemUpgrades[key] ?? 0), 0, maxLvl);
      if (curLvl < maxLvl) eligibleGems.push({ key, displayName: GEM_LABELS[key] });
    }
    const eligibleCards: Array<{ key: string; blockType: BlockType; tier: BlockTier; displayName: string }> = [];
    for (const bt of BLOCK_TYPES) {
      for (const t of BLOCK_CARD_TIERS) {
        if (!getBlockData(t, bt)) continue;
        const key = `${bt},${t}`;
        const cur = (baseBuild.blockCards[key] ?? 0) as CardLevel;
        if (cur === 1) eligibleCards.push({ key, blockType: bt, tier: t, displayName: `${bt} T${t}` });
      }
    }
    const eligibleSkills: Array<{ key: "avadaKeda" | "blockBonker"; displayName: string }> = [];
    if (!baseBuild.avadaKedaEnabled) eligibleSkills.push({ key: "avadaKeda", displayName: "Avada Keda" });
    if (!baseBuild.blockBonkerEnabled) eligibleSkills.push({ key: "blockBonker", displayName: "Block Bonker" });
    const eligibleFragmentUpgrades: Array<{ key: string; displayName: string }> = [];
    for (const [key, info] of Object.entries(FRAGMENT_UPGRADES)) {
      const stageUnlock = clampInt(Number(info.stage_unlock ?? 0), 0, 999);
      const maxLvl = clampInt(Number(info.max_level ?? 0), 0, 999);
      const curLvl = clampInt(Number(baseBuild.fragmentUpgradeLevels[key] ?? 0), 0, maxLvl);
      const ascTier = Number((info as { ascension_tier?: number }).ascension_tier ?? 0);
      if (ascTier > (baseBuild.ascensionLevel ?? 0)) continue;
      if (baseBuild.unlockedStage >= stageUnlock && curLvl < maxLvl) eligibleFragmentUpgrades.push({ key, displayName: String(info.display_name ?? key) });
    }
    const totalOptions = eligibleGems.length + eligibleCards.length + eligibleSkills.length + eligibleFragmentUpgrades.length;
    if (totalOptions === 0) {
      setGemFragNextProgress("No gem, card, skill tree, or fragment upgrades to evaluate (all maxed or already have skills).");
      return;
    }
    setGemFragNextRunning(true);
    setGemFragNextProgress(null);
    setGemFragNextResults(null);
    gemFragNextCancelRef.current = false;
    const hc = typeof navigator !== "undefined" ? navigator.hardwareConcurrency : 4;
    const pool = createWorkerPool(clampInt(Math.max(1, hc - 1), 1, 8));
    const options = mcOptionsFromBuild(baseBuild);
    const seedBase = (Date.now() & 0x7fffffff) >>> 0;
    const N_SIMS = 3000;
    type CostClass = "gem" | "skill" | "common" | "rare" | "epic" | "legendary" | "mythic" | "divine";
    type GemFragResult = { source: "gem" | "card" | "skill" | "fragment"; costClass: CostClass; key: string; displayName: string; meanFrags: number; growthPct: number; cost: number | undefined; perCost: number; allFragmentsGrowthPct: number; perCostAllFragments: number; significant: boolean };
    const results: GemFragResult[] = [];
    try {
      setGemFragNextProgress(`Which Gem/Card/Skill Tree Upgrade next to maximize Fragment gains (${targetFrag}): Baseline…`);
      const baseStats = getTotalStats(baseBuild);
      const polychromeBase = clampInt(Number(baseBuild.fragmentUpgradeLevels["polychrome_bonus"] ?? 0), 0, 1);
      const cardCfgBase = { blockCards: baseBuild.blockCards, polychromeBonus: 0.15 * polychromeBase };
      const baseOut = await pool.run({
        type: "stageLite",
        payload: { stats: baseStats, starting_floor: 1, n_sims: N_SIMS, options, cardCfg: cardCfgBase, seed: seedBase, targetFrag, initialSpeedModHits: baseBuild.permanentSpeedModEnabled ? PERMANENT_SPEED_MOD_INITIAL_HITS : undefined },
      });
      const baseFragSamples = (baseOut as { target_frag_samples?: number[] }).target_frag_samples ?? [];
      const baseTotalSamples = (baseOut as { total_fragments_samples?: number[] }).total_fragments_samples ?? [];
      const baseStatsRes = baseFragSamples.length > 0 ? sampleStats(baseFragSamples) : { mean: 0, std: 0, min: 0, max: 0 };
      const baseMeanFrags = baseStatsRes.mean;
      const baseStd = baseStatsRes.std;
      const baseMeanAllFrags = baseTotalSamples.length > 0 ? sampleStats(baseTotalSamples).mean : 0;

      let idx = 0;
      for (let i = 0; i < eligibleGems.length; i += 1) {
        if (gemFragNextCancelRef.current) break;
        const { key, displayName } = eligibleGems[i]!;
        idx += 1;
        setGemFragNextProgress(`Which Gem/Card/Skill Tree Upgrade next to maximize Fragment gains: ${idx}/${totalOptions} — Gem: ${displayName}`);
        const curLvl = clampInt(Number(baseBuild.gemUpgrades[key] ?? 0), 0, 999);
        const cost = getGemUpgradeCost(key, curLvl, baseBuild.ascensionLevel ?? 0);
        const variantBuild: ArchBuild = {
          ...baseBuild,
          gemUpgrades: { ...baseBuild.gemUpgrades, [key]: curLvl + 1 },
        };
        const stats = getTotalStats(variantBuild);
        const polychromeLvl = clampInt(Number(variantBuild.fragmentUpgradeLevels["polychrome_bonus"] ?? 0), 0, 1);
        const cardCfg = { blockCards: variantBuild.blockCards, polychromeBonus: 0.15 * polychromeLvl };
        const out = await pool.run({
          type: "stageLite",
          payload: { stats, starting_floor: 1, n_sims: N_SIMS, options, cardCfg, seed: seedBase + 40000 + idx, targetFrag, initialSpeedModHits: baseBuild.permanentSpeedModEnabled ? PERMANENT_SPEED_MOD_INITIAL_HITS : undefined },
        });
        const fragSamples = (out as { target_frag_samples?: number[] }).target_frag_samples ?? [];
        const totalSamples = (out as { total_fragments_samples?: number[] }).total_fragments_samples ?? [];
        const varStats = fragSamples.length > 0 ? sampleStats(fragSamples) : { mean: 0, std: 0, min: 0, max: 0 };
        const meanAllFrags = totalSamples.length > 0 ? sampleStats(totalSamples).mean : 0;
        const meanFrags = varStats.mean;
        const growthPct = baseMeanFrags > 0 ? ((meanFrags - baseMeanFrags) / baseMeanFrags) * 100 : 0;
        const allFragmentsGrowthPct = baseMeanAllFrags > 0 ? ((meanAllFrags - baseMeanAllFrags) / baseMeanAllFrags) * 100 : 0;
        const perCost = cost > 0 ? growthPct / cost : 0;
        const perCostAllFragments = cost > 0 ? allFragmentsGrowthPct / cost : 0;
        const seBase = baseStd / Math.sqrt(N_SIMS);
        const seVar = varStats.std / Math.sqrt(N_SIMS);
        const seDiff = Math.sqrt(seBase * seBase + seVar * seVar);
        const seGrowthPct = baseMeanFrags > 0 ? (seDiff / baseMeanFrags) * 100 : 0;
        const significant = seGrowthPct > 0 && Math.abs(growthPct) > 1.96 * seGrowthPct;
        results.push({ source: "gem", costClass: "gem", key, displayName, meanFrags, growthPct, cost, perCost, allFragmentsGrowthPct, perCostAllFragments, significant });
      }
      for (let i = 0; i < eligibleCards.length; i += 1) {
        if (gemFragNextCancelRef.current) break;
        const { key, blockType, tier, displayName } = eligibleCards[i]!;
        idx += 1;
        setGemFragNextProgress(`Which Gem/Card/Skill Tree Upgrade next to maximize Fragment gains: ${idx}/${totalOptions} — Card: ${displayName}`);
        const cost = getCardGemCost(blockType, tier);
        const variantBuild: ArchBuild = {
          ...baseBuild,
          blockCards: { ...baseBuild.blockCards, [key]: 2 },
        };
        const stats = getTotalStats(variantBuild);
        const polychromeLvl = clampInt(Number(variantBuild.fragmentUpgradeLevels["polychrome_bonus"] ?? 0), 0, 1);
        const cardCfg = { blockCards: variantBuild.blockCards, polychromeBonus: 0.15 * polychromeLvl };
        const out = await pool.run({
          type: "stageLite",
          payload: { stats, starting_floor: 1, n_sims: N_SIMS, options, cardCfg, seed: seedBase + 50000 + idx, targetFrag, initialSpeedModHits: baseBuild.permanentSpeedModEnabled ? PERMANENT_SPEED_MOD_INITIAL_HITS : undefined },
        });
        const fragSamples = (out as { target_frag_samples?: number[] }).target_frag_samples ?? [];
        const totalSamples = (out as { total_fragments_samples?: number[] }).total_fragments_samples ?? [];
        const varStats = fragSamples.length > 0 ? sampleStats(fragSamples) : { mean: 0, std: 0, min: 0, max: 0 };
        const meanAllFrags = totalSamples.length > 0 ? sampleStats(totalSamples).mean : 0;
        const meanFrags = varStats.mean;
        const growthPct = baseMeanFrags > 0 ? ((meanFrags - baseMeanFrags) / baseMeanFrags) * 100 : 0;
        const allFragmentsGrowthPct = baseMeanAllFrags > 0 ? ((meanAllFrags - baseMeanAllFrags) / baseMeanAllFrags) * 100 : 0;
        const perCost = cost > 0 ? growthPct / cost : 0;
        const perCostAllFragments = cost > 0 ? allFragmentsGrowthPct / cost : 0;
        const seBase = baseStd / Math.sqrt(N_SIMS);
        const seVar = varStats.std / Math.sqrt(N_SIMS);
        const seDiff = Math.sqrt(seBase * seBase + seVar * seVar);
        const seGrowthPct = baseMeanFrags > 0 ? (seDiff / baseMeanFrags) * 100 : 0;
        const significant = seGrowthPct > 0 && Math.abs(growthPct) > 1.96 * seGrowthPct;
        results.push({ source: "card", costClass: "gem", key, displayName, meanFrags, growthPct, cost, perCost, allFragmentsGrowthPct, perCostAllFragments, significant });
      }
      for (let i = 0; i < eligibleSkills.length; i += 1) {
        if (gemFragNextCancelRef.current) break;
        const { key, displayName } = eligibleSkills[i]!;
        idx += 1;
        setGemFragNextProgress(`Which Gem/Card/Skill Tree Upgrade next to maximize Fragment gains: ${idx}/${totalOptions} — Skill: ${displayName}`);
        const variantBuild: ArchBuild = {
          ...baseBuild,
          ...(key === "avadaKeda" ? { avadaKedaEnabled: true } : { blockBonkerEnabled: true }),
        };
        const stats = getTotalStats(variantBuild);
        const polychromeLvl = clampInt(Number(variantBuild.fragmentUpgradeLevels["polychrome_bonus"] ?? 0), 0, 1);
        const cardCfg = { blockCards: variantBuild.blockCards, polychromeBonus: 0.15 * polychromeLvl };
        const out = await pool.run({
          type: "stageLite",
          payload: { stats, starting_floor: 1, n_sims: N_SIMS, options, cardCfg, seed: seedBase + 60000 + idx, targetFrag, initialSpeedModHits: baseBuild.permanentSpeedModEnabled ? PERMANENT_SPEED_MOD_INITIAL_HITS : undefined },
        });
        const fragSamples = (out as { target_frag_samples?: number[] }).target_frag_samples ?? [];
        const totalSamples = (out as { total_fragments_samples?: number[] }).total_fragments_samples ?? [];
        const varStats = fragSamples.length > 0 ? sampleStats(fragSamples) : { mean: 0, std: 0, min: 0, max: 0 };
        const meanAllFrags = totalSamples.length > 0 ? sampleStats(totalSamples).mean : 0;
        const meanFrags = varStats.mean;
        const growthPct = baseMeanFrags > 0 ? ((meanFrags - baseMeanFrags) / baseMeanFrags) * 100 : 0;
        const allFragmentsGrowthPct = baseMeanAllFrags > 0 ? ((meanAllFrags - baseMeanAllFrags) / baseMeanAllFrags) * 100 : 0;
        const seBase = baseStd / Math.sqrt(N_SIMS);
        const seVar = varStats.std / Math.sqrt(N_SIMS);
        const seDiff = Math.sqrt(seBase * seBase + seVar * seVar);
        const seGrowthPct = baseMeanFrags > 0 ? (seDiff / baseMeanFrags) * 100 : 0;
        const significant = seGrowthPct > 0 && Math.abs(growthPct) > 1.96 * seGrowthPct;
        results.push({ source: "skill", costClass: "skill", key, displayName, meanFrags, growthPct, cost: undefined, perCost: 0, allFragmentsGrowthPct, perCostAllFragments: 0, significant });
      }
      for (let i = 0; i < eligibleFragmentUpgrades.length; i += 1) {
        if (gemFragNextCancelRef.current) break;
        const { key, displayName } = eligibleFragmentUpgrades[i]!;
        idx += 1;
        setGemFragNextProgress(`Which Gem/Card/Skill Tree Upgrade next to maximize Fragment gains: ${idx}/${totalOptions} — Fragment: ${displayName}`);
        const curLvl = clampInt(Number(baseBuild.fragmentUpgradeLevels[key] ?? 0), 0, 999);
        const cost = getUpgradeCost(key, curLvl, baseBuild.ascensionLevel ?? 0) ?? undefined;
        const variantBuild: ArchBuild = {
          ...baseBuild,
          fragmentUpgradeLevels: { ...baseBuild.fragmentUpgradeLevels, [key]: curLvl + 1 },
        };
        const stats = getTotalStats(variantBuild);
        const polychromeLvl = clampInt(Number(variantBuild.fragmentUpgradeLevels["polychrome_bonus"] ?? 0), 0, 1);
        const cardCfg = { blockCards: variantBuild.blockCards, polychromeBonus: 0.15 * polychromeLvl };
        const out = await pool.run({
          type: "stageLite",
          payload: { stats, starting_floor: 1, n_sims: N_SIMS, options, cardCfg, seed: seedBase + 70000 + idx, targetFrag, initialSpeedModHits: baseBuild.permanentSpeedModEnabled ? PERMANENT_SPEED_MOD_INITIAL_HITS : undefined },
        });
        const fragSamples = (out as { target_frag_samples?: number[] }).target_frag_samples ?? [];
        const totalSamples = (out as { total_fragments_samples?: number[] }).total_fragments_samples ?? [];
        const varStats = fragSamples.length > 0 ? sampleStats(fragSamples) : { mean: 0, std: 0, min: 0, max: 0 };
        const meanAllFrags = totalSamples.length > 0 ? sampleStats(totalSamples).mean : 0;
        const meanFrags = varStats.mean;
        const growthPct = baseMeanFrags > 0 ? ((meanFrags - baseMeanFrags) / baseMeanFrags) * 100 : 0;
        const allFragmentsGrowthPct = baseMeanAllFrags > 0 ? ((meanAllFrags - baseMeanAllFrags) / baseMeanAllFrags) * 100 : 0;
        const perCost = cost != null && cost > 0 ? growthPct / cost : 0;
        const perCostAllFragments = cost != null && cost > 0 ? allFragmentsGrowthPct / cost : 0;
        const seBase = baseStd / Math.sqrt(N_SIMS);
        const seVar = varStats.std / Math.sqrt(N_SIMS);
        const seDiff = Math.sqrt(seBase * seBase + seVar * seVar);
        const seGrowthPct = baseMeanFrags > 0 ? (seDiff / baseMeanFrags) * 100 : 0;
        const significant = seGrowthPct > 0 && Math.abs(growthPct) > 1.96 * seGrowthPct;
        const costClass = (FRAGMENT_UPGRADES[key] as { cost_type?: CostClass })?.cost_type ?? "common";
        results.push({ source: "fragment", costClass, key, displayName, meanFrags, growthPct, cost, perCost, allFragmentsGrowthPct, perCostAllFragments, significant });
      }
      results.sort((a, b) => b.growthPct - a.growthPct);
      setGemFragNextResults(results);
      setGemFragNextProgress(gemFragNextCancelRef.current ? "Cancelled." : "Done.");
    } catch (e) {
      setGemFragNextProgress(e instanceof Error ? e.message : String(e));
    } finally {
      pool.terminate();
      setGemFragNextRunning(false);
    }
  }

  function sampleStats(samples: number[]): { mean: number; std: number; min: number; max: number } {
    if (!samples.length) return { mean: 0, std: 0, min: 0, max: 0 };
    let sum = 0;
    let sum2 = 0;
    let min = samples[0]!;
    let max = samples[0]!;
    for (const x of samples) {
      const v = Number(x);
      sum += v;
      sum2 += v * v;
      if (v < min) min = v;
      if (v > max) max = v;
    }
    const mean = sum / samples.length;
    const variance = Math.max(0, sum2 / samples.length - mean * mean);
    return { mean, std: Math.sqrt(variance), min, max };
  }

  function renderHistogramCard(args: {
    samples: number[];
    kind: "stage" | "rate";
    title: ReactNode;
    xLabel: string;
    ariaLabel?: string;
    /** When set and kind === "stage", show flame above highest-stage bar. */
    gradientIdPrefix?: string;
    /** When set, flame is clickable and calls this with the stage of the flame bar (e.g. open stamina-at-stage overview). */
    onFlameClick?: (stage: number) => void;
  }): ReactNode {
    const { samples, kind, title, xLabel, ariaLabel, gradientIdPrefix, onFlameClick } = args;
    if (!samples.length) return null;
    const W = 560;
    const pad = 10;
    const axisH = 26;
    const labelAreaH = kind === "stage" ? 72 : 0; // space above bars for rotated labels
    const H = 184 + labelAreaH;
    const plotTop = pad + labelAreaH;
    const plotH = H - pad * 2 - axisH - labelAreaH;

    const xs = samples.map((x) => Number(x)).filter((x) => Number.isFinite(x));
    if (!xs.length) return null;

    let bins: number[] = [];
    let counts: number[] = [];
    let min = Math.min(...xs);
    let max = Math.max(...xs);
    let step = 1;

    if (kind === "stage") {
      const lo = Math.floor(min);
      const hi = Math.ceil(max);
      const n = Math.max(1, Math.min(40, hi - lo + 1));
      bins = Array.from({ length: n }, (_, i) => lo + i);
      counts = new Array(n).fill(0);
      for (const v of xs) {
        const k = Math.max(lo, Math.min(hi, Math.floor(v)));
        const idx = k - lo;
        if (idx >= 0 && idx < counts.length) counts[idx] += 1;
      }
      step = 1;
    } else {
      const n = 30;
      if (max <= min) max = min + 1;
      step = (max - min) / n;
      counts = new Array(n).fill(0);
      for (const v of xs) {
        const idx = Math.max(0, Math.min(n - 1, Math.floor((v - min) / step)));
        counts[idx] += 1;
      }
      bins = Array.from({ length: n }, (_, i) => min + i * step);
    }

    const maxC = Math.max(1, ...counts);
    const barW = (W - pad * 2) / counts.length;
    const totalSamples = xs.length;
    // Rightmost (highest-stage) bar with count > 0: show flame above it when kind === "stage"
    let highlightBarIndex = -1;
    if (kind === "stage" && gradientIdPrefix != null) {
      for (let i = counts.length - 1; i >= 0; i--) {
        if (counts[i]! > 0) {
          highlightBarIndex = i;
          break;
        }
      }
    }
    const showFlameAboveBar = kind === "stage" && highlightBarIndex >= 0 && gradientIdPrefix != null;
    const bars = counts.map((c, i) => {
      const h = (plotH * c) / maxC;
      const x = pad + i * barW;
      const y = plotTop + plotH - h;
      const binStart = bins[i] ?? 0;
      const binEnd = binStart + step;
      const titleText =
        kind === "stage"
          ? `Stage ${Math.floor(binStart)}: ${c} (${totalSamples > 0 ? ((100 * c) / totalSamples).toFixed(1) : "0"}%)`
          : `${binStart.toFixed(1)}–${binEnd.toFixed(1)}`;
      return (
        <rect key={i} x={x} y={y} width={Math.max(1, barW - 1)} height={h} fill="rgba(92,107,192,0.55)">
          <title>{titleText}</title>
        </rect>
      );
    });

    const barLabels =
      kind === "stage" && totalSamples > 0
        ? counts.map((c, i) => {
            if (c <= 0) return null;
            const h = (plotH * c) / maxC;
            const barLeft = pad + i * barW;
            const barWidth = Math.max(1, barW - 1);
            const barCx = barLeft + barWidth / 2;
            const yBarTop = plotTop + plotH - h;
            const labelY = yBarTop - 4;
            const pct = (100 * c) / totalSamples;
            const labelText = `${formatWithThinSpaces(c, 0)} (${pct.toFixed(1)}%)`;
            return (
              <text
                key={i}
                x={barCx}
                y={labelY}
                textAnchor="start"
                dominantBaseline="middle"
                fontSize="9"
                fontWeight="700"
                fill="rgba(15,23,42,0.9)"
                transform={`rotate(-90, ${barCx}, ${labelY})`}
              >
                {labelText}
              </text>
            );
          })
        : null;

    // X axis ticks / labels (so bins are understandable)
    const tickCount = kind === "stage" ? Math.min(9, counts.length) : 6;
    const stride = kind === "stage" ? Math.max(1, Math.ceil(counts.length / tickCount)) : 1;
    const ticks: Array<{ x: number; label: string }> = [];
    if (kind === "stage") {
      for (let i = 0; i < counts.length; i += stride) {
        const v = bins[i] ?? 0;
        const x = pad + (i + 0.5) * barW;
        ticks.push({ x, label: String(Math.floor(v)) });
      }
    } else {
      // 0%, 25%, 50%, 75%, 100%
      const idxs = [0, 0.25, 0.5, 0.75, 1].map((t) => Math.round((counts.length - 1) * t));
      const uniq = Array.from(new Set(idxs));
      for (const i of uniq) {
        const v = bins[i] ?? min;
        const x = pad + (i + 0.5) * barW;
        ticks.push({ x, label: v.toFixed(1) });
      }
    }

    return (
      <div className="histCard">
        <div className="histTitle">{title}</div>
        <div className="histPlotRow">
          <div className="histYAxis">Frequency</div>
          <svg width="100%" viewBox={`0 0 ${W} ${H}`} className="histSvg" aria-label={ariaLabel ?? (typeof title === "string" ? title : "Histogram")}>
            {showFlameAboveBar ? (
              <defs>
                <filter id="archFlameFade" colorInterpolationFilters="sRGB">
                  <feColorMatrix type="saturate" values="0.55" />
                  <feComponentTransfer>
                    <feFuncA type="linear" slope="0.88" />
                  </feComponentTransfer>
                </filter>
              </defs>
            ) : null}
            {bars}
            {showFlameAboveBar ? (() => {
              const i = highlightBarIndex;
              const c = counts[i]!;
              const barH = (plotH * c) / maxC;
              const barTop = plotTop + plotH - barH;
              const barCenterX = pad + (i + 0.5) * barW;
              const flameW = 28;
              const flameH = 32;
              const flameImg = (
                <image
                  href={assetUrl("sprites/arch/flame.gif")}
                  x={barCenterX - flameW / 2}
                  y={barTop - flameH}
                  width={flameW}
                  height={flameH}
                  filter="url(#archFlameFade)"
                  aria-hidden="true"
                />
              );
              return onFlameClick ? (
                <g
                  key="flame"
                  style={{ cursor: "pointer" }}
                  onClick={(e) => {
                    e.stopPropagation();
                    const stageVal = bins[highlightBarIndex];
                    if (stageVal != null && Number.isFinite(stageVal)) onFlameClick(Math.floor(stageVal));
                  }}
                >
                  {flameImg}
                </g>
              ) : (
                <g key="flame">{flameImg}</g>
              );
            })() : null}
            {barLabels}
            {/* x axis baseline */}
            <line
              x1={pad}
              x2={W - pad}
              y1={H - pad - axisH}
              y2={H - pad - axisH}
              stroke="rgba(15,23,42,0.18)"
              strokeWidth={1}
            />
            {/* tick labels */}
            {ticks.map((t, idx) => (
              <g key={idx}>
                <line x1={t.x} x2={t.x} y1={H - pad - axisH} y2={H - pad - axisH + 4} stroke="rgba(15,23,42,0.18)" strokeWidth={1} />
                <text
                  x={t.x}
                  y={H - pad - 8}
                  textAnchor="middle"
                  fontSize="10"
                  fontWeight="700"
                  fill="rgba(15,23,42,0.70)"
                >
                  {t.label}
                </text>
              </g>
            ))}
          </svg>
        </div>
        <div className="histXAxis">{xLabel}</div>
      </div>
    );
  }

  function formatBlockBreakdownLabel(key: string): string {
    const [blockType, tier] = key.includes(",") ? key.split(",") : [key, "1"];
    const name = blockType.charAt(0).toUpperCase() + blockType.slice(1);
    return tier ? `${name} T${tier}` : name;
  }

  function getFragIconPath(t: BlockType): string {
    return t === "common"
      ? "sprites/archaeology/fragmentcommon.png"
      : t === "rare"
        ? "sprites/archaeology/fragmentrare.png"
        : t === "epic"
          ? "sprites/archaeology/fragmentepic.png"
          : t === "legendary"
            ? "sprites/archaeology/fragmentlegendary.png"
            : t === "mythic"
              ? "sprites/archaeology/fragmentmythic.png"
              : "sprites/archaeology/fragmentdivine.png";
  }

  function renderTieBreakBars(tb: NonNullable<TieBreakReport>): ReactNode {
    if (!tb?.top3?.length) return null;
    // Match desktop visual: grouped horizontal bars with legend outside plot.
    const rows = tb.top3;
    const FRAG_ORDER_BAR: readonly BlockType[] = ARCH_FRAGMENT_TYPES;
    type Series = {
      key: string;
      label: string;
      barClass: string;
      valueFmt: (v: number) => string;
      get: (r: (typeof rows)[number]) => number;
      fragType?: BlockType;
    };

    const series: Series[] =
      tb.mode === "stage"
        ? [
            { key: "frags", label: "Fragments/h", barClass: "tbBarFrag", valueFmt: (v) => v.toFixed(2), get: (r) => Number(r.secondary ?? 0) },
            { key: "xp", label: "XP/h", barClass: "tbBarXp", valueFmt: (v) => v.toFixed(1), get: (r) => Number(r.tertiary ?? 0) },
          ]
        : tb.mode === "XP"
          ? (() => {
              const fragFirst = tb.xpTieBreakSecondary !== "avg_max_stage";
              const fragsBar = {
                key: "frags",
                label: "Fragments/h",
                barClass: "tbBarFrag",
                valueFmt: (v: number) => v.toFixed(2),
                get: (r: (typeof rows)[number]) => Number((fragFirst ? r.secondary : r.tertiary) ?? 0),
              };
              const stageBar = {
                key: "stage",
                label: "Avg max stage",
                barClass: "tbBarStage",
                valueFmt: (v: number) => v.toFixed(2),
                get: (r: (typeof rows)[number]) => Number((fragFirst ? r.tertiary : r.secondary) ?? 0),
              };
              return fragFirst ? [fragsBar, stageBar] : [stageBar, fragsBar];
            })()
          : tb.mode === "frag" && tb.targetFrag
            ? (() => {
                const idx = FRAG_ORDER_BAR.indexOf(tb.targetFrag);
                const L = FRAG_ORDER_BAR.length;
                const secFrag = idx > 0 ? FRAG_ORDER_BAR[idx - 1]! : (idx + 1 < L ? FRAG_ORDER_BAR[idx + 1]! : null);
                const terFrag = idx > 0 ? (idx + 1 < L ? FRAG_ORDER_BAR[idx + 1]! : null) : (idx + 2 < L ? FRAG_ORDER_BAR[idx + 2]! : null);
                const arr: Series[] = [
                  {
                    key: "primary",
                    label: `${tb.targetFrag.toUpperCase()}/h`,
                    barClass: "tbBarFrag",
                    valueFmt: (v) => v.toFixed(2),
                    get: (r) => Number(r.primary ?? 0),
                    fragType: tb.targetFrag,
                  },
                ];
                if (secFrag != null) {
                  arr.push({
                    key: "secondary",
                    label: `${secFrag.toUpperCase()}/h`,
                    barClass: "tbBarFrag",
                    valueFmt: (v) => v.toFixed(2),
                    get: (r) => Number(r.secondary ?? 0),
                    fragType: secFrag,
                  });
                }
                if (terFrag != null) {
                  arr.push({
                    key: "tertiary",
                    label: `${terFrag.toUpperCase()}/h`,
                    barClass: "tbBarFrag",
                    valueFmt: (v) => v.toFixed(2),
                    get: (r) => Number(r.tertiary ?? 0),
                    fragType: terFrag,
                  });
                }
                arr.push({
                  key: "xp",
                  label: "XP/h",
                  barClass: "tbBarXp",
                  valueFmt: (v) => v.toFixed(1),
                  get: (r) => Number((r as { xpPerHour?: number }).xpPerHour ?? 0),
                });
                return arr;
              })()
            : [
                { key: "frags", label: "Fragments/h", barClass: "tbBarFrag", valueFmt: (v) => v.toFixed(2), get: (r) => Number(r.primary ?? 0) },
                { key: "xp", label: "XP/h", barClass: "tbBarXp", valueFmt: (v) => v.toFixed(1), get: (r) => Number(r.secondary ?? 0) },
              ];

    const maxByKey: Record<string, number> = {};
    for (const s of series) {
      maxByKey[s.key] = Math.max(1, ...rows.map((r) => s.get(r)));
    }

    const labelFor = (r: (typeof rows)[number]) => {
      const d = r.dist;
      const parts = [
        `STR:${d.strength ?? 0}`,
        `AGI:${d.agility ?? 0}`,
        `PER:${d.perception ?? 0}`,
        `INT:${d.intellect ?? 0}`,
        `LCK:${d.luck ?? 0}`,
      ];
      return `${r.label}: ${parts.join(" | ")}`;
    };

    return (
      <div className="tbWrap">
        <div className="tbPlot">
          {rows.map((r) => {
            return (
              <div key={r.label} className="tbRow">
                <div className="tbLabel mono">{labelFor(r)}</div>
                <div className="tbBars">
                  {series.map((s) => {
                    const v = s.get(r);
                    const max = maxByKey[s.key] ?? 1;
                    const pct = Math.max(0, Math.min(1, max > 0 ? v / max : 0));
                    return (
                      <div key={s.key} className={`tbBarLine ${s.fragType != null ? "tbBarLineWithIcon" : ""}`}>
                        {s.fragType != null ? (
                          <Sprite path={getFragIconPath(s.fragType)} alt="" className="iconSmall tbBarFragIcon" />
                        ) : null}
                        <div className={`tbBar ${s.barClass}`} style={{ width: `${(pct * 100).toFixed(1)}%` }} />
                        <div className="tbValue mono">{s.valueFmt(v)}</div>
                      </div>
                    );
                  })}
                </div>
              </div>
            );
          })}
        </div>
        <div className="tbLegend">
          <div className="tbLegendTitle">Legend</div>
          {series.map((s) => (
            <div key={s.key} className="tbLegendItem">
              {s.fragType != null ? (
                <>
                  <Sprite path={getFragIconPath(s.fragType)} alt="" className="iconSmall" />
                  <span className="tbLegendLabel">{s.label}</span>
                </>
              ) : (
                <>
                  <span className={`tbSwatch ${s.barClass === "tbBarFrag" ? "tbSwatchFrag" : s.barClass === "tbBarXp" ? "tbSwatchXp" : "tbSwatchStage"}`} />{" "}
                  {s.label}
                </>
              )}
            </div>
          ))}
        </div>
      </div>
    );
  }

  const visibleMcLog = useMemo(() => mcLog.filter((e) => e.mcType !== "det"), [mcLog]);
  const stageLogEntries = useMemo(() => visibleMcLog.filter((e) => e.mcType === "stage"), [visibleMcLog]);
  const fragmentLogEntries = useMemo(() => visibleMcLog.filter((e) => e.mcType === "frag"), [visibleMcLog]);
  const activeLog = useMemo(() => (activeLogId ? visibleMcLog.find((x) => x.id === activeLogId) ?? null : null), [activeLogId, visibleMcLog]);
  const openLog = useMemo(() => (openLogId ? visibleMcLog.find((x) => x.id === openLogId) ?? null : null), [openLogId, visibleMcLog]);

  useEffect(() => {
    function onKeyDown(ev: KeyboardEvent) {
      if (ev.key !== "Escape") return;
      if (openLogId) {
        setOpenLogId(null);
        return;
      }
      if (mcWindowOpen) {
        setMcWindowOpen(false);
      }
    }
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [openLogId, mcWindowOpen]);

  const mcProgressFrac = useMemo(() => {
    if (!mcProgress) return null as null | { done: number; total: number; text: string };
    const m = mcProgress.match(/(\d+)\s*\/\s*(\d+)/);
    if (!m) return null;
    const done = Number(m[1]);
    const total = Number(m[2]);
    if (!Number.isFinite(done) || !Number.isFinite(total) || total <= 0) return null;
    return { done, total, text: `${done}/${total}` };
  }, [mcProgress]);

  const mcPhaseLabel = useMemo(() => {
    if (!mcProgress) return null as null | string;
    const defaultScreening = 100;
    const defaultRefinement = 200;
    const refinementN = mcSettings.devTuning ? clampInt(Number(mcSettings.refinementSims ?? defaultRefinement), 0, 999999) : defaultRefinement;
    const totalPhases = refinementN > 0 ? 2 : 1;
    if (/phase\s*1\s*:/i.test(mcProgress)) return `Phase 1/${totalPhases}`;
    if (/phase\s*2\s*:/i.test(mcProgress)) return `Phase 2/${totalPhases}`;
    if (/phase\s*3\s*:/i.test(mcProgress) || /final sims/i.test(mcProgress)) return "Final";
    return null;
  }, [mcProgress, mcSettings.devTuning, mcSettings.refinementSims]);

  return (
    <div className="container">
      <div className="header">
        <div>
          <h1 className="title">Archaeology Simulator</h1>
          <p className="subtitle">
            Monte Carlo optimizers (multi-core). Saved MC runs can be reopened.
          </p>
        </div>
        <div className="badge">MC • Multi-core</div>
      </div>

      <div className="archWarningBanner" role="status">
        <span className="archWarningIcon" aria-hidden>
          <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M12 9v4m0 4h.01M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z" />
          </svg>
        </span>
        <div className="archWarningText">
          Since 2.1 (end of Feb 2026) a lot of stats changed in Archaeology. All changes which are shown in the{" "}
          <a href="https://shminer.miraheze.org/wiki/Archaeology" target="_blank" rel="noopener noreferrer">
            wiki
          </a>{" "}
          here are implemented! (as per March 2026)
        </div>
      </div>

      <div className="panel archSetupPanel" style={{ background: "var(--tier1)" }}>
        <div className="panelHeader" style={{ marginBottom: 8, display: "flex", flexWrap: "wrap", alignItems: "center", justifyContent: "space-between", gap: 8 }}>
          <div>
            <h2 className="panelTitle">Run setup</h2>
            <p className="panelHint">
              Calc stage: <span className="mono">{calcStage}</span>
            </p>
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap" }}>
            <span className="small">Ascension:</span>
            <span className="mono" style={{ fontWeight: 800 }}>
              {ascensionLabel(build.ascensionLevel ?? 0)}
            </span>
            <Tooltip
              content={{
                title: "Ascension",
                sections: [
                  {
                    heading: "Levels",
                    lines: [
                      "No Ascension: pre-ascension archaeology (no Divine blocks).",
                      "Ascension 1: Divine blocks and Divinity skill unlock.",
                      "Ascension 2: Tier 4 blocks and Corruption skill unlock.",
                    ],
                  },
                  {
                    heading: "Costs",
                    lines: [
                      "After Ascension 1, base fragment upgrades cost 5× and gem upgrades cost 50×.",
                      "Ascension-only upgrades use their own cost tables.",
                    ],
                  },
                ],
              }}
            />
          </div>
        </div>

        <div className="archSetupGrid" style={{ marginBottom: 8 }}>
          <div className="archSetupCell archSetupCellAscension" style={{ gridColumn: "1 / -1" }}>
            <div className="label" style={{ marginBottom: 6 }}>
              <span>Ascension state</span>
            </div>
            <div className="btnRow" style={{ flexWrap: "wrap" }}>
              {([0, 1, 2] as const).map((lvl) => {
                const active = (build.ascensionLevel ?? 0) === lvl;
                return (
                  <button
                    key={lvl}
                    type="button"
                    className={active ? "btn" : "btn btnSecondary"}
                    disabled={mcRunning}
                    onClick={() => setAscensionLevel(lvl)}
                  >
                    {ascensionLabel(lvl)}
                  </button>
                );
              })}
            </div>
          </div>
        </div>

        <div className="archSetupGrid">
          <div className="archSetupCell" style={{ background: "var(--tier3)" }}>
            <div className="label">
              <span>
                Unlocked stage
                <Tooltip content={{ title: "Unlocked stage", lines: ["Used to lock upgrades/cards in this simulator."] }} />
              </span>
              <span className="mono">{build.unlockedStage}</span>
            </div>
            <NumberField
              value={build.unlockedStage}
              min={1}
              max={999}
              onCommit={(n) => setBuild((s) => ({ ...s, unlockedStage: n }))}
            />
          </div>

          <div className="archSetupCell" style={{ background: "var(--tier3)" }}>
            <div className="label">
              <span>
                Arch level
                <Tooltip content={{ title: "Arch level", lines: ["Total stats points available to distribute (and used by the MC optimizers)."] }} />
              </span>
              <span className="mono">{build.archLevel}</span>
            </div>
            <input className="input" type="number" min={0} step={1} value={build.archLevel} onChange={(e) => setArchLevel(Number(e.target.value))} />
            <div className="small" style={{ marginTop: 6 }}>
              Stats used: <span className="mono">{totalSkillPoints}</span> / <span className="mono">{skillPointBudget}</span>
              {getBonusSkillPoints(build) > 0 ? (
                <>
                  {" "}
                  (<span className="mono">{build.archLevel}</span> level + <span className="mono">{getBonusSkillPoints(build)}</span> ascension)
                </>
              ) : null}
            </div>
          </div>
        </div>

        <div className="btnRow" style={{ marginTop: 10 }}>
          <span className="nudgeTarget">
            <span className="nudgeArrow" aria-hidden="true">
              ➜
            </span>
            <button className="btn btnImportant" type="button" onClick={() => setMcWindowOpen(true)}>
              Open Simulation
            </button>
          </span>
          <label className="archToggleRow" style={{ display: "inline-flex", alignItems: "center", gap: 6, marginLeft: 8 }}>
            <input
              type="checkbox"
              checked={build.permanentSpeedModEnabled ?? false}
              onChange={(e) => setBuild((s) => ({ ...s, permanentSpeedModEnabled: e.target.checked }))}
              aria-describedby="arch-permanent-speed-mod-desc"
            />
            <span id="arch-permanent-speed-mod-desc">Permanent Speed Mod</span>
            <Tooltip
              content={{
                title: "Permanent Speed Mod",
                lines: [
                  "When on, every simulation run starts with speed mod effectively always active (2× attack speed).",
                  "Use this when you have so many speed mod procs that you never run out in practice.",
                ],
              }}
              label="?"
            />
          </label>
          <button
            className={resetAllArmed ? "btn btnDanger" : "btn btnSecondary"}
            type="button"
            onClick={() => {
              if (!resetAllArmed) {
                setResetAllArmed(true);
                setResetMcLogArmed(false);
                return;
              }
              setResetAllArmed(false);
              if (!confirmDanger("Reset all Arch settings? This will reset stages, arch level, stats, upgrades, cards, and toggles.")) return;
              setBuild(defaultBuild());
            }}
            disabled={mcRunning}
            title={resetAllArmed ? "Click again to confirm (then confirm dialog)." : "Click once to arm, click again to confirm."}
          >
            {resetAllArmed ? "Confirm reset all" : "Reset all"}
          </button>
          <button
            className={resetMcLogArmed ? "btn btnDanger" : "btn btnSecondary"}
            type="button"
            onClick={() => {
              if (!resetMcLogArmed) {
                setResetMcLogArmed(true);
                setResetAllArmed(false);
                return;
              }
              setResetMcLogArmed(false);
              if (!confirmDanger("Reset MC results log? This will delete all saved MC runs in this browser.")) return;
              setMcLog([]);
              setActiveLogId(null);
            }}
            disabled={mcRunning}
            title={resetMcLogArmed ? "Click again to confirm (then confirm dialog)." : "Click once to arm, click again to confirm."}
          >
            {resetMcLogArmed ? "Confirm reset MC log" : "Reset MC log"}
          </button>
        </div>
      </div>

      <div className="archGrid archGridNoMc">
        {/* Column 1: build (collapsible) */}
        <div style={{ display: "grid", gap: 12 }}>
          <Collapsible
            id="arch-skills"
            title={
              <span style={{ display: "inline-flex", alignItems: "center", gap: 8 }}>
                <span>Skills</span>
                <Tooltip content={SKILLS_TOOLTIP} />
              </span>
            }
            defaultExpanded={false}
          >
            <div className="small" style={{ marginBottom: 8 }}>
              Toggle skills that affect the simulation.
            </div>
            <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
              <button className="btn btnSecondary" type="button" onClick={() => setBuild((s) => ({ ...s, enrageEnabled: !s.enrageEnabled }))}>
                <Sprite path="sprites/archaeology/Archaeology_Ability_Enrage.png" alt="Enrage" className="iconSmall" /> Enrage: <SkillToggleState on={build.enrageEnabled} />
              </button>
              <button className="btn btnSecondary" type="button" onClick={() => setBuild((s) => ({ ...s, flurryEnabled: !s.flurryEnabled }))}>
                <Sprite path="sprites/archaeology/Archaeology_Ability_Flurry.png" alt="Flurry" className="iconSmall" /> Flurry: <SkillToggleState on={build.flurryEnabled} />
              </button>
              <button className="btn btnSecondary" type="button" onClick={() => setBuild((s) => ({ ...s, quakeEnabled: !s.quakeEnabled }))}>
                <Sprite path="sprites/archaeology/Archaeology_Ability_Quake.png" alt="Quake" className="iconSmall" /> Quake: <SkillToggleState on={build.quakeEnabled} />
              </button>
              <button className="btn btnSecondary" type="button" onClick={() => setBuild((s) => ({ ...s, avadaKedaEnabled: !s.avadaKedaEnabled }))}>
                <Sprite path="sprites/archaeology/avadakeda.png" alt="Avada Keda" className="iconSmall" /> Avada Keda: <SkillToggleState on={build.avadaKedaEnabled} />
              </button>
              <button className="btn btnSecondary" type="button" onClick={() => setBuild((s) => ({ ...s, blockBonkerEnabled: !s.blockBonkerEnabled }))}>
                <Sprite path="sprites/archaeology/blockbonker.png" alt="Block Bonker" className="iconSmall" /> Block Bonker: <SkillToggleState on={build.blockBonkerEnabled} />
              </button>
            </div>
          </Collapsible>

          <Collapsible
            id="arch-player-stats"
            title={
              <span style={{ display: "inline-flex", alignItems: "center", gap: 8 }}>
                <span>Player stats (OPTIONAL)</span>
                <Tooltip content={PLAYER_STATS_TOOLTIP} />
              </span>
            }
            defaultExpanded={false}
            headerRight={
              <span className="mono">
                {totalSkillPoints}/{skillPointBudget}
              </span>
            }
          >
            <div className="sectionTitle">Stats</div>
            <div className="small" style={{ marginBottom: 8 }}>
              Spend your <span className="mono">Arch level</span> points here.
            </div>
            {getVisibleSkills(build.ascensionLevel ?? 0).map((statKey) => {
              const meta = getSkillDisplay(statKey);
              const cap = getSkillPointCap(build, statKey);
              const v = clampInt(Number(build.skillPoints[statKey] ?? 0), 0, cap);
              return (
                <div key={statKey} className="row" style={{ marginBottom: 8 }}>
                  <div className="label" style={{ display: "flex", alignItems: "center", gap: 6 }}>
                    <Sprite path={meta.icon} alt={meta.label} className="iconSmall" />
                    <span className="mono">{meta.short}</span>
                    <Tooltip content={STAT_TOOLTIPS[statKey]} />
                    <span className="mono">
                      {v} / {cap}
                    </span>
                  </div>
                  <div className="btnRow" style={{ marginTop: 0 }}>
                    <button className="btn btnSecondary" type="button" onClick={() => setSkill(statKey, -5)} disabled={v <= 0}>
                      −5
                    </button>
                    <button className="btn btnSecondary" type="button" onClick={() => setSkill(statKey, -1)} disabled={v <= 0}>
                      −
                    </button>
                    <button className="btn" type="button" onClick={() => setSkill(statKey, +1)} disabled={v >= cap || totalSkillPoints >= skillPointBudget}>
                      +
                    </button>
                    <button className="btn btnSecondary" type="button" onClick={() => setSkill(statKey, +5)} disabled={v >= cap || totalSkillPoints >= skillPointBudget}>
                      +5
                    </button>
                  </div>
                </div>
              );
            })}

            <div className="sectionTitle" style={{ display: "flex", alignItems: "center", gap: 6 }}>
              Run MC Simulation of above build
              <Tooltip
                content={{
                  title: "Build MC",
                  lines: [
                    "Runs N Monte Carlo runs with the current player stats (no optimization).",
                    "Results show the same metrics and plots as the Stage/XP/Frag optimizer results.",
                  ],
                }}
              />
            </div>
            <div className="small" style={{ marginBottom: 6 }}>
              Run <span className="mono">N</span> Monte Carlo runs with the current player stats. Results open in the same results window as the Stage/XP/Frag optimizers.
            </div>
            <div className="row" style={{ marginBottom: 8, flexWrap: "wrap", gap: 8, alignItems: "center" }}>
              <label style={{ display: "flex", alignItems: "center", gap: 6 }}>
                <span className="mono">N</span>
                <input
                  type="number"
                  inputMode="numeric"
                  min={100}
                  max={500000}
                  step={500}
                  value={buildMcN}
                  onChange={(e) => setBuildMcN(clampInt(Number(e.target.value) || 5000, 100, 500000))}
                  className="mono"
                  style={{ width: 88, padding: "4px 6px" }}
                  disabled={buildMcRunning}
                />
              </label>
              <button
                type="button"
                className="btn"
                onClick={() => runBuildMc()}
                disabled={buildMcRunning || mcRunning}
              >
                Run Simulation
              </button>
              {buildMcProgress != null ? (
                <span className="small mono" style={{ color: "var(--muted)" }}>
                  {buildMcProgress}
                </span>
              ) : null}
            </div>

            <div className="sectionTitle">Derived stats</div>
            {(() => {
              const bb = getBlockBonkerBonus(build);
              return bb.highest_stage > 0 ? (
                <div className="small" style={{ marginBottom: 4, color: "var(--muted)" }}>
                  Block Bonker: ON (unlocked {build.unlockedStage} → +{bb.highest_stage}% dmg/stam, +{bb.highest_stage} speed mod)
                </div>
              ) : build.blockBonkerEnabled ? (
                <div className="small" style={{ marginBottom: 4, color: "var(--muted)" }}>
                  Block Bonker: ON but unlocked stage 1 → no bonus. Set Unlocked stage to match in-game.
                </div>
              ) : (
                <div className="small" style={{ marginBottom: 4, color: "var(--muted)" }}>
                  Block Bonker: OFF — Damage/Stamina below exclude this bonus. Turn ON and set Unlocked stage to match in-game.
                </div>
              );
            })()}
            <div className="kv" style={{ background: "var(--tier1)" }}>
              <kbd>Damage</kbd>
              <div className="mono">{formatInt(stats.total_damage)}</div>
              <kbd>Armor Penetration</kbd>
              <div className="mono">{formatInt(stats.armor_pen)}</div>
              <kbd>Max Stamina</kbd>
              <div className="mono">{formatInt(stats.max_stamina)}</div>
              <kbd>Crit Chance</kbd>
              <div className="mono">{formatPct(stats.crit_chance, 2)}</div>
              <kbd>Crit Damage</kbd>
              <div className="mono">{stats.crit_damage.toFixed(3)}x</div>
              <kbd>Super Crit Chance</kbd>
              <div className="mono">{formatPct(stats.super_crit_chance, 2)}</div>
              <kbd>Super Crit Damage</kbd>
              <div className="mono">{stats.super_crit_dmg_mult.toFixed(3)}x</div>
              <kbd>Ultra Crit Chance</kbd>
              <div className="mono">{formatPct(stats.ultra_crit_chance, 2)}</div>
              <kbd>Ultra Crit Damage</kbd>
              <div className="mono">{stats.ultra_crit_dmg_mult.toFixed(3)}x</div>
              <kbd>Ability Instacharge</kbd>
              <div className="mono">{formatPct(stats.ability_instacharge, 2)}</div>
              <kbd>
                Arch Exp Gain (ingame)
                <Tooltip
                  content={{
                    title: "Arch Exp Gain (ingame)",
                    lines: [
                      "Matches the game’s Stats menu: Archaeology Exp Gain from fragment upgrades only.",
                      "Total XP mult below also includes gem upgrades, 2× stat cap, and Intellect.",
                    ],
                  }}
                />
              </kbd>
              <div className="mono">{stats.arch_xp_mult.toFixed(3)}x</div>
              <kbd>
                Total XP mult
                <Tooltip
                  content={{
                    title: "Total XP mult",
                    lines: [
                      "Arch Exp Gain × gem XP × 2× stat cap upgrade × Intellect skill. Used for sim XP/h.",
                      "In-game only shows the Arch Exp Gain part.",
                    ],
                  }}
                />
              </kbd>
              <div className="mono">{stats.xp_gain_total.toFixed(3)}x</div>
              <kbd>Fragment Gain</kbd>
              <div className="mono">{stats.fragment_mult.toFixed(3)}x</div>
            </div>

            <div className="sectionTitle">Mods</div>
            <div className="small" style={{ marginBottom: 8 }}>
              Mod chances are <span className="mono">per block hit</span>.
            </div>
            <div className="small" style={{ marginBottom: 6 }}>
              Speed Mod: when multiple blocks trigger it, <strong>duration</strong> adds (more hits at 2× speed); speed stays 2×. Flurry: 2× speed for 5 <strong>seconds</strong> (fixed). Speed Mod and Flurry <strong>stack multiplicatively</strong> (2× × 2× = 4× when both active).
            </div>
            <div className="kv" style={{ background: "var(--tier1)" }}>
              <kbd>EXP Mod Chance</kbd>
              <div className="mono">{formatPct(stats.exp_mod_chance, 2)}</div>
              <kbd>EXP Mod Gain</kbd>
              <div className="mono">{stats.exp_mod_gain.toFixed(2)}x</div>

              <kbd>Loot Mod Chance</kbd>
              <div className="mono">{formatPct(stats.loot_mod_chance, 2)}</div>
              <kbd>Loot Mod Gain</kbd>
              <div className="mono">{stats.loot_mod_multiplier.toFixed(2)}x</div>

              <kbd>Speed Mod Chance</kbd>
              <div className="mono">{formatPct(stats.speed_mod_chance, 2)}</div>
              <kbd>Speed Mod Gain</kbd>
              <div className="mono">{stats.speed_mod_gain.toFixed(1)}</div>

              <kbd>Stamina Mod Chance</kbd>
              <div className="mono">{formatPct(stats.stamina_mod_chance, 2)}</div>
              <kbd>Stamina Mod Gain</kbd>
              <div className="mono">{stats.stamina_mod_gain.toFixed(1)}</div>
            </div>
          </Collapsible>
        </div>

        {/* Column 2: upgrades/cards */}
        <div style={{ display: "grid", gap: 6 }}>
          <Collapsible
            id="arch-diverse-upgrades"
            title="Diverse Upgrades (Mid-Late Game)"
            defaultExpanded={false}
            className="archDiverseUpgrades"
          >
            <div className="panel archDiverseSection" style={{ padding: "8px 10px" }}>
              <div
                className="fragmentUpgradeRow"
                style={{ display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap", marginBottom: 6 }}
              >
                <img
                  src="https://static.wikitide.net/shminerwiki/thumb/1/10/Axolotl_Quest.png/36px-Axolotl_Quest.png"
                  alt=""
                  width={36}
                  height={36}
                  style={{ flexShrink: 0 }}
                />
                <span style={{ color: "var(--text, inherit)" }}>
                  Axolotl Skin Quest (rank 0 = +3%, +3% per rank)
                  <Tooltip content={{ title: "Axolotl Skin Quest", lines: ["When owned, rank 0 already gives +3% fragment gain; each rank adds another +3% (e.g. rank 0 = 1.03×, rank 5 = 1.18×)."] }} />
                </span>
                <label style={{ display: "flex", alignItems: "center", cursor: "pointer" }}>
                  <input
                    type="checkbox"
                    checked={build.axolotlQuestOwned ?? false}
                    onChange={(e) => setBuild((s) => ({ ...s, axolotlQuestOwned: e.target.checked }))}
                    aria-label="Have Axolotl Skin Quest"
                  />
                </label>
                {build.axolotlQuestOwned ? (
                  <>
                    <span className="small mono">Rank:</span>
                    <input
                      className="input mono"
                      type="number"
                      min={0}
                      max={20}
                      step={1}
                      value={build.axolotlQuestRank ?? 0}
                      onChange={(e) => setBuild((s) => ({ ...s, axolotlQuestRank: clampInt(Number(e.target.value), 0, 20) }))}
                      style={{ width: 56 }}
                    />
                  </>
                ) : null}
              </div>
              <div
                className="fragmentUpgradeRow"
                style={{ display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap" }}
              >
                <img
                  src="https://static.wikitide.net/shminerwiki/thumb/d/d3/Cave_Legendary_Fish.png/45px-Cave_Legendary_Fish.png"
                  alt=""
                  width={36}
                  height={36}
                  style={{ flexShrink: 0, objectFit: "contain" }}
                />
                <span style={{ color: "var(--text, inherit)" }}>
                  Level 1 Tribute (Cave Legendary Fish)
                  <Tooltip content={{ title: "Level 1 Tribute (Cave Legendary Fish)", lines: ["Fragment gain +0.25% per mythic chest owned (additive)."] }} />
                </span>
                <label style={{ display: "flex", alignItems: "center", cursor: "pointer" }}>
                  <input
                    type="checkbox"
                    checked={build.level1TributeEnabled ?? false}
                    onChange={(e) => setBuild((s) => ({ ...s, level1TributeEnabled: e.target.checked }))}
                    aria-label="Level 1 Tribute enabled"
                  />
                </label>
                {build.level1TributeEnabled ? (
                  <>
                    <span className="small mono">Mythic chests:</span>
                    <input
                      className="input mono"
                      type="number"
                      min={0}
                      max={999}
                      step={1}
                      value={build.mythicChestsOwned ?? 0}
                      onChange={(e) => setBuild((s) => ({ ...s, mythicChestsOwned: clampInt(Number(e.target.value), 0, 999) }))}
                      style={{ width: 88 }}
                    />
                  </>
                ) : null}
              </div>
              <div
                className="fragmentUpgradeRow"
                style={{ display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap" }}
              >
                <img
                  src="https://static.wikitide.net/shminerwiki/thumb/5/55/Archbundle_vp.png/60px-Archbundle_vp.png"
                  alt=""
                  width={36}
                  height={36}
                  style={{ flexShrink: 0, objectFit: "contain" }}
                />
                <span style={{ color: "var(--text, inherit)" }}>
                  Archaeology Bundle! (1.25× fragment gain)
                  <Tooltip content={{ title: "Archaeology Bundle!", lines: ["When enabled: 1.25× fragment gain multiplier."] }} />
                </span>
                <label style={{ display: "flex", alignItems: "center", cursor: "pointer" }}>
                  <input
                    type="checkbox"
                    checked={build.archBundleEnabled ?? false}
                    onChange={(e) => setBuild((s) => ({ ...s, archBundleEnabled: e.target.checked }))}
                    aria-label="Archaeology Bundle enabled"
                  />
                </label>
              </div>
            </div>
          </Collapsible>

          <Collapsible
            id="arch-upgrade-recommendations"
            title="Upgrade recommendations"
            defaultExpanded={false}
          >
            <div className="panel" style={{ background: "var(--tier2)", padding: "6px 8px" }}>
              <Collapsible
                id="arch-which-upgrade-next"
                title="Which Fragment Upgrade next to maximize Stage Push?"
                defaultExpanded={false}
                className="archWhichNextGold"
                headerRight={
                  <Tooltip
                    content={{
                      title: "Which Upgrade Next?",
                      sections: [
                        {
                          heading: "Prerequisite",
                          lines: [
                            "Requires a Stage Push MC result in the log.",
                            "Uses the Top #1 skill build from the selected result.",
                          ],
                        },
                        {
                          heading: "What it does",
                          lines: [
                            "For each unlocked, non-maxed fragment upgrade, simulates +1 level with N=3000 runs.",
                            "Ranks by mean floors/run. Best upgrade is shown first.",
                            "* = not statistically significant (95% CI includes 0).",
                          ],
                        },
                      ],
                    }}
                  />
                }
              >
                <div className="small" style={{ marginBottom: 8 }}>
                  {stageLogEntries.length === 0 ? (
                    <div className="pillLocked" style={{ padding: 8 }}>
                      Run a Stage Push MC first. No Stage result in the log.
                    </div>
                  ) : (
                    <>
                      <div style={{ display: "flex", flexWrap: "wrap", gap: 8, alignItems: "center", marginBottom: 8 }}>
                        <label className="small">
                          Reference:
                          <select
                            className="mono"
                            style={{ marginLeft: 6 }}
                            value={upgradeNextRefId ?? stageLogEntries[0]?.id ?? ""}
                            onChange={(e) => setUpgradeNextRefId(e.target.value || null)}
                            disabled={upgradeNextRunning || mcRunning}
                          >
                            {stageLogEntries.map((e) => (
                              <option key={e.id} value={e.id}>
                                {e.label} — {e.metrics.floorsPerRun.toFixed(2)} floors/run ({new Date(e.createdAt).toLocaleString()})
                              </option>
                            ))}
                          </select>
                        </label>
                        <button
                          className="btn"
                          type="button"
                          onClick={() => runUpgradeNext()}
                          disabled={upgradeNextRunning || mcRunning || stageLogEntries.length === 0}
                        >
                          {upgradeNextRunning ? "Running…" : "Run (N=3000)"}
                        </button>
                        {upgradeNextRunning ? (
                          <button className="btn btnSecondary" type="button" onClick={() => { upgradeNextCancelRef.current = true; }} disabled={!upgradeNextRunning}>
                            Cancel
                          </button>
                        ) : null}
                      </div>
                      {upgradeNextProgress ? (
                        <div className="small mono" style={{ marginBottom: 8 }}>
                          {upgradeNextProgress}
                        </div>
                      ) : null}
                      {upgradeNextResults && upgradeNextResults.length > 0 ? (() => {
                        const rs = upgradeNextResults;
                        const FRAG_ORDER = ARCH_FRAGMENT_TYPES;
                        const heatPct = (v: number, lo: number, hi: number) =>
                          hi > lo ? Math.max(0, Math.min(100, ((v - lo) / (hi - lo)) * 100)) : 50;
                        const byCostType = (ct: (typeof FRAG_ORDER)[number]) => rs.filter((r) => r.costType === ct);
                        const minMaxPerType = Object.fromEntries(
                          FRAG_ORDER.map((ct) => {
                            const group = byCostType(ct);
                            const floors = group.map((r) => r.meanFloors);
                            const growth = group.map((r) => r.growthPct);
                            const perCost = group.map((r) => r.perCost).filter((v): v is number => v != null && Number.isFinite(v));
                            return [
                              ct,
                              {
                                minFloors: floors.length ? Math.min(...floors) : 0,
                                maxFloors: floors.length ? Math.max(...floors) : 0,
                                minGrowth: growth.length ? Math.min(...growth) : 0,
                                maxGrowth: growth.length ? Math.max(...growth) : 0,
                                minPerCost: perCost.length ? Math.min(...perCost) : 0,
                                maxPerCost: perCost.length ? Math.max(...perCost) : 0,
                              },
                            ];
                          }),
                        ) as Record<(typeof FRAG_ORDER)[number], { minFloors: number; maxFloors: number; minGrowth: number; maxGrowth: number; minPerCost: number; maxPerCost: number }>;
                        let rowNum = 0;
                        return (
                          <div className="small">
                            <div style={{ fontWeight: 700, marginBottom: 4 }}>Best next upgrade (by fragment type, sorted by Floors/run +%):</div>
                            <div className="small" style={{ marginBottom: 8, display: "flex", alignItems: "center", gap: 16, flexWrap: "wrap" }}>
                              <span
                                style={{
                                  color: "hsl(120, 75%, 35%)",
                                  textShadow: "0 0 8px hsla(120, 75%, 45%, 0.9), 0 0 14px hsla(120, 75%, 50%, 0.5)",
                                  fontWeight: 600,
                                }}
                              >
                                GREEN = GOOD
                              </span>
                              <span title="95% confidence; two-sample comparison (baseline vs variant, N=3000 each)">
                                * = not statistically significant
                              </span>
                              <span title="Colors normalized within each fragment cost type (common through divine).">Colors per fragment type</span>
                            </div>
                            <table className="mono" style={{ borderCollapse: "collapse", width: "100%" }}>
                              <thead>
                                <tr>
                                  <th style={{ textAlign: "left", paddingRight: 12 }}>#</th>
                                  <th style={{ textAlign: "left", paddingRight: 12 }}>Upgrade</th>
                                  <th className="num">Floors/run</th>
                                  <th className="num">Floors/run (+%)</th>
                                  <th className="num">cost</th>
                                  <th className="num" title="Floors/run (+%) per cost">(+%)/cost</th>
                                </tr>
                              </thead>
                              <tbody>
                                {FRAG_ORDER.map((ct) => {
                                  const group = rs.filter((r) => r.costType === ct).sort((a, b) => b.growthPct - a.growthPct);
                                  if (group.length === 0) return null;
                                  const color = BLOCK_COLORS[ct as keyof typeof BLOCK_COLORS] ?? "#666";
                                  const icon = getFragIconPath(ct);
                                  return (
                                    <Fragment key={ct}>
                                      <tr style={{ backgroundColor: "rgba(15,23,42,0.06)" }}>
                                        <td colSpan={6} style={{ padding: "6px 8px", fontWeight: 700, color }}>
                                          <span style={{ display: "inline-flex", alignItems: "center", gap: 8 }}>
                                            <Sprite path={icon} alt={ct} className="iconSmall" />
                                            {ct.toUpperCase()}
                                          </span>
                                        </td>
                                      </tr>
                                      {group.map((r) => {
                                        rowNum += 1;
                                        const scale = minMaxPerType[ct];
                                        return (
                                          <tr key={r.key}>
                                            <td style={{ paddingRight: 12 }}>{rowNum}</td>
                                            <td style={{ paddingRight: 12 }}>{r.displayName}</td>
                                            <td className="num">
                                              <span
                                                style={{ ...heatStyleRedGreen(heatPct(r.meanFloors, scale.minFloors, scale.maxFloors)), padding: "2px 6px", borderRadius: 4, cursor: !r.significant ? "help" : undefined }}
                                                title={!r.significant ? "Not statistically significant (95% CI includes 0)" : undefined}
                                              >
                                                {!r.significant ? "*" : r.meanFloors.toFixed(3)}
                                              </span>
                                            </td>
                                            <td className="num">
                                              <span
                                                style={{ ...heatStyleRedGreen(heatPct(r.growthPct, scale.minGrowth, scale.maxGrowth)), padding: "2px 6px", borderRadius: 4, cursor: !r.significant ? "help" : undefined }}
                                                title={
                                                  !r.significant
                                                    ? "Not statistically significant (95% CI includes 0)"
                                                    : r.growthPct < 0
                                                      ? "(too much variance / rather negative)"
                                                      : undefined
                                                }
                                              >
                                                {!r.significant
                                                  ? "*"
                                                  : `${r.growthPct >= 0 ? "+" : ""}${r.growthPct.toFixed(2)}%`}
                                              </span>
                                            </td>
                                            <td className="num">{r.cost != null ? String(r.cost) : "—"}</td>
                                            <td className="num">
                                              {r.perCost != null ? (
                                                <span
                                                  style={{ ...heatStyleRedGreen(heatPct(r.perCost, scale.minPerCost, scale.maxPerCost)), padding: "2px 6px", borderRadius: 4, cursor: !r.significant ? "help" : undefined }}
                                                  title={
                                                    !r.significant
                                                      ? "Not statistically significant (95% CI includes 0)"
                                                      : r.perCost < 0
                                                        ? "(too much variance / rather negative)"
                                                        : undefined
                                                  }
                                                >
                                                  {!r.significant || r.perCost < 0 ? "*" : r.perCost.toFixed(4)}
                                                </span>
                                              ) : (
                                                "—"
                                              )}
                                            </td>
                                          </tr>
                                        );
                                      })}
                                    </Fragment>
                                  );
                                })}
                              </tbody>
                            </table>
                          </div>
                        );
                      })() : null}
                    </>
                  )}
                </div>
              </Collapsible>

              <Collapsible
                id="arch-gem-card-skill-next"
                title="Which Gem/Card/Skill Tree Upgrade next to maximize Stage Push?"
                defaultExpanded={false}
                className="archWhichNextGold"
                headerRight={
                  <Tooltip
                    content={{
                      title: "Gem / Card / Skill MC",
                      sections: [
                        {
                          heading: "What",
                          lines: [
                            "Evaluates Gem upgrades (+1 level), Card upgrades (Card → Gilded), and Skill Tree skills (Avada Keda, Block Bonker) in one run.",
                            "Only non-maxed gems, cards at Card level, and skills you do not have are tested.",
                          ],
                        },
                        {
                          heading: "Significance",
                          lines: ["Uses same Stage MC (N=3000) and 95% confidence test. * = not statistically significant. Colors per cost class (gems vs skills)."],
                        },
                      ],
                    }}
                  />
                }
              >
                <div className="small" style={{ marginBottom: 8 }}>
                  {stageLogEntries.length === 0 ? (
                    <div className="pillLocked" style={{ padding: 8 }}>
                      Run a Stage Push MC first. No Stage result in the log.
                    </div>
                  ) : (
                    <>
                      <div style={{ display: "flex", flexWrap: "wrap", gap: 8, alignItems: "center", marginBottom: 8 }}>
                        <label className="small">
                          Reference:
                          <select
                            className="mono"
                            style={{ marginLeft: 6 }}
                            value={gemCardSkillNextRefId ?? stageLogEntries[0]?.id ?? ""}
                            onChange={(e) => setGemCardSkillNextRefId(e.target.value || null)}
                            disabled={gemCardSkillNextRunning || mcRunning}
                          >
                            {stageLogEntries.map((e) => (
                              <option key={e.id} value={e.id}>
                                {e.label} — {e.metrics.floorsPerRun.toFixed(2)} floors/run ({new Date(e.createdAt).toLocaleString()})
                              </option>
                            ))}
                          </select>
                        </label>
                        <button
                          className="btn"
                          type="button"
                          onClick={() => runGemCardSkillNext()}
                          disabled={gemCardSkillNextRunning || mcRunning || stageLogEntries.length === 0}
                        >
                          {gemCardSkillNextRunning ? "Running…" : "Run (N=3000)"}
                        </button>
                        {gemCardSkillNextRunning ? (
                          <button className="btn btnSecondary" type="button" onClick={() => { gemCardSkillNextCancelRef.current = true; }} disabled={!gemCardSkillNextRunning}>
                            Cancel
                          </button>
                        ) : null}
                      </div>
                      {gemCardSkillNextProgress ? (
                        <div className="small mono" style={{ marginBottom: 8 }}>
                          {gemCardSkillNextProgress}
                        </div>
                      ) : null}
                      {gemCardSkillNextResults && gemCardSkillNextResults.length > 0 ? (() => {
                        const rs = gemCardSkillNextResults;
                        const heatPct = (v: number, lo: number, hi: number) =>
                          hi > lo ? Math.max(0, Math.min(100, ((v - lo) / (hi - lo)) * 100)) : 50;
                        const byClass = (cls: "gem" | "skill") => rs.filter((r) => r.costClass === cls);
                        const scaleGem = (() => {
                          const g = byClass("gem");
                          const floors = g.map((r) => r.meanFloors);
                          const growth = g.map((r) => r.growthPct);
                          const perC = g.map((r) => r.perCost).filter((v) => Number.isFinite(v) && v >= 0);
                          return {
                            minFloors: floors.length ? Math.min(...floors) : 0,
                            maxFloors: floors.length ? Math.max(...floors) : 0,
                            minGrowth: growth.length ? Math.min(...growth) : 0,
                            maxGrowth: growth.length ? Math.max(...growth) : 0,
                            minPerCost: perC.length ? Math.min(...perC) : 0,
                            maxPerCost: perC.length ? Math.max(...perC) : 0,
                          };
                        })();
                        const scaleSkill = (() => {
                          const s = byClass("skill");
                          const floors = s.map((r) => r.meanFloors);
                          const growth = s.map((r) => r.growthPct);
                          return {
                            minFloors: floors.length ? Math.min(...floors) : 0,
                            maxFloors: floors.length ? Math.max(...floors) : 0,
                            minGrowth: growth.length ? Math.min(...growth) : 0,
                            maxGrowth: growth.length ? Math.max(...growth) : 0,
                            minPerCost: 0,
                            maxPerCost: 0,
                          };
                        })();
                        let rowNum = 0;
                        return (
                          <div className="small">
                            <div style={{ fontWeight: 700, marginBottom: 4 }}>Best next upgrade (by Floors/run +%; colors per cost class):</div>
                            <div className="small" style={{ marginBottom: 8, display: "flex", alignItems: "center", gap: 16, flexWrap: "wrap" }}>
                              <span style={{ color: "hsl(120, 75%, 35%)", textShadow: "0 0 8px hsla(120, 75%, 45%, 0.9)", fontWeight: 600 }}>GREEN = GOOD</span>
                              <span title="95% confidence">* = not statistically significant</span>
                              <span>Colors: gems/cards vs skills</span>
                            </div>
                            <table className="mono" style={{ borderCollapse: "collapse", width: "100%" }}>
                              <thead>
                                <tr>
                                  <th style={{ textAlign: "left", paddingRight: 12 }}>#</th>
                                  <th style={{ textAlign: "left", paddingRight: 12 }}>Type</th>
                                  <th style={{ textAlign: "left", paddingRight: 12 }}>Option</th>
                                  <th style={{ textAlign: "left", paddingRight: 12 }}>Floors/run</th>
                                  <th style={{ textAlign: "left", paddingRight: 12 }}>Floors/run (+%)</th>
                                  <th style={{ textAlign: "left", paddingRight: 12 }}>Cost</th>
                                  <th style={{ textAlign: "left", paddingRight: 12 }} title="Floors/run (+%) per gem">(+%)/cost</th>
                                </tr>
                              </thead>
                              <tbody>
                                {rs.map((r) => {
                                  rowNum += 1;
                                  const scale = r.costClass === "gem" ? scaleGem : scaleSkill;
                                  return (
                                    <tr key={`${r.source}-${r.key}`}>
                                      <td style={{ paddingRight: 12 }}>{rowNum}</td>
                                      <td style={{ paddingRight: 12 }}>{r.source === "gem" ? "Gem" : r.source === "card" ? "Card" : "Skill"}</td>
                                      <td style={{ paddingRight: 12 }}>{r.displayName}</td>
                                      <td className="num">
                                        <span style={{ ...heatStyleRedGreen(heatPct(r.meanFloors, scale.minFloors, scale.maxFloors)), padding: "2px 6px", borderRadius: 4, cursor: !r.significant ? "help" : undefined }} title={!r.significant ? "Not statistically significant" : undefined}>
                                          {!r.significant ? "*" : r.meanFloors.toFixed(3)}
                                        </span>
                                      </td>
                                      <td className="num">
                                        <span style={{ ...heatStyleRedGreen(heatPct(r.growthPct, scale.minGrowth, scale.maxGrowth)), padding: "2px 6px", borderRadius: 4, cursor: !r.significant ? "help" : undefined }}>
                                          {!r.significant ? "*" : `${r.growthPct >= 0 ? "+" : ""}${r.growthPct.toFixed(2)}%`}
                                        </span>
                                      </td>
                                      <td className="num">{r.cost != null ? r.cost : "—"}</td>
                                      <td className="num">
                                        {r.cost != null && r.cost > 0 ? (
                                          <span style={{ ...heatStyleRedGreen(heatPct(r.perCost, scale.minPerCost, scale.maxPerCost)), padding: "2px 6px", borderRadius: 4 }}>{!r.significant || r.perCost < 0 ? "*" : r.perCost.toFixed(6)}</span>
                                        ) : (
                                          "—"
                                        )}
                                      </td>
                                    </tr>
                                  );
                                })}
                              </tbody>
                            </table>
                          </div>
                        );
                      })() : null}
                    </>
                  )}
                </div>
              </Collapsible>

              <Collapsible
                id="arch-gem-frag-next"
                title="Which Gem/Card/Skill Tree/Fragment Upgrade to maximize Fragment gains?"
                defaultExpanded={false}
                className="archWhichNextPurple"
                headerRight={
                  <Tooltip
                    content={{
                      title: "Gem / Card / Skill Tree MC (Fragment)",
                      sections: [
                        {
                          heading: "What",
                          lines: [
                            "Evaluates which upgrade gives the most target fragment/run gain: Gem (+1 level), Card (Card→Gilded), or Skill Tree (Avada Keda / Block Bonker).",
                            "Uses a Fragment MC result as template. Only options you do not yet have are compared: non-maxed gems, cards at Card level (→ Gilded), and skills not yet enabled.",
                          ],
                        },
                        {
                          heading: "Significance",
                          lines: [
                            "Uses same MC (N=3000) and 95% confidence test as Stage Push.",
                            "* = not statistically significant.",
                          ],
                        },
                      ],
                    }}
                  />
                }
              >
                <div className="small" style={{ marginBottom: 8 }}>
                  {fragmentLogEntries.length === 0 ? (
                    <div className="pillLocked" style={{ padding: 8 }}>
                      Run a Fragment MC first. No Fragment result in the log. Pick one as template.
                    </div>
                  ) : (
                    <>
                      <div style={{ display: "flex", flexWrap: "wrap", gap: 8, alignItems: "center", marginBottom: 8 }}>
                        <label className="small">
                          Fragment template:
                          <select
                            className="mono"
                            style={{ marginLeft: 6 }}
                            value={gemFragNextRefId ?? fragmentLogEntries[0]?.id ?? ""}
                            onChange={(e) => setGemFragNextRefId(e.target.value || null)}
                            disabled={gemFragNextRunning || mcRunning}
                          >
                            {fragmentLogEntries.map((e) => (
                              <option key={e.id} value={e.id}>
                                {e.label} — {(e.mc?.targetFrag ?? "?").toUpperCase()} {e.metrics.fragmentsPerHour.toFixed(1)}/h ({new Date(e.createdAt).toLocaleString()})
                              </option>
                            ))}
                          </select>
                        </label>
                        <button
                          className="btn"
                          type="button"
                          onClick={() => runGemFragNext()}
                          disabled={gemFragNextRunning || mcRunning || fragmentLogEntries.length === 0}
                        >
                          {gemFragNextRunning ? "Running…" : "Run (N=3000)"}
                        </button>
                        {gemFragNextRunning ? (
                          <button className="btn btnSecondary" type="button" onClick={() => { gemFragNextCancelRef.current = true; }} disabled={!gemFragNextRunning}>
                            Cancel
                          </button>
                        ) : null}
                      </div>
                      {gemFragNextProgress ? (
                        <div className="small mono" style={{ marginBottom: 8 }}>
                          {gemFragNextProgress}
                        </div>
                      ) : null}
                      {gemFragNextResults && gemFragNextResults.length > 0 ? (() => {
                        const rs = gemFragNextResults;
                        const scale = 1000;
                        const heatPct = (v: number, lo: number, hi: number) =>
                          hi > lo ? Math.max(0, Math.min(100, ((v - lo) / (hi - lo)) * 100)) : 50;
                        const classes: GemFragCostClass[] = ["gem", "skill", "common", "rare", "epic", "legendary", "mythic", "divine"];
                        const byClass = (cls: GemFragCostClass) => rs.filter((r) => r.costClass === cls);
                        const minMax = (cls: GemFragCostClass, getVal: (r: (typeof rs)[number]) => number) => {
                          const vals = byClass(cls).map(getVal).filter((v) => Number.isFinite(v));
                          return { min: vals.length > 0 ? Math.min(...vals) : 0, max: vals.length > 0 ? Math.max(...vals) : 0 };
                        };
                        const growthByClass = Object.fromEntries(classes.map((c) => [c, minMax(c, (r) => r.growthPct)])) as Record<GemFragCostClass, { min: number; max: number }>;
                        const allGrowthByClass = Object.fromEntries(classes.map((c) => [c, minMax(c, (r) => r.allFragmentsGrowthPct)])) as Record<GemFragCostClass, { min: number; max: number }>;
                        const perCostByClass = Object.fromEntries(
                          classes.map((c) => {
                            const vals = byClass(c).map((r) => r.perCost * scale).filter((v) => Number.isFinite(v) && v >= 0);
                            return [c, { min: vals.length > 0 ? Math.min(...vals) : 0, max: vals.length > 0 ? Math.max(...vals) : 0 }];
                          }),
                        ) as Record<GemFragCostClass, { min: number; max: number }>;
                        const perCostAllByClass = Object.fromEntries(
                          classes.map((c) => {
                            const vals = byClass(c).map((r) => r.perCostAllFragments * scale).filter((v) => Number.isFinite(v) && v >= 0);
                            return [c, { min: vals.length > 0 ? Math.min(...vals) : 0, max: vals.length > 0 ? Math.max(...vals) : 0 }];
                          }),
                        ) as Record<GemFragCostClass, { min: number; max: number }>;
                        const targetFragLabel = (fragmentLogEntries.find((e) => e.id === (gemFragNextRefId ?? fragmentLogEntries[0]?.id))?.mc?.targetFrag ?? "target").toUpperCase();
                        const costEfficTitle =
                          "Cost efficiency: (+%) per unit cost × 1000. Colors are normalized within each cost class (gems vs common/rare/epic/legendary/mythic/divine fragments).";
                        let rowNum = 0;
                        return (
                          <div className="small">
                            <div style={{ fontWeight: 700, marginBottom: 4 }}>Best next upgrade (by {targetFragLabel}/run +% and all fragments/run +%):</div>
                            <div className="small" style={{ marginBottom: 8, display: "flex", alignItems: "center", gap: 16, flexWrap: "wrap" }}>
                              <span style={{ color: "hsl(120, 75%, 35%)", textShadow: "0 0 8px hsla(120, 75%, 45%, 0.9)", fontWeight: 600 }}>GREEN = GOOD</span>
                              <span title="95% confidence">* = not statistically significant</span>
                              <span title={costEfficTitle}>Colors per cost class (gems vs common/rare/epic/legendary/mythic/divine)</span>
                            </div>
                            <table className="mono" style={{ borderCollapse: "collapse", width: "100%" }}>
                              <thead>
                                <tr>
                                  <th style={{ textAlign: "left", paddingRight: 12 }}>#</th>
                                  <th style={{ textAlign: "left", paddingRight: 12 }}>Type</th>
                                  <th style={{ textAlign: "left", paddingRight: 12 }}>Option</th>
                                  <th style={{ textAlign: "left", paddingRight: 12 }}>{targetFragLabel}/run (+%)</th>
                                  <th style={{ textAlign: "left", paddingRight: 12 }} title={costEfficTitle}>Cost effic.</th>
                                  <th style={{ textAlign: "left", paddingRight: 12 }}>all fragments/run (+%)</th>
                                  <th style={{ textAlign: "left", paddingRight: 12 }} title={costEfficTitle}>Cost effic.</th>
                                  <th style={{ textAlign: "left", paddingRight: 12 }} title="Gem cost for Gem/Card; fragment cost for Fragment upgrades">Cost</th>
                                </tr>
                              </thead>
                              <tbody>
                                {rs.map((r) => {
                                  rowNum += 1;
                                  return (
                                    <tr key={`${r.source}-${r.key}`}>
                                      <td style={{ paddingRight: 12 }}>{rowNum}</td>
                                      <td style={{ paddingRight: 12 }}>{r.source === "gem" ? "Gem" : r.source === "card" ? "Card" : r.source === "skill" ? "Skill" : "Fragment"}</td>
                                      <td style={{ paddingRight: 12 }}>{r.displayName}</td>
                                      <td className="num">
                                        <span style={{ ...heatStyleRedGreen(heatPct(r.growthPct, growthByClass[r.costClass].min, growthByClass[r.costClass].max)), padding: "2px 6px", borderRadius: 4, cursor: !r.significant ? "help" : undefined }} title={!r.significant ? "Not statistically significant" : undefined}>
                                          {!r.significant ? "*" : `${r.growthPct >= 0 ? "+" : ""}${r.growthPct.toFixed(2)}%`}
                                        </span>
                                      </td>
                                      <td className="num">
                                        {r.cost != null && r.cost > 0 ? (
                                          <span style={{ ...heatStyleRedGreen(heatPct(r.perCost * scale, perCostByClass[r.costClass].min, perCostByClass[r.costClass].max)), padding: "2px 6px", borderRadius: 4 }} title={costEfficTitle}>{!r.significant || r.perCost < 0 ? "*" : (r.perCost * scale).toFixed(3)}</span>
                                        ) : (
                                          "—"
                                        )}
                                      </td>
                                      <td className="num">
                                        <span style={{ ...heatStyleRedGreen(heatPct(r.allFragmentsGrowthPct, allGrowthByClass[r.costClass].min, allGrowthByClass[r.costClass].max)), padding: "2px 6px", borderRadius: 4, cursor: !r.significant ? "help" : undefined }}>
                                          {!r.significant ? "*" : `${r.allFragmentsGrowthPct >= 0 ? "+" : ""}${r.allFragmentsGrowthPct.toFixed(2)}%`}
                                        </span>
                                      </td>
                                      <td className="num">
                                        {r.cost != null && r.cost > 0 ? (
                                          <span style={{ ...heatStyleRedGreen(heatPct(r.perCostAllFragments * scale, perCostAllByClass[r.costClass].min, perCostAllByClass[r.costClass].max)), padding: "2px 6px", borderRadius: 4 }} title={costEfficTitle}>{!r.significant ? "*" : (r.perCostAllFragments * scale).toFixed(3)}</span>
                                        ) : (
                                          "—"
                                        )}
                                      </td>
                                      <td className="num">{r.cost != null ? r.cost : "—"}</td>
                                    </tr>
                                  );
                                })}
                              </tbody>
                            </table>
                          </div>
                        );
                      })() : null}
                    </>
                  )}
                </div>
              </Collapsible>
            </div>
          </Collapsible>

          <Collapsible
            id="arch-fragment-upgrades"
            title="Fragment upgrades"
            defaultExpanded={false}
          >
            <div className="panel fragmentUpgradesPanel" style={{ background: "var(--tier2)" }}>
              {ARCH_FRAGMENT_TYPES.map((ct) => {
              const entries = fragmentGroups[ct] ?? [];
              const color = BLOCK_COLORS[ct];
              const icon = getFragIconPath(ct);
              if (!entries.length) return null;
              const groupCollapsed = collapsedFragmentGroups.has(ct);
              return (
                <div key={ct} className="fragmentGroup" style={{ borderColor: `rgba(15,23,42,0.12)` }}>
                  <div
                    className="fragmentGroupHeader fragmentGroupHeaderCollapsible"
                    role="button"
                    tabIndex={0}
                    aria-expanded={!groupCollapsed}
                    aria-label={groupCollapsed ? `Expand ${ct} upgrades` : `Collapse ${ct} upgrades`}
                    onClick={() => toggleCollapsedFragmentGroup(ct)}
                    onKeyDown={(e: React.KeyboardEvent) => {
                      if (e.key === "Enter" || e.key === " ") {
                        e.preventDefault();
                        toggleCollapsedFragmentGroup(ct);
                      }
                    }}
                  >
                    <span className="fragmentGroupChevron" aria-hidden>
                      {groupCollapsed ? "▶" : "▼"}
                    </span>
                    <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                      <Sprite path={icon} alt={`${ct} icon`} className="iconSmall" />
                      <div className="mono" style={{ fontWeight: 900, color }}>
                        {ct.toUpperCase()}
                      </div>
                    </div>
                  </div>

                  {!groupCollapsed ? (
                    <div style={{ display: "grid", gap: 8 }}>
                      {entries.map(([key, info]) => {
                        const lvl = clampInt(Number(build.fragmentUpgradeLevels[key] ?? 0), 0, clampInt(Number(info.max_level ?? 0), 0, 999));
                        const maxLvl = clampInt(Number(info.max_level ?? 0), 0, 999);
                        const stageUnlock = clampInt(Number(info.stage_unlock ?? 0), 0, 999);
                        const ascTier = Number((info as { ascension_tier?: number }).ascension_tier ?? 0);
                        const ascLocked = ascTier > (build.ascensionLevel ?? 0);
                        const locked = ascLocked || build.unlockedStage < stageUnlock;
                        const nextCost = getUpgradeCost(key, lvl, build.ascensionLevel ?? 0);
                        const isMaxed = !locked && lvl >= maxLvl;
                        return (
                          <div
                            key={key}
                            className={`fragmentUpgradeRow ${locked ? "fragmentUpgradeRowLocked" : ""} ${isMaxed ? "fragmentUpgradeRowMaxed" : ""}`}
                            style={{
                              ...(locked ? undefined : heatStyle(lvl, maxLvl)),
                              ...(isMaxed ? { color: "#888" } : undefined),
                            }}
                          >
                            <div className="fragmentUpgradeTop">
                              <div style={{ display: "flex", alignItems: "center", gap: 6, minWidth: 0 }}>
                                <div className="mono" style={{ fontWeight: 900 }}>
                                  {info.display_name}
                                </div>
                              </div>
                              <div className="fragmentUpgradeRight upgradeLevel" style={isMaxed ? { color: "#888" } : undefined}>
                                {locked ? (
                                  <span className="small">
                                    <span className="pillLocked">LOCKED</span>{" "}
                                    <span className="lockedText">
                                      {ascLocked ? `requires ${ascensionLabel(ascTier as AscensionLevel)}` : `until stage ${stageUnlock}`}
                                    </span>
                                  </span>
                                ) : (
                                  <>
                                    <span className="small">lvl</span>{" "}
                                    <span className="heatNum mono" style={isMaxed ? { color: "#888" } : heatStyle(lvl, maxLvl)}>
                                      {lvl}
                                    </span>{" "}
                                    <span className="small">/</span> <span className="mono">{maxLvl}</span>
                                  </>
                                )}
                              </div>
                            </div>
                            {!locked ? (
                              <>
                                <div className="small">
                                  next cost: <span className="mono">{nextCost == null ? "—" : String(nextCost)}</span>
                                </div>
                                <div style={{ marginTop: 8, display: "flex", flexWrap: "wrap", alignItems: "center", gap: 8 }}>
                                  {lvl >= maxLvl ? (
                                    <span
                                      className="fragmentUpgradeMaxed"
                                      style={{
                                        background: "hsl(120, 45%, 35%)",
                                        color: "#fff",
                                        padding: "6px 12px",
                                        borderRadius: 6,
                                        fontWeight: 600,
                                      }}
                                    >
                                      Maxed
                                    </span>
                                  ) : null}
                                  <div className="btnRow fragmentUpgradeButtons">
                                    <button className="btn btnSecondary" type="button" onClick={() => setFragmentUpgrade(key, -5)} disabled={lvl <= 0 || mcRunning}>
                                      −5
                                    </button>
                                    <button className="btn btnSecondary" type="button" onClick={() => setFragmentUpgrade(key, -1)} disabled={lvl <= 0 || mcRunning}>
                                      −
                                    </button>
                                    {lvl < maxLvl ? (
                                      <>
                                        <button className="btn" type="button" onClick={() => setFragmentUpgrade(key, +1)} disabled={mcRunning}>
                                          +
                                        </button>
                                        <button className="btn btnSecondary" type="button" onClick={() => setFragmentUpgrade(key, +5)} disabled={mcRunning}>
                                          +5
                                        </button>
                                      </>
                                    ) : null}
                                  </div>
                                </div>
                              </>
                            ) : null}
                          </div>
                        );
                      })}
                    </div>
                  ) : null}
                </div>
              );
            })}
            </div>
          </Collapsible>

          <Collapsible id="arch-gem-upgrades" title="Gem upgrades" defaultExpanded={false} headerRight={<Sprite path="sprites/common/gem.png" alt="Gem" className="iconSmall" />}>
            <div className="panel gemPanel" style={{ background: "var(--tier1)", padding: "6px 8px" }}>
              <div className="small" style={{ marginBottom: 4 }}>
                Permanent. Maxed levels are highlighted.
              </div>

              <div style={{ display: "grid", gap: 4 }}>
                {(
                  [
                    {
                      key: "stamina" as const,
                      label: "Max Stamina / Stam mod chance",
                      icon: "sprites/archaeology/gem_upgrade_stamina.png",
                      perLevel: "+2 / +0.05%",
                    },
                    {
                      key: "xp" as const,
                      label: "Archaeology Exp Gain / Exp mod chance",
                      icon: "sprites/archaeology/gem_upgrade_xp.png",
                      perLevel: "+5% / +0.05%",
                    },
                    {
                      key: "fragment" as const,
                      label: "Fragment Gain / Loot mod chance",
                      icon: "sprites/archaeology/gem_upgrade_fragment.png",
                      perLevel: "+2% / +0.05%",
                    },
                  ] as const
                ).map((u) => {
                  const k = u.key;
                  const lvl = build.gemUpgrades[k] ?? 0;
                  const max = getGemUpgradeMaxLevel(k, build.ascensionLevel ?? 0);
                  const nextCost = getGemUpgradeCost(k, lvl, build.ascensionLevel ?? 0);
                  const locked = build.unlockedStage < (GEM_UPGRADE_BONUSES[k].stage_unlock ?? 0);
                  const maxed = lvl >= max;
                  return (
                    <div key={k} className={`gemUpgradeRow ${maxed ? "gemUpgradeMaxed" : ""} ${locked ? "gemUpgradeLocked" : ""}`} style={maxed || locked ? undefined : heatStyle(lvl, max)}>
                      <div className="label" style={{ alignItems: "center" }}>
                        <span style={{ display: "inline-flex", alignItems: "center", gap: 8 }}>
                          <Sprite path={u.icon} alt={`${k} gem upgrade`} className="iconSmall" />
                          <span className="mono" style={{ fontWeight: 900, color: "rgba(15,23,42,0.86)" }}>
                            {u.label}
                          </span>
                        </span>
                        {locked ? (
                          <span className="small upgradeLevel">
                            <span className="pillLocked">LOCKED</span> <span className="lockedText">until stage {GEM_UPGRADE_BONUSES[k].stage_unlock}</span>
                          </span>
                        ) : (
                          <span className="mono upgradeLevel">
                            <span className="small">lvl</span>{" "}
<span className="heatNum mono" style={heatStyle(lvl, max)}>
                            {lvl}
                          </span>{" "}
                            <span className="small">/</span> <span className="mono">{max}</span>
                          </span>
                        )}
                      </div>
                      {!locked ? (
                        <>
                          <div className="small" style={{ marginTop: 2 }}>
                            per level: <span className="mono">{u.perLevel}</span>
                          </div>
                          <div className="small">
                            next cost: <span className="mono">{nextCost == null ? "—" : String(nextCost)}</span>
                          </div>
                          <div className="btnRow" style={{ marginTop: 8 }}>
                            <button className="btn btnSecondary" type="button" onClick={() => setGemUpgrade(k, -1)} disabled={lvl <= 0 || mcRunning}>
                              −
                            </button>
                            <button className="btn" type="button" onClick={() => setGemUpgrade(k, +1)} disabled={lvl >= max || mcRunning}>
                              +
                            </button>
                          </div>
                        </>
                      ) : null}
                    </div>
                  );
                })}
              </div>
            </div>
          </Collapsible>

          <Collapsible id="arch-cards" title="Cards" defaultExpanded={false} headerRight={<Sprite path="sprites/archaeology/cards.png" alt="Cards" className="iconSmall" />}>
            <div className="small" style={{ marginBottom: 8 }}>
              Per block type + tier. Card effects: HP −10/−20/−35% and XP +10/+20/+35% (polychrome can be boosted by the Stage 34 fragment upgrade).
            </div>

            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 4 }}>
              {BLOCK_TYPES.map((bt) => {
                const color = BLOCK_COLORS[bt];
                return (
                  <div key={bt} style={{ border: "1px solid rgba(15,23,42,0.10)", borderRadius: 10, padding: 6, background: "var(--tier2)" }}>
                    <div style={{ display: "flex", gap: 6, alignItems: "center", marginBottom: 4 }}>
                      <span className="mono" style={{ color, fontWeight: 900 }}>
                        {bt.toUpperCase()}
                      </span>
                    </div>

                    {BLOCK_CARD_TIERS.map((tier) => {
                      const t = tier as BlockTier;
                      if (!getBlockData(t, bt)) return null;
                      const cardKey = `${bt},${t}`;
                      const cur = (build.blockCards[cardKey] ?? 0) as CardLevel;
                      const icon = archBlockIconPath(bt, t);
                      return (
                        <div
                          key={tier}
                          style={{
                            display: "grid",
                            gridTemplateColumns: "1fr",
                            gap: 4,
                            alignItems: "center",
                            justifyItems: "center",
                            marginBottom: 4,
                            padding: "4px 6px",
                            border: "1px solid rgba(15,23,42,0.08)",
                            borderRadius: 10,
                            background: "rgba(255,255,255,0.72)",
                          }}
                        >
                          <div style={{ display: "flex", gap: 6, alignItems: "center", justifyContent: "center" }}>
                            <Sprite path={icon} alt={`${bt} icon`} className="iconSmall" />
                            <div className="mono">
                              {bt} T{tier}
                            </div>
                          </div>
                          <div style={{ display: "flex", gap: 4, justifyContent: "center", flexWrap: "wrap" }}>
                            <button
                              className={`btn btnSecondary ${cur === 1 ? "cardBtnActive" : ""}`}
                              type="button"
                              onClick={() => setBlockCard(bt, t, 1)}
                              style={{ padding: "3px 6px" }}
                            >
                              Card {cur === 1 ? "✓" : ""}
                            </button>
                            <button
                              className={`btn btnSecondary ${cur === 2 ? "cardBtnActive" : ""}`}
                              type="button"
                              onClick={() => setBlockCard(bt, t, 2)}
                              style={{ padding: "3px 6px" }}
                            >
                              Gild {cur === 2 ? "✓" : ""}
                            </button>
                            <button
                              className={`btn btnSecondary ${cur === 3 ? "cardBtnActive" : ""}`}
                              type="button"
                              onClick={() => setBlockCard(bt, t, 3)}
                              style={{ padding: "3px 6px" }}
                            >
                              Poly {cur === 3 ? "✓" : ""}
                            </button>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                );
              })}

              <div style={{ gridColumn: "1 / -1", border: "1px solid rgba(15,23,42,0.10)", borderRadius: 10, padding: 6, background: "var(--tier2)" }}>
                <div className="label" style={{ justifyContent: "center", gap: 8 }}>
                  <span className="mono">Misc card (ability cooldown)</span>
                  <span className="mono">{build.miscCardLevel === 0 ? "OFF" : build.miscCardLevel === 1 ? "Card" : build.miscCardLevel === 2 ? "Gild" : "Poly"}</span>
                </div>
                <div className="small">Card: −3% cooldown • Gild: −6% • Poly: −10%</div>
                <div className="btnRow" style={{ marginTop: 4, justifyContent: "center" }}>
                  <button className={`btn btnSecondary ${build.miscCardLevel === 1 ? "cardBtnActive" : ""}`} type="button" onClick={() => setMiscCard(1)}>
                    Card {build.miscCardLevel === 1 ? "✓" : ""}
                  </button>
                  <button className={`btn btnSecondary ${build.miscCardLevel === 2 ? "cardBtnActive" : ""}`} type="button" onClick={() => setMiscCard(2)}>
                    Gild {build.miscCardLevel === 2 ? "✓" : ""}
                  </button>
                  <button className={`btn btnSecondary ${build.miscCardLevel === 3 ? "cardBtnActive" : ""}`} type="button" onClick={() => setMiscCard(3)}>
                    Poly {build.miscCardLevel === 3 ? "✓" : ""}
                  </button>
                </div>
              </div>
            </div>
          </Collapsible>

        </div>
      </div>

      {mcWindowOpen ? (
        <div className="modalOverlay" onMouseDown={() => setMcWindowOpen(false)}>
          <div className="modalWindow modalWindowWide" onMouseDown={(e) => e.stopPropagation()}>
            <div className="modalHeader">
              <div>
                <div className="mono" style={{ fontWeight: 900 }}>
                  Monte Carlo • Multi-core
                </div>
                <div className="small">
                  Saved runs: <span className="mono">{visibleMcLog.length}</span>
                  {mcProgress ? (
                    <>
                      {" "}
                      • Status: <span className="mono">{mcProgress}</span>
                    </>
                  ) : null}
                </div>
              </div>
              <div style={{ display: "flex", gap: 10, alignItems: "center" }}>
                <button className="btn btnSecondary" type="button" onClick={() => setMcWindowOpen(false)}>
                  Close
                </button>
              </div>
            </div>
            <div className="modalBody modalBodyWide">
              <div className="mcModalGrid">
                <div className="panel mcPanel">
                  <div className="panelHeader">
                    <h2 className="panelTitle">Monte Carlo</h2>
                    <p className="panelHint">
                      Multi-core • unbiased from <span className="mono">Stage 1</span>
                    </p>
                  </div>

                  {(() => {
                    const defaultScreening = 100;
                    const defaultRefinement = 200;
                    const screeningN = mcSettings.devTuning ? clampInt(Number(mcSettings.screeningSims ?? defaultScreening), 0, 999999) : defaultScreening;
                    const refinementN = mcSettings.devTuning ? clampInt(Number(mcSettings.refinementSims ?? defaultRefinement), 0, 999999) : defaultRefinement;
                    return (
                      <>
                        <div className="mcDevBox">
                          <div className="mcDevHeader">
                            <div className="mono" style={{ fontWeight: 900 }}>
                              Screening/Refinement
                            </div>
                          </div>

                          <label className="toggle" style={{ marginTop: 8 }}>
                            <input
                              type="checkbox"
                              checked={mcSettings.devTuning}
                              onChange={(e) =>
                                setMcSettings((s) => ({
                                  ...s,
                                  devTuning: e.target.checked,
                                  screeningSims: clampInt(Number(s.screeningSims ?? defaultScreening), 0, 999999),
                                  refinementSims: clampInt(Number(s.refinementSims ?? defaultRefinement), 0, 999999),
                                }))
                              }
                            />
                            <span style={{ display: "inline-flex", alignItems: "center", gap: 8 }}>
                              Developer only: override N
                              <Tooltip
                                content={{
                                  title: "Defaults",
                                  sections: [
                                    {
                                      heading: "Defaults",
                                      lines: ["Screening N default: 100", "Refinement N default: 200", "Combinations default: ×1"],
                                    },
                                    {
                                      heading: "Recommendation",
                                      lines: ["If your CPU is fast enough, try 500 / 350 / ×4 for better results."],
                                    },
                                  ],
                                }}
                              />
                            </span>
                          </label>

                          <div style={{ display: "grid", gridTemplateColumns: "repeat(3, minmax(0, 1fr))", gap: 8, marginTop: 8 }}>
                            <div>
                              <div className="label">
                                <span>Screening N</span>
                                <span className="mono">{mcSettings.screeningSims}</span>
                              </div>
                              <input
                                className="input"
                                type="number"
                                min={0}
                                step={10}
                                disabled={!mcSettings.devTuning || mcRunning}
                                value={mcSettings.screeningSims}
                                onChange={(e) => setMcSettings((s) => ({ ...s, screeningSims: clampInt(Number(e.target.value), 0, 999999) }))}
                              />
                            </div>
                            <div>
                              <div className="label">
                                <span>Refinement N</span>
                                <span className="mono">{mcSettings.refinementSims}</span>
                              </div>
                              <input
                                className="input"
                                type="number"
                                min={0}
                                step={10}
                                disabled={!mcSettings.devTuning || mcRunning}
                                value={mcSettings.refinementSims}
                                onChange={(e) => setMcSettings((s) => ({ ...s, refinementSims: clampInt(Number(e.target.value), 0, 999999) }))}
                              />
                            </div>
                            <div>
                              <div className="label">
                                <span style={{ display: "inline-flex", alignItems: "center", gap: 8 }}>
                                  Combinations
                                  <Tooltip
                                    content={{
                                      title: "Combinations",
                                      lines: [
                                        "This increases how many different stat distributions are sampled in Phase 1.",
                                        "Higher = more coverage, slower runs.",
                                      ],
                                    }}
                                  />
                                </span>
                                <span className="mono">×{mcSettings.combosMult}</span>
                              </div>
                              <input
                                className="input"
                                type="number"
                                min={1}
                                step={1}
                                disabled={!mcSettings.devTuning || mcRunning}
                                value={mcSettings.combosMult}
                                onChange={(e) => setMcSettings((s) => ({ ...s, combosMult: clampInt(Number(e.target.value), 1, 50) }))}
                              />
                            </div>
                          </div>
                        </div>
                      </>
                    );
                  })()}

                  {false && (
                    <div className="mcDevBox" style={{ marginTop: 8 }}>
                      <div className="mcDevHeader">
                        <span className="mono" style={{ fontWeight: 900 }}>Tie-break</span>
                      </div>
                      <label className="toggle" style={{ marginTop: 8 }}>
                        <input
                          type="checkbox"
                          checked={mcSettings.tieBreakWithSignificance}
                          onChange={(e) => setMcSettings((s) => ({ ...s, tieBreakWithSignificance: e.target.checked }))}
                        />
                        <span style={{ display: "inline-flex", alignItems: "center", gap: 8 }}>
                          Tie-break w/ significance
                          <Tooltip
                            content={{
                              title: "Tie-break w/ significance",
                              sections: [
                                { heading: "When off", lines: ["Ties use a fixed percentage threshold."] },
                                { heading: "When on", lines: ["Significance tests at every step (Welch, α=0.05)."] },
                              ],
                            }}
                          />
                        </span>
                      </label>
                    </div>
                  )}

                  <div className="mcCards">
                    <div className="mcCard mcCardStage">
                      {mcRunning && mcActiveMode === "stage" && mcProgressFrac ? (
                        <div className="mcProgressBig mcProgressInCard" title={mcProgress ?? undefined}>
                          {mcPhaseLabel ? <div className="mcProgressPhase">{mcPhaseLabel}</div> : null}
                          <div className="mcProgressCount">{mcProgressFrac.text}</div>
                        </div>
                      ) : null}
                      <div className="mcCardTitle" style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 8 }}>
                        <span>Stage Push Optimizer</span>
                        <Tooltip
                          content={{
                            title: "Stage Push Optimizer",
                            lines: [
                              "Runs many Monte Carlo simulations in parallel to find the best stat distribution.",
                              "Goal: maximize your average max stage (how far a run tends to push).",
                              "Uses screening + refinement phases, then saves a detailed run you can reopen.",
                            ],
                          }}
                        />
                      </div>
                      <div className="small">Objective: maximize average max stage.</div>
                      <div className="btnRow" style={{ marginTop: 10 }}>
                        <button
                          className="btn"
                          type="button"
                          disabled={mcRunning}
                          onClick={() => (mcSettings.comparisonEnabled && mcSettings.comparisonMethods.length >= 1 ? runComparison("stage") : runMcOptimizer("stage"))}
                        >
                          Run MC <span className="mono">({mcEstimateLabel})</span>
                        </button>{" "}
                        <Tooltip
                          content={{
                            title: "Estimated run time",
                            lines: [
                              "Rough estimate from a short calibration on your device; depends on Screening N, Refinement N, and Combinations above.",
                              "Actual duration may vary.",
                            ],
                          }}
                        />
                        {mcRunning ? (
                          <button className="btn btnSecondary" type="button" onClick={cancelMc}>
                            Cancel
                          </button>
                        ) : null}
                      </div>
                    </div>

                    <div className="mcCard mcCardXp">
                      {mcRunning && mcActiveMode === "XP" && mcProgressFrac ? (
                        <div className="mcProgressBig mcProgressInCard" title={mcProgress ?? undefined}>
                          {mcPhaseLabel ? <div className="mcProgressPhase">{mcPhaseLabel}</div> : null}
                          <div className="mcProgressCount">{mcProgressFrac.text}</div>
                        </div>
                      ) : null}
                      <div className="mcCardTitle" style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 8 }}>
                        <span>XP Optimizer</span>
                        <Tooltip
                          content={{
                            title: "XP Optimizer",
                            lines: [
                              "Searches stat distributions using parallel Monte Carlo simulations.",
                              "Goal: maximize XP per hour (speed + kills + XP multipliers).",
                              "Best for farming XP efficiently at your current setup.",
                            ],
                          }}
                        />
                      </div>
                      <div className="small">Objective: maximize XP/hour.</div>
                      <div className="row" style={{ marginTop: 8, flexWrap: "wrap", alignItems: "center", gap: "8px 14px" }}>
                        <span className="label" style={{ marginBottom: 0 }}>
                          Tie-break after XP/h
                          <Tooltip
                            content={{
                              title: "Tie-break after XP/h",
                              lines: [
                                "When two builds have similar XP/h, the optimizer picks the better one using a second metric, then a third.",
                                "Fragments/h first: compare total fragments/h, then avg max stage.",
                                "Avg max stage first: compare avg max stage, then fragments/h.",
                              ],
                            }}
                            label="?"
                          />
                        </span>
                        <label style={{ display: "inline-flex", alignItems: "center", gap: 6, marginBottom: 0, cursor: mcRunning ? "default" : "pointer" }}>
                          <input
                            type="radio"
                            name="arch-xp-tie"
                            checked={mcSettings.xpTieBreakSecondary === "frag_per_hour"}
                            disabled={mcRunning}
                            onChange={() => setMcSettings((s) => ({ ...s, xpTieBreakSecondary: "frag_per_hour" }))}
                          />
                          <span>Fragments/h first</span>
                        </label>
                        <label style={{ display: "inline-flex", alignItems: "center", gap: 6, marginBottom: 0, cursor: mcRunning ? "default" : "pointer" }}>
                          <input
                            type="radio"
                            name="arch-xp-tie"
                            checked={mcSettings.xpTieBreakSecondary === "avg_max_stage"}
                            disabled={mcRunning}
                            onChange={() => setMcSettings((s) => ({ ...s, xpTieBreakSecondary: "avg_max_stage" }))}
                          />
                          <span>Avg max stage first</span>
                        </label>
                      </div>
                      <div className="btnRow" style={{ marginTop: 10 }}>
                        <button
                          className="btn"
                          type="button"
                          disabled={mcRunning}
                          onClick={() => (mcSettings.comparisonEnabled && mcSettings.comparisonMethods.length >= 1 ? runComparison("XP") : runMcOptimizer("XP"))}
                        >
                          Run MC <span className="mono">({mcEstimateLabel})</span>
                        </button>{" "}
                        <Tooltip
                          content={{
                            title: "Estimated run time",
                            lines: [
                              "Rough estimate from a short calibration on your device; depends on Screening N, Refinement N, and Combinations above.",
                              "Actual duration may vary.",
                            ],
                          }}
                        />
                        {mcRunning ? (
                          <button className="btn btnSecondary" type="button" onClick={cancelMc}>
                            Cancel
                          </button>
                        ) : null}
                      </div>
                    </div>

                    <div className="mcCard mcCardFrag">
                      {mcRunning && mcActiveMode === "frag" && mcProgressFrac ? (
                        <div className="mcProgressBig mcProgressInCard" title={mcProgress ?? undefined}>
                          {mcPhaseLabel ? <div className="mcProgressPhase">{mcPhaseLabel}</div> : null}
                          <div className="mcProgressCount">{mcProgressFrac.text}</div>
                        </div>
                      ) : null}
                      <div className="mcCardTitle" style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 8 }}>
                        <span>Fragment Farmer</span>
                        <Tooltip
                          content={{
                            title: "Fragment Farmer",
                            lines: [
                              "Searches stat distributions using parallel Monte Carlo simulations.",
                              "Goal: maximize fragments per hour for the selected target fragment type.",
                              "Use the fragment toggles to choose what you want to farm.",
                            ],
                          }}
                        />
                      </div>
                      <div className="small">Objective: maximize target fragments/hour.</div>
                      <div className="row" style={{ marginTop: 8 }}>
                        <div className="label">
                          <span>Target fragment</span>
                          <span className="mono">{mcSettings.targetFrag.toUpperCase()}</span>
                        </div>
                        <div className="fragToggleRow">
                          {ARCH_FRAGMENT_TYPES.map((t) => {
                            const icon = getFragIconPath(t);
                            const active = mcSettings.targetFrag === t;
                            const tierColor = BLOCK_COLORS[t];
                            return (
                              <button
                                key={t}
                                type="button"
                                className={`btn btnSecondary fragToggle ${active ? "fragToggleActive" : ""}`}
                                style={
                                  active && tierColor
                                    ? {
                                        borderColor: `${tierColor}99`,
                                        boxShadow: `0 0 0 3px ${tierColor}29, 0 0 22px ${tierColor}29`,
                                        background: `${tierColor}14`,
                                      }
                                    : undefined
                                }
                                disabled={mcRunning}
                                onClick={() => setMcSettings((s) => ({ ...s, targetFrag: t }))}
                                title={`Target: ${t.toUpperCase()}`}
                              >
                                <Sprite path={icon} alt={`${t} fragment`} className="iconSmall" />
                                <span className="mono">{t.toUpperCase()}</span>
                              </button>
                            );
                          })}
                        </div>
                      </div>
                      <div className="btnRow" style={{ marginTop: 10 }}>
                        <button
                          className="btn"
                          type="button"
                          disabled={mcRunning}
                          onClick={() => (mcSettings.comparisonEnabled && mcSettings.comparisonMethods.length >= 1 ? runComparison("frag") : runMcOptimizer("frag"))}
                        >
                          Run MC <span className="mono">({mcEstimateLabel})</span>
                        </button>{" "}
                        <Tooltip
                          content={{
                            title: "Estimated run time",
                            lines: [
                              "Rough estimate from a short calibration on your device; depends on Screening N, Refinement N, and Combinations above.",
                              "Actual duration may vary.",
                            ],
                          }}
                        />
                        {mcRunning ? (
                          <button className="btn btnSecondary" type="button" onClick={cancelMc}>
                            Cancel
                          </button>
                        ) : null}
                      </div>
                    </div>
                  </div>

                  <div className="mcCompareSection" style={{ marginTop: 16, display: "none" }}>
                    <label className="toggle" style={{ display: "inline-flex", alignItems: "center", gap: 8 }}>
                      <input
                        type="checkbox"
                        checked={mcSettings.comparisonEnabled}
                        disabled={mcRunning}
                        onChange={(e) => setMcSettings((s) => ({ ...s, comparisonEnabled: e.target.checked }))}
                      />
                      <span>Compare methods (run selected methods in sequence, same params)</span>
                      <Tooltip
                        content={{
                          title: "Compare methods",
                          lines: [
                            "Run multiple search methods with the same screening/refinement params.",
                            "Each method runs in sequence; results are compared by primary metric.",
                            "Multi-start runs the 2-phase search 3 times with different RNG seeds and keeps the best.",
                          ],
                        }}
                      />
                    </label>
                    {mcSettings.comparisonEnabled ? (
                      <div style={{ marginTop: 8, display: "flex", flexDirection: "column", gap: 6 }}>
                        {(["default", "multiStart3"] as const).map((id) => (
                          <label key={id} className="toggle" style={{ fontWeight: "normal" }}>
                            <input
                              type="checkbox"
                              checked={mcSettings.comparisonMethods.includes(id)}
                              disabled={mcRunning}
                              onChange={(e) => {
                                if (e.target.checked)
                                  setMcSettings((s) => ({ ...s, comparisonMethods: [...s.comparisonMethods, id] }));
                                else
                                  setMcSettings((s) => ({ ...s, comparisonMethods: s.comparisonMethods.filter((m) => m !== id) }));
                              }}
                            />
                            <span>{id === "default" ? "Default 2-phase" : "Multi-start (3 seeds)"}</span>
                          </label>
                        ))}
                        <p className="small" style={{ margin: 0 }}>
                          Multi-start runs the same 2-phase search 3 times with different seeds and keeps the best result.
                        </p>
                      </div>
                    ) : null}
                  </div>

                  {comparisonResult ? (
                    <div className="panel" style={{ marginTop: 16, background: "var(--tier2)" }}>
                      <div className="panelHeader">
                        <h2 className="panelTitle">Comparison result</h2>
                        <p className="panelHint">
                          Primary: {comparisonResult.mode === "stage" ? "avg max stage" : comparisonResult.mode === "XP" ? "XP/h" : "target frag/h"}
                        </p>
                      </div>
                      <table className="mcCompareTable" style={{ width: "100%", borderCollapse: "collapse", marginTop: 8 }}>
                        <thead>
                          <tr>
                            <th style={{ textAlign: "left", padding: "4px 8px" }}>Method</th>
                            <th style={{ textAlign: "right", padding: "4px 8px" }}>Primary</th>
                            <th style={{ padding: "4px 8px" }} />
                          </tr>
                        </thead>
                        <tbody>
                          {comparisonResult.methodResults.map((row) => (
                            <tr key={row.methodId}>
                              <td style={{ padding: "4px 8px" }}>
                                {row.label}
                                {row.methodId === comparisonResult.winnerId ? (
                                  <span className="badge" style={{ marginLeft: 6 }}>best</span>
                                ) : null}
                              </td>
                              <td style={{ textAlign: "right", padding: "4px 8px" }} className="mono">
                                {row.primary.toFixed(2)}
                              </td>
                              <td style={{ padding: "4px 8px" }}>
                                <button
                                  type="button"
                                  className="btn btnSecondary"
                                  onClick={() => applyBuildToCurrent(row.build)}
                                >
                                  Apply
                                </button>
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  ) : null}
                </div>
                <div className="mcLogPanel">
                  <div className="mcLogHeader">
                    <div className="mcLogTitle">MC Results Log</div>
                    <div style={{ display: "flex", gap: 8 }}>
                      <button
                        className={resetMcLogArmed ? "btn btnDanger" : "btn btnSecondary"}
                        type="button"
                        style={{ padding: "6px 10px", background: "#ffffff" }}
                        onClick={() => {
                          if (!resetMcLogArmed) {
                            setResetMcLogArmed(true);
                            setResetAllArmed(false);
                            return;
                          }
                          setResetMcLogArmed(false);
                          if (!confirmDanger("Reset MC results log? This will delete all saved MC runs in this browser.")) return;
                          setMcLog([]);
                          setActiveLogId(null);
                        }}
                        disabled={mcRunning}
                        title={resetMcLogArmed ? "Click again to confirm (then confirm dialog)." : "Click once to arm, click again to confirm."}
                      >
                        {resetMcLogArmed ? "Confirm reset" : "Reset"}
                      </button>
                    </div>
                  </div>
                  <div className="mcLogList">
                    {visibleMcLog.length === 0 ? (
                      <div className="small" style={{ textAlign: "center", padding: 14 }}>
                        No saved MC runs yet. Run one of the optimizers to create entries you can reopen later.
                      </div>
                    ) : (
                      <div className="mcLogTableWrap">
                        <table className="mcLogTable">
                          <thead>
                            <tr>
                              <th className="mono">Time</th>
                              <th>Run</th>
                              <th className="mono num">Floors/run</th>
                              <th className="mono num">XP/h</th>
                              <th className="mono num">Frag/h</th>
                              <th className="mono" style={{ textAlign: "right" }}>
                                Actions
                              </th>
                            </tr>
                          </thead>
                          <tbody>
                            {visibleMcLog.map((e, idx) => {
                              const active = e.id === activeLogId;
                              const rowClass = `${active ? "active " : ""}${idx % 2 === 1 ? "zebra" : ""}`.trim();
                              return (
                                <>
                                  <tr key={`${e.id}:row`} className={rowClass}>
                                    <td className="mono time">{new Date(e.createdAt).toLocaleString()}</td>
                                    <td className="run">
                                      {e.mc?.screeningSims === 0 ? (
                                        <>
                                          <span className="mcTypePill mcTypePill_stage">STAGE</span>{" "}
                                          <span className="mcTypePill mcTypePill_frag">FRAG</span>{" "}
                                          <span className="mcTypePill mcTypePill_XP">XP</span>{" "}
                                        </>
                                      ) : (
                                        <span className={`mcTypePill mcTypePill_${e.mcType}`}>{e.mcType.toUpperCase()}</span>
                                      )}{" "}
                                      <span className="label">{e.label}</span>
                                    </td>
                                    <td className="mono num">{formatWithThinSpaces(e.metrics.floorsPerRun, 2)}</td>
                                    <td className="mono num">{formatWithThinSpaces(Math.round(e.metrics.xpPerHour), 0)}</td>
                                    <td className="mono num">{formatWithThinSpaces(e.metrics.fragmentsPerHour, 1)}</td>
                                    <td className="actions" />
                                  </tr>
                                  <tr key={`${e.id}:actions`} className={`${rowClass} mcActionsRow`.trim()}>
                                    <td className="actionsCell" colSpan={6}>
                                      <div className="mcLogButtons">
                                        <button
                                          className="btn btnSecondary"
                                          type="button"
                                          onClick={() => {
                                            setActiveLogId(e.id);
                                            setOpenLogId(e.id);
                                          }}
                                        >
                                          Open
                                        </button>
                                        <button
                                          className="btn"
                                          type="button"
                                          onClick={() => {
                                            setBuild(e.build);
                                            setActiveLogId(e.id);
                                          }}
                                        >
                                          Load
                                        </button>
                                        <button
                                          className={deleteLogArmedId === e.id ? "btn btnDanger" : "btn btnSecondary"}
                                          type="button"
                                          onClick={() => {
                                            if (deleteLogArmedId !== e.id) {
                                              setDeleteLogArmedId(e.id);
                                              setResetAllArmed(false);
                                              setResetMcLogArmed(false);
                                              return;
                                            }
                                            setDeleteLogArmedId(null);
                                            if (!confirmDanger("Delete this saved MC run?")) return;
                                            setMcLog((xs) => xs.filter((x) => x.id !== e.id));
                                            if (active) setActiveLogId(null);
                                            if (openLogId === e.id) setOpenLogId(null);
                                          }}
                                          title={deleteLogArmedId === e.id ? "Click again to confirm (then confirm dialog)." : "Click once to arm, click again to confirm."}
                                        >
                                          {deleteLogArmedId === e.id ? "Confirm delete" : "Delete"}
                                        </button>
                                      </div>
                                    </td>
                                  </tr>
                                </>
                              );
                            })}
                          </tbody>
                        </table>
                      </div>
                    )}
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      ) : null}

      {openLog ? (
        <div className="modalOverlay" onMouseDown={() => setOpenLogId(null)}>
          <div className="modalWindow" onMouseDown={(e) => e.stopPropagation()}>
            <div className="modalHeader">
              <div>
                <div className="mono" style={{ fontWeight: 900 }}>
                  {openLog.label}
                  {openLog.mc?.screeningSims === 0
                    ? " • STAGE • FRAG • XP"
                    : ` • ${openLog.mcType.toUpperCase()}`}
                </div>
                <div className="small">{new Date(openLog.createdAt).toLocaleString()}</div>
              </div>
              <div style={{ display: "flex", gap: 8 }}>
                <button className="btn" type="button" onClick={() => setBuild(openLog.build)}>
                  Load build
                </button>
                <button className="btn btnSecondary" type="button" onClick={() => setOpenLogId(null)}>
                  Close
                </button>
              </div>
            </div>
            <div className="modalBody">
              {openLog.mc ? (
                <p className="small" style={{ marginBottom: 8, opacity: 0.9 }}>
                  {openLog.mc.refinementSims != null && openLog.mc.screeningSims === 0
                    ? `Mean and SD below are from the final sims (N=${openLog.mc.refinementSims}).`
                    : "Mean and SD below are from the final sims (N≈3000) of the winning build (top1), not from all candidates."}
                </p>
              ) : null}
              <div className="kv">
                <kbd>Unlocked</kbd>
                <div className="mono">{formatWithThinSpaces(Number(openLog.build.unlockedStage), 1)}</div>
                <kbd>Arch level</kbd>
                <div className="mono">{formatWithThinSpaces(Number(openLog.build.archLevel), 1)}</div>
                <kbd>Floors/run</kbd>
                <div className="mono">
                  {openLog.metrics.floorsPerRunStd != null
                    ? `${formatWithThinSpaces(openLog.metrics.floorsPerRun, 1)} ± ${formatWithThinSpaces(openLog.metrics.floorsPerRunStd, 1)}`
                    : formatWithThinSpaces(openLog.metrics.floorsPerRun, 1)}
                </div>
                <kbd>XP/run</kbd>
                <div className="mono">
                  {openLog.metrics.xpPerRunStd != null
                    ? `${formatWithThinSpaces(openLog.metrics.xpPerRun, 1)} ± ${formatWithThinSpaces(openLog.metrics.xpPerRunStd, 1)}`
                    : formatWithThinSpaces(openLog.metrics.xpPerRun, 1)}
                </div>
                <kbd>XP/h</kbd>
                <div className="mono">
                  {openLog.metrics.xpPerHourStd != null
                    ? `${formatWithThinSpaces(openLog.metrics.xpPerHour, 1)} ± ${formatWithThinSpaces(openLog.metrics.xpPerHourStd, 1)}`
                    : formatWithThinSpaces(openLog.metrics.xpPerHour, 1)}
                </div>
                <kbd>Fragments/run</kbd>
                <div className="mono">{formatWithThinSpaces(openLog.metrics.fragmentsPerRunTotal, 1)}</div>
                <kbd>Frag/h</kbd>
                <div className="mono">
                  {openLog.metrics.fragmentsPerHourStd != null
                    ? `${formatWithThinSpaces(openLog.metrics.fragmentsPerHour, 1)} ± ${formatWithThinSpaces(openLog.metrics.fragmentsPerHourStd, 1)}`
                    : formatWithThinSpaces(openLog.metrics.fragmentsPerHour, 1)}
                </div>
                <kbd>Attacks/run</kbd>
                <div className="mono">
                  {openLog.metrics.attacksPerRun != null
                    ? openLog.metrics.attacksPerRunStd != null
                      ? `${formatWithThinSpaces(Number(openLog.metrics.attacksPerRun), 1)} ± ${formatWithThinSpaces(Number(openLog.metrics.attacksPerRunStd), 1)}`
                      : formatWithThinSpaces(Number(openLog.metrics.attacksPerRun), 1)
                    : "—"}
                </div>
                <kbd>Run duration</kbd>
                <div className="mono">
                  {formatDurationMinSec(openLog.metrics.durationSeconds)}
                  {openLog.metrics.durationSecondsStd != null ? ` ± ${formatDurationMinSec(openLog.metrics.durationSecondsStd)}` : ""}
                </div>
                {(() => {
                  const byType = openLog.metrics.fragmentsPerHourByType;
                  if (!byType) return null;
                  return (
                    <>
                      <kbd>Fragment distribution (Frag/h)</kbd>
                      <div className="small mono" style={{ display: "flex", flexWrap: "wrap", gap: "6px 12px", alignItems: "center" }}>
                        {ARCH_FRAGMENT_TYPES.map((t) => (
                          <span key={t} style={{ display: "inline-flex", alignItems: "center", gap: 4 }}>
                            <Sprite path={getFragIconPath(t)} alt={t} className="iconSmall" />
                            = {formatWithThinSpaces(byType[t] ?? 0, 1)}
                          </span>
                        ))}
                      </div>
                    </>
                  );
                })()}
              </div>

              {openLog.metrics.blockBreakdown?.by_type && Object.keys(openLog.metrics.blockBreakdown.by_type).length > 0 ? (
                <div style={{ marginTop: 12 }}>
                  <Collapsible
                    id="arch-result-block-breakdown"
                    title="Block time distribution"
                    defaultExpanded={false}
                  >
                  <p className="small" style={{ marginBottom: 8 }}>Time spent per block type over the run (estimated).</p>
                  <div className="archBlockBreakdownTableWrap">
                    <table className="archBlockBreakdownTable">
                      <thead>
                        <tr>
                          <th></th>
                          <th>Block</th>
                          <th className="num">Destroyed/run</th>
                          <th className="num">Time/run (s)</th>
                          <th className="num">Share</th>
                          <th className="num">Avg hits/block</th>
                        </tr>
                      </thead>
                      <tbody>
                        {(() => {
                          const blockTypeOrder = BLOCK_TYPES;
                          const entries = Object.entries(openLog.metrics.blockBreakdown!.by_type)
                            .filter(([, v]) => v && (v.blocks_destroyed_per_run >= 0.01 || v.time_seconds_per_run >= 0.5))
                            .map(([key, v]) => {
                              const [blockType, tierStr] = key.includes(",") ? key.split(",") : [key, "1"];
                              const tier = tierStr || "1";
                              const sortIdx = blockTypeOrder.indexOf(blockType as (typeof blockTypeOrder)[number]);
                              return { key, blockType, tier, v, sortIdx: sortIdx < 0 ? 99 : sortIdx, tierNum: Number(tier) || 1 };
                            })
                            .sort((a, b) => a.sortIdx !== b.sortIdx ? a.sortIdx - b.sortIdx : a.tierNum - b.tierNum);
                          return entries.map(({ key, blockType, tier, v }) => (
                            <tr key={key}>
                              <td>
                                <Sprite path={archBlockIconPath(blockType as BlockType, Number(tier) as BlockTier)} alt={`${blockType} T${tier}`} className="iconSmall" />
                              </td>
                              <td>{blockType.charAt(0).toUpperCase() + blockType.slice(1)} T{tier}</td>
                              <td className="num mono">{formatWithThinSpaces(v.blocks_destroyed_per_run, 1)}</td>
                              <td className="num mono">{formatWithThinSpaces(v.time_seconds_per_run, 0)}</td>
                              <td className="num mono">{formatWithThinSpaces(v.time_share * 100, 1)}%</td>
                              <td className="num mono">{formatWithThinSpaces(v.avg_hits_per_block, 1)}</td>
                            </tr>
                          ));
                        })()}
                      </tbody>
                    </table>
                  </div>
                  {(openLog.metrics.blockBreakdown.most_time_type || openLog.metrics.blockBreakdown.most_avg_hits_type) && (
                    <p className="small" style={{ marginTop: 6, color: "var(--muted)" }}>
                      {[
                        openLog.metrics.blockBreakdown.most_time_type &&
                          `Most time: ${formatBlockBreakdownLabel(openLog.metrics.blockBreakdown.most_time_type)}`,
                        openLog.metrics.blockBreakdown.most_avg_hits_type &&
                          `Highest avg hits/block: ${formatBlockBreakdownLabel(openLog.metrics.blockBreakdown.most_avg_hits_type)}`,
                      ]
                        .filter(Boolean)
                        .join(" • ")}
                    </p>
                  )}
                  </Collapsible>
                </div>
              ) : null}

              {openLog.mc ? (
                <div style={{ marginTop: 12, display: "grid", gap: 10 }}>
                  {(() => {
                    const b = openLog.build;
                    const skills = getVisibleSkills(b.ascensionLevel ?? 0);
                    const skillTitle = (
                      <span
                        style={{
                          display: "inline-flex",
                          alignItems: "center",
                          gap: 6,
                          flexWrap: "wrap",
                          fontSize: 16,
                          fontWeight: 900,
                          marginBottom: 6,
                        }}
                      >
                        {skills.map((s) => {
                          const meta = getSkillDisplay(s);
                          const v = b.skillPoints[s] ?? 0;
                          const skillCap = getSkillPointCap(b, s);
                          return (
                            <span key={s} style={{ display: "inline-flex", alignItems: "center", gap: 4 }}>
                              <Sprite path={meta.icon} alt={meta.label} className="iconSmall" />
                              {meta.short}{" "}
                              <span className="mono" style={heatGlowStyle(v, skillCap)}>
                                {v}
                              </span>
                            </span>
                          );
                        })}
                        <span style={{ opacity: 0.5, fontWeight: 600 }}>—</span>
                      </span>
                    );
                    const distTitle =
                      openLog.mc.objective === "stage"
                        ? "Reached Stage Distribution in Final Simulation (over N=3000)"
                        : openLog.mc.objective === "XP"
                          ? "XP per Hour Distribution in Final Simulation (over N=3000)"
                          : "Fragments per Hour Distribution in Final Simulation (over N=3000)";
                    return (
                      <div>
                        {renderHistogramCard({
                          samples: openLog.mc.objectiveSamples ?? [],
                          kind: openLog.mc.objective === "stage" ? "stage" : "rate",
                          gradientIdPrefix: openLog.mc.objective === "stage" ? openLog.id : undefined,
                          onFlameClick:
                            openLog.mc.objective === "stage" && (openLog.mc.avgStaminaAtEndOfStage || openLog.mc.staminaAtStageByRun?.length)
                              ? (stage: number) => {
                                  setStaminaOverviewStage(stage);
                                  setStaminaOverviewOpen(true);
                                }
                              : undefined,
                          title: (
                            <div style={{ display: "flex", flexDirection: "column", gap: 2 }}>
                              {skillTitle}
                              <span style={{ fontSize: 11, fontWeight: 700, color: "rgba(15,23,42,0.7)" }}>
                                {distTitle}
                              </span>
                            </div>
                          ),
                          ariaLabel: `${formatSkillPointsLine(b, skills)} — ${distTitle}`,
                          xLabel:
                            openLog.mc.objective === "stage"
                              ? "Max Stage Reached"
                              : openLog.mc.objective === "XP"
                                ? "XP per Hour"
                                : "Fragments per Hour",
                        })}
                      </div>
                    );
                  })()}

                  {staminaOverviewOpen && openLog?.mc?.objective === "stage" && (openLog.mc.avgStaminaAtEndOfStage || openLog.mc.staminaAtStageByRun?.length) ? (
                    <div
                      className="modalBackdrop"
                      style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.4)", zIndex: 1000, display: "flex", alignItems: "center", justifyContent: "center" }}
                      onClick={() => { setStaminaOverviewOpen(false); setStaminaOverviewStage(null); }}
                      role="dialog"
                      aria-modal="true"
                      aria-label="Avg stamina at end of stage"
                    >
                      <div
                        className="panel"
                        style={{
                          background: "var(--tier2)",
                          padding: 10,
                          borderRadius: 10,
                          maxWidth: 320,
                          boxShadow: "0 8px 24px rgba(0,0,0,0.25)",
                        }}
                        onClick={(e) => e.stopPropagation()}
                      >
                        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 6 }}>
                          <div className="mono" style={{ fontWeight: 900, fontSize: 13 }}>
                            Avg stamina at end of stage
                          </div>
                          <button type="button" className="btn btnSecondary" onClick={() => { setStaminaOverviewOpen(false); setStaminaOverviewStage(null); }}>
                            Close
                          </button>
                        </div>
                        <div className="small" style={{ marginBottom: 6, color: "var(--muted)" }}>
                          {staminaOverviewStage != null && openLog.mc.staminaAtStageByRun?.length && openLog.mc.objectiveSamples?.length
                            ? `Runs that reached stage ${staminaOverviewStage}: average stamina remaining at end of each stage.`
                            : "Over all runs that reached each stage: average stamina remaining when that stage was completed."}
                        </div>
                        <div style={{ maxHeight: 220, overflowY: "auto", border: "1px solid rgba(15,23,42,0.12)", borderRadius: 6 }}>
                          <table className="mono" style={{ width: "100%", borderCollapse: "collapse", fontSize: 12 }}>
                            <thead style={{ position: "sticky", top: 0, background: "var(--tier2)", zIndex: 1 }}>
                              <tr style={{ borderBottom: "1px solid rgba(15,23,42,0.2)" }}>
                                <th style={{ textAlign: "left", padding: "4px 6px" }}>Stage</th>
                                <th style={{ textAlign: "right", padding: "4px 6px" }}>Avg stamina left ± SD</th>
                              </tr>
                            </thead>
                            <tbody>
                              {(() => {
                                const byRun = openLog.mc.staminaAtStageByRun;
                                const maxStages = openLog.mc.objectiveSamples ?? [];
                                const filterStage = staminaOverviewStage ?? null;
                                if (filterStage != null && byRun?.length && maxStages.length === byRun.length) {
                                  const runIndices = maxStages.map((ms, i) => (Number(ms) >= filterStage ? i : -1)).filter((i) => i >= 0);
                                  const stages = Array.from({ length: filterStage }, (_, i) => i + 1);
                                  return stages.map((s) => {
                                    const values = runIndices
                                      .filter((i) => (byRun[i]?.length ?? 0) >= s)
                                      .map((i) => Number(byRun[i]![s - 1]));
                                    const n = values.length;
                                    if (n === 0) return <tr key={s} style={{ borderBottom: "1px solid rgba(15,23,42,0.08)" }}><td style={{ padding: "4px 6px" }}>{s}</td><td style={{ textAlign: "right", padding: "4px 6px" }}>—</td></tr>;
                                    const mean = values.reduce((a, b) => a + b, 0) / n;
                                    const sd = n > 1 ? Math.sqrt(Math.max(0, values.reduce((sum, v) => sum + (v - mean) ** 2, 0) / (n - 1))) : null;
                                    const sdStr = sd != null && Number.isFinite(sd) ? (sd < 10 ? sd.toFixed(1) : formatInt(Math.round(sd))) : "";
                                    return (
                                      <tr key={s} style={{ borderBottom: "1px solid rgba(15,23,42,0.08)" }}>
                                        <td style={{ padding: "4px 6px" }}>{s}</td>
                                        <td style={{ textAlign: "right", padding: "4px 6px" }}>
                                          {sdStr ? `${formatInt(Math.round(mean))} ± ${sdStr}` : formatInt(Math.round(mean))}
                                        </td>
                                      </tr>
                                    );
                                  });
                                }
                                const avg = openLog.mc.avgStaminaAtEndOfStage ?? {};
                                const std = openLog.mc.stdStaminaAtEndOfStage ?? {};
                                const samples = openLog.mc.objectiveSamples ?? [];
                                const maxStage = samples.length ? Math.max(0, ...samples.map((x) => Number(x))) : 0;
                                const stages = Array.from({ length: Math.max(0, maxStage - 1) }, (_, i) => i + 1);
                                return stages.map((s) => {
                                  const m = avg[s] ?? 0;
                                  const sd = std[s];
                                  const sdStr = sd != null && Number.isFinite(sd) ? (sd < 10 ? sd.toFixed(1) : formatInt(Math.round(sd))) : "";
                                  return (
                                    <tr key={s} style={{ borderBottom: "1px solid rgba(15,23,42,0.08)" }}>
                                      <td style={{ padding: "4px 6px" }}>{s}</td>
                                      <td style={{ textAlign: "right", padding: "4px 6px" }}>
                                        {sdStr ? `${formatInt(Math.round(m))} ± ${sdStr}` : formatInt(Math.round(m))}
                                      </td>
                                    </tr>
                                  );
                                });
                              })()}
                            </tbody>
                          </table>
                        </div>
                        <p className="small" style={{ marginTop: 6, color: "var(--muted)" }}>
                          End of max stage = 0 (run ended there).
                        </p>
                      </div>
                    </div>
                  ) : null}

                  {openLog.mc.tieBreak ? (
                    <Collapsible
                      id="arch-result-tiebreak"
                      title="Tie-break"
                      defaultExpanded={false}
                      headerRight={<Tooltip content={TIEBREAK_TOOLTIP} />}
                    >
                      <div className="small">
                        Tied at primary: <span className="mono">{openLog.mc.tieBreak.tiedAtPrimary}</span> • Winner:{" "}
                        <span className="mono">{openLog.mc.tieBreak.winnerReason}</span>
                      </div>
                      <div style={{ marginTop: 10 }}>{renderTieBreakBars(openLog.mc.tieBreak)}</div>
                      {openLog.mc.tieBreak.top3?.length ? (
                        <ul className="list" style={{ marginTop: 8 }}>
                          {openLog.mc.tieBreak.top3.map((c) => (
                            <li key={c.label}>
                              <span className="mono">{c.label}</span> • primary <span className="mono">{c.primary.toFixed(3)}</span>
                              {c.secondary != null ? (
                                <>
                                  {" "}
                                  • secondary <span className="mono">{c.secondary.toFixed(3)}</span>
                                </>
                              ) : null}
                              {c.tertiary != null ? (
                                <>
                                  {" "}
                                  • tertiary <span className="mono">{c.tertiary.toFixed(3)}</span>
                                </>
                              ) : null}
                              <div className="mono" style={{ marginTop: 4 }}>
                                {formatSkillPointsLine(
                                  {
                                    ...openLog.build,
                                    skillPoints: skillPointsFromOptimizerDistRecord(openLog.build, c.dist),
                                  },
                                  getVisibleSkills(openLog.build.ascensionLevel ?? 0),
                                )}
                              </div>
                            </li>
                          ))}
                        </ul>
                      ) : null}
                    </Collapsible>
                  ) : null}
                </div>
              ) : null}
            </div>
          </div>
        </div>
      ) : null}
    </div>
  );
}

