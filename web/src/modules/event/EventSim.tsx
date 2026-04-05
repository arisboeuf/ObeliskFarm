import { useEffect, useMemo, useRef, useState, type CSSProperties } from "react";
import { createPortal } from "react-dom";
import { formatInt, formatTime } from "../../lib/format";
import { loadJson, saveJson } from "../../lib/storage";
import { COSTS, GEM_UPGRADE_NAMES, getPrestigeWaveRequirement, getRewardMilestoneDisplayLabel, getNextRewardMilestoneAfterPrestige, PRESTIGE_UNLOCKED, UPGRADE_SHORT_NAMES, TARGET_WAVE_OPTIONS, clampToTargetWaveOption, type TargetWaveOption } from "../../lib/event/constants";
import {
  canAllocateUpgrade,
  copyState,
  createEmptyState,
  getMaxLevelWithCaps,
  type Budget,
  type OptimizationResult,
  type UpgradeState,
} from "../../lib/event/optimizer";
import { monteCarloOptimizeGuided, estimateReachProbabilityGivenState, type MCOptimizationResult, type PrestigeReachMcResult } from "../../lib/event/monteCarloOptimizer";
import { applyUpgrades, calculateMaterials, getEnemyHpAtWave, getGemMaxLevel, runFullSimulation, runFullSimulationWithHpPerWave, type HpPerWaveRow } from "../../lib/event/simulation";
import { mulberry32 } from "../../lib/rng";
import { assetUrl } from "../../lib/assets";
import { currencyIconFilename, gemUpgradeIconFilename, upgradeIconFilename } from "../../lib/event/icons";
import { Collapsible } from "../../components/Collapsible";
import { SilverHologramCanvas } from "../../components/SilverHologramCanvas";
import { Tooltip } from "../../components/Tooltip";

type SavedStateV1 = {
  prestige: number;
  upgrade_levels: Record<string, number[]>;
  gem_levels: number[];
  world_monuments?: number;
  targetWaveOverride?: boolean;
  targetWave?: number;
  /** Legacy: was target prestige; loaded and converted to wave if targetWave missing */
  targetPrestigeOverride?: boolean;
  targetPrestige?: number;
};

export type EventMcComparisonMethodId = "default" | "multiStart3" | "wide" | "stable" | "wideMulti2";

function getMethodConfig(
  methodId: EventMcComparisonMethodId,
  baseN: number,
  baseR: number
): { numCandidates: number; runsPerCombo: number; seeds: number } {
  switch (methodId) {
    case "default":
      return { numCandidates: baseN, runsPerCombo: baseR, seeds: 1 };
    case "multiStart3":
      return { numCandidates: baseN, runsPerCombo: baseR, seeds: 3 };
    case "wide":
      return { numCandidates: Math.min(40000, baseN * 2), runsPerCombo: baseR, seeds: 1 };
    case "stable":
      return { numCandidates: baseN, runsPerCombo: Math.min(1000, baseR * 2), seeds: 1 };
    case "wideMulti2":
      return { numCandidates: Math.min(40000, baseN * 2), runsPerCombo: baseR, seeds: 2 };
    default:
      return { numCandidates: baseN, runsPerCombo: baseR, seeds: 1 };
  }
}

function getMethodLabel(methodId: EventMcComparisonMethodId): string {
  switch (methodId) {
    case "default":
      return "Default (1 run)";
    case "multiStart3":
      return "Multi-start (3 seeds)";
    case "wide":
      return "Wide (2×N)";
    case "stable":
      return "Stable (2×runs/combo)";
    case "wideMulti2":
      return "Wide + Multi-start (2 seeds)";
    default:
      return String(methodId);
  }
}

const COMPARISON_METHOD_IDS: EventMcComparisonMethodId[] = ["default", "multiStart3", "wide", "stable", "wideMulti2"];

/** Set to true to show "Developer: Compare algorithms" button and modal. */
const SHOW_COMPARISON = false;

type UiState = {
  prestige: number;
  /** World Monuments built (1–4). Rewards except Gifts/Mythic Chests/Skins are ×2 per monument. */
  worldMonuments: number;
  budget1: string;
  budget2: string;
  budget3: string;
  budget4: string;
  upgrades: UpgradeState;
  mcCandidates: number;
  mcRunsPerCombo: number;
  /** Wave band step (e.g. 5): same band → tie-break by currency/h. 0 = off. */
  waveBandStep: number;
  /** When true: band = highest reward wave reached (EVENT_REWARD_WAVES), tie-break by currency/h. */
  useRewardMilestones: boolean;
  /** When true: MC only considers setups whose attack damage does not exceed enemy HP at target wave. */
  targetWaveOverride: boolean;
  /** Target wave for override (e.g. 200). Only setups with atk <= enemy HP at this wave are considered. */
  targetWave: number;
  devOnlyMcTuning: boolean;
  // Developer comparison (only used in sub-window)
  comparisonMethods: EventMcComparisonMethodId[];
  comparisonReplicates: number;
  comparisonValidationSims: number;
};

const STORAGE_KEY = "obeliskfarm:web:event_budget_save.json:v1";

function parseNumber(raw: string): number {
  const cleaned = raw.trim().replaceAll(",", "").replaceAll(" ", "");
  if (!cleaned) return 0;
  const n = Number(cleaned);
  return Number.isFinite(n) ? n : 0;
}

function clampInt(n: number, min: number, max: number): number {
  if (!Number.isFinite(n)) return min;
  return Math.max(min, Math.min(max, Math.trunc(n)));
}

function formatPct01(x: number, digits = 1): string {
  if (!Number.isFinite(x)) return "—";
  return `${(x * 100).toFixed(digits)}%`;
}

function heatAlphaFromLevel(level: number): number {
  // Absolute-points heatmap (NOT normalized by max per-upgrade).
  // Compress a bit so high levels don't fully saturate.
  // Typical event upgrade levels go up to ~50.
  const lvl = Math.max(0, Math.trunc(level));
  if (lvl <= 0) return 0;
  const maxRef = 50;
  const alpha = (Math.log1p(lvl) / Math.log1p(maxRef)) * 0.28; // up to ~0.28
  return Math.max(0.06, Math.min(0.28, alpha));
}

function heatStyle(level: number): CSSProperties {
  const a = heatAlphaFromLevel(level);
  if (a <= 0) return {};
  // Green -> Yellow -> Orange based on absolute points.
  const maxRef = 50;
  const t = Math.max(0, Math.min(1, Math.log1p(Math.max(0, level)) / Math.log1p(maxRef)));
  const hue = t < 0.5 ? 120 + (60 - 120) * (t / 0.5) : 60 + (30 - 60) * ((t - 0.5) / 0.5);
  const bg = `hsla(${hue.toFixed(1)}, 85%, 70%, ${a.toFixed(3)})`;
  const border = `hsla(${hue.toFixed(1)}, 85%, 38%, 0.35)`;
  return { backgroundColor: bg, borderColor: border };
}

function Sprite(props: { path: string | null; alt: string; className?: string; label?: string }) {
  const { path, alt, className, label } = props;
  const [ok, setOk] = useState(true);
  if (!path || !ok) {
    return <span className="iconPlaceholder" title={`Missing sprite: ${label ?? alt}`}>?</span>;
  }
  const src = path.startsWith("http://") || path.startsWith("https://") ? path : assetUrl(path);
  return (
    <img
      className={className ?? "icon"}
      src={src}
      alt={alt}
      onError={() => setOk(false)}
      title={alt}
    />
  );
}

export function EventSim() {
  const initial = useMemo<UiState>(() => {
    const saved = loadJson<SavedStateV1>(STORAGE_KEY);
    const base = createEmptyState();
    if (saved?.upgrade_levels) {
      for (const tier of [1, 2, 3, 4] as const) {
        const key = String(tier);
        const arr = saved.upgrade_levels[key];
        if (Array.isArray(arr) && arr.length === base.levels[tier].length) {
          base.levels[tier] = arr.map((x) => (Number.isFinite(Number(x)) ? Math.max(0, Math.trunc(Number(x))) : 0));
        }
      }
    }
    if (Array.isArray(saved?.gem_levels) && saved!.gem_levels.length === 4) {
      base.gemLevels = [
        clampInt(Number(saved!.gem_levels[0]), 0, 999),
        clampInt(Number(saved!.gem_levels[1]), 0, 999),
        clampInt(Number(saved!.gem_levels[2]), 0, 999),
        clampInt(Number(saved!.gem_levels[3]), 0, 999),
      ];
    }

    return {
      prestige: clampInt(saved?.prestige ?? 0, 0, 999),
      worldMonuments: clampInt(saved?.world_monuments ?? 1, 1, 4),
      budget1: "",
      budget2: "",
      budget3: "",
      budget4: "",
      upgrades: base,
      mcCandidates: 2000,
      mcRunsPerCombo: 500,
      waveBandStep: 0,
      useRewardMilestones: true,
      targetWaveOverride: saved?.targetWaveOverride ?? saved?.targetPrestigeOverride ?? true,
      targetWave: (() => {
        const raw = saved?.targetWave ?? (saved?.targetPrestige != null ? getPrestigeWaveRequirement(saved.targetPrestige) : 250);
        const w = clampInt(raw, 0, 99999);
        return clampToTargetWaveOption(w);
      })(),
      devOnlyMcTuning: false,
      comparisonMethods: ["default", "multiStart3"],
      comparisonReplicates: 3,
      comparisonValidationSims: 0,
    };
  }, []);

  const [ui, setUi] = useState<UiState>(initial);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<OptimizationResult | null>(null);
  const [mcStats, setMcStats] = useState<MCOptimizationResult | null>(null);
  const [running, setRunning] = useState(false);
  const [progress, setProgress] = useState<{ cur: number; total: number; curWave: number; bestWave: number } | null>(null);
  const [mcMeta, setMcMeta] = useState<{ startedAt: number; totalSims: number } | null>(null);
  const [appliedSinceLastOptimize, setAppliedSinceLastOptimize] = useState(false);
  const [resetUpgradesArmed, setResetUpgradesArmed] = useState(false);
  const PRESTIGE_REACH_HOURS_MAX = 24;
  const [prestigeReachHoursSelected, setPrestigeReachHoursSelected] = useState(4);
  const [prestigeReachMcResult, setPrestigeReachMcResult] = useState<PrestigeReachMcResult[] | null>(null);
  const [prestigeReachMcRunning, setPrestigeReachMcRunning] = useState(false);
  const [prestigeReachMcProgress, setPrestigeReachMcProgress] = useState<{
    hour: number;
    currentRun: number;
    totalRuns: number;
  } | null>(null);
  const prestigeReachCancelRef = useRef(false);
  const workerJobRef = useRef<"main" | "prestigeReach" | null>(null);
  type PrestigeReachContext = {
    hour: number;
    results: PrestigeReachMcResult[];
    initial: UpgradeState;
    budget1h: Budget;
    targetWave: number;
    prestige: number;
    numCandidates: number;
    runsPerCombo: number;
    waveBandStep: number | null;
    useRewardMilestones: boolean;
  };
  const prestigeReachContextRef = useRef<PrestigeReachContext | null>(null);
  const PRESTIGE_REACH_SIGNIFICANT = 0.95;
  const [waveHistogramOpen, setWaveHistogramOpen] = useState(false);
  const [waveHistogramSamples, setWaveHistogramSamples] = useState<number[] | null>(null);
  const [waveHistogramHpPerWave, setWaveHistogramHpPerWave] = useState<HpPerWaveRow[] | null>(null);
  const [waveHistogramLoading, setWaveHistogramLoading] = useState(false);
  type ComparisonReplicateRow = {
    methodId: EventMcComparisonMethodId;
    replicateIndex: number;
    bestWave: number;
    validationWave?: number;
    result: OptimizationResult;
    statistics: Record<string, number>;
    bestWaveBand?: number;
    bestCurrencyPerHour?: number;
  };

  type ComparisonMethodSummary = {
    methodId: EventMcComparisonMethodId;
    label: string;
    replicates: ComparisonReplicateRow[];
    summary: {
      meanBest: number;
      stdBest: number;
      minBest: number;
      maxBest: number;
      medianBest: number;
      meanVal?: number;
      stdVal?: number;
    };
  };

  const [comparisonResult, setComparisonResult] = useState<null | {
    methodResults: ComparisonMethodSummary[];
    winnerId: EventMcComparisonMethodId;
  }>(null);
  const [comparisonWindowOpen, setComparisonWindowOpen] = useState(false);
  const workerRef = useRef<Worker | null>(null);
  const lastInitialRef = useRef<UpgradeState | null>(null);
  const comparisonRunRef = useRef<{
    active: boolean;
    methods: EventMcComparisonMethodId[];
    methodIndex: number;
    replicateIndex: number;
    multiStartRun: number;
    results: ComparisonReplicateRow[];
    budget: Budget;
    prestige: number;
    baseN: number;
    baseR: number;
    replicates: number;
    validationSims: number;
  } | null>(null);

  function confirmDanger(message: string): boolean {
    try {
      return window.confirm(message);
    } catch {
      return false;
    }
  }

  // autosave (matches desktop save schema: prestige + upgrade_levels + gem_levels + world_monuments; NOT budgets)
  useEffect(() => {
    const t = window.setTimeout(() => {
      const payload: SavedStateV1 = {
        prestige: ui.prestige,
        world_monuments: ui.worldMonuments,
        upgrade_levels: {
          "1": ui.upgrades.levels[1].slice(),
          "2": ui.upgrades.levels[2].slice(),
          "3": ui.upgrades.levels[3].slice(),
          "4": ui.upgrades.levels[4].slice(),
        },
        gem_levels: ui.upgrades.gemLevels.slice(),
        targetWaveOverride: ui.targetWaveOverride,
        targetWave: ui.targetWave,
      };
      saveJson(STORAGE_KEY, payload);
    }, 250);
    return () => window.clearTimeout(t);
  }, [ui.prestige, ui.worldMonuments, ui.upgrades, ui.targetWaveOverride, ui.targetWave]);

  useEffect(() => {
    if (!resetUpgradesArmed) return;
    const t = window.setTimeout(() => setResetUpgradesArmed(false), 4500);
    return () => window.clearTimeout(t);
  }, [resetUpgradesArmed]);

  useEffect(() => {
    if (!comparisonWindowOpen) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") setComparisonWindowOpen(false);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [comparisonWindowOpen]);

  const totalPoints = useMemo(() => {
    return ([1, 2, 3, 4] as const).reduce((acc, tier) => acc + ui.upgrades.levels[tier].reduce((a, b) => a + b, 0), 0);
  }, [ui.upgrades]);

  const currentSimStats = useMemo(() => {
    const prestige = clampInt(ui.prestige, 0, 999);
    const gemLevels = (ui.upgrades.gemLevels ?? [0, 0, 0, 0]) as unknown as [number, number, number, number];
    return applyUpgrades(ui.upgrades.levels as unknown as Record<number, number[]>, prestige, gemLevels);
  }, [ui.prestige, ui.upgrades]);
  const currentPlayerStats = currentSimStats.player;
  const currentEnemyStats = currentSimStats.enemy;

  const maxOneHitWaveTooltipLine = useMemo(() => {
    const atk = currentPlayerStats.atk;
    const { baseHealth, healthScaling } = currentEnemyStats;
    if (atk < baseHealth) return "No wave is one-hit with this damage.";
    if (healthScaling <= 0) return "All waves are one-hit with this damage.";
    const w = Math.floor((atk - baseHealth) / healthScaling);
    return `Highest wave one-hit with this damage: ${formatInt(w)}.`;
  }, [currentPlayerStats.atk, currentEnemyStats.baseHealth, currentEnemyStats.healthScaling]);

  function ensureWorker() {
    if (workerRef.current) return;
    workerRef.current = new Worker(new URL("../../workers/mc.worker.ts", import.meta.url), { type: "module" });
    workerRef.current.onmessage = (ev: MessageEvent<any>) => {
      const msg = ev.data;
      if (msg?.type === "progress" && workerJobRef.current === "prestigeReach") {
        const ctx = prestigeReachContextRef.current;
        if (ctx) {
          const p = msg.payload as { cur: number; total: number };
          setPrestigeReachMcProgress({ hour: ctx.hour, currentRun: p.cur, totalRuns: p.total });
        }
        return;
      }
      if (msg?.type === "progress") {
        setProgress(msg.payload);
        return;
      }
      if (msg?.type === "done" && workerJobRef.current === "prestigeReach") {
        const ctx = prestigeReachContextRef.current;
        if (!ctx) return;
        const r: MCOptimizationResult = msg.payload;
        const budgetH: Budget = {
          1: ctx.budget1h[1] * ctx.hour,
          2: ctx.budget1h[2] * ctx.hour,
          3: ctx.budget1h[3] * ctx.hour,
          4: ctx.budget1h[4] * ctx.hour,
        };
        // Defer heavy work so UI can process Cancel clicks and stay responsive
        setTimeout(() => {
          if (prestigeReachCancelRef.current) {
            setPrestigeReachMcResult(ctx.results.length > 0 ? ctx.results : null);
            setPrestigeReachMcRunning(false);
            setPrestigeReachMcProgress(null);
            prestigeReachContextRef.current = null;
            workerJobRef.current = null;
            return;
          }
          const reach = estimateReachProbabilityGivenState({
            state: r.bestState,
            prestige: ctx.prestige,
            targetWave: ctx.targetWave,
            budget: budgetH,
            numRuns: 500,
            runsPerCombo: 5,
          });
          ctx.results.push(reach);
          setPrestigeReachMcResult([...ctx.results]);
          setPrestigeReachMcRunning(false);
          setPrestigeReachMcProgress(null);
          prestigeReachContextRef.current = null;
          workerJobRef.current = null;
        }, 0);
        return;
      }
      if (msg?.type === "cancelled" && workerJobRef.current === "prestigeReach") {
        const ctx = prestigeReachContextRef.current;
        setPrestigeReachMcResult(ctx?.results && ctx.results.length > 0 ? ctx.results : null);
        setPrestigeReachMcRunning(false);
        setPrestigeReachMcProgress(null);
        prestigeReachContextRef.current = null;
        workerJobRef.current = null;
        return;
      }
      if (msg?.type === "done") {
        const r: MCOptimizationResult = msg.payload;
        const bandMode = r.bestWaveBand != null;
        const byReward = r.tieBreakByRewardMilestones === true;
        const recs = [
          "Monte Carlo Optimization (guided MC)",
          `N=${ui.mcCandidates} candidates, ${ui.mcRunsPerCombo} runs/combo`,
          `Best Wave: ${r.bestWave.toFixed(1)}`,
          ...(bandMode
            ? [
                byReward
                  ? `Reward milestone: ${r.bestWaveBand} (tie-break by currency/h)`
                  : `Wave band: ${r.bestWaveBand} (step ${r.waveBandStep ?? 0}; tie-break by currency/h)`,
                `Currency/h: ${Number(r.bestCurrencyPerHour).toLocaleString(undefined, { maximumFractionDigits: 0 })}`,
              ]
            : []),
          `Average Wave: ${(r.statistics.mean_wave ?? 0).toFixed(1)} ± ${(r.statistics.std_dev_wave ?? 0).toFixed(1)}`,
          `Wave Range: ${(r.statistics.min_wave ?? 0).toFixed(1)} - ${(r.statistics.max_wave ?? 0).toFixed(1)}`,
          `Median Wave: ${(r.statistics.median_wave ?? 0).toFixed(1)}`,
        ];
        const optResult: OptimizationResult = {
          upgrades: r.bestState,
          expectedWave: r.bestWave,
          expectedTime: r.bestTime,
          materialsSpent: r.materialsSpent,
          materialsRemaining: r.materialsRemaining,
          playerStats: r.playerStats,
          enemyStats: r.enemyStats,
          recommendations: recs,
          breakpoints: [],
        };
        const comp = comparisonRunRef.current;
        if (comp?.active) {
          const cfg = getMethodConfig(comp.methods[comp.methodIndex]!, comp.baseN, comp.baseR);
          if (comp.multiStartRun + 1 < cfg.seeds) {
            comp.multiStartRun += 1;
            workerRef.current?.postMessage({
              type: "start",
              payload: {
                budget: comp.budget,
                prestige: comp.prestige,
                initialState: ui.upgrades,
                numCandidates: cfg.numCandidates,
                runsPerCombo: cfg.runsPerCombo,
                seedBase: 1_000_000 + comp.methodIndex * 500 + comp.replicateIndex * 10 + (comp.multiStartRun + 1),
                waveBandStep: clampInt(ui.waveBandStep ?? 0, 0, 20) || null,
                useRewardMilestones: ui.useRewardMilestones ?? false,
                targetWave: ui.targetWaveOverride ? clampInt(ui.targetWave, 0, 99999) : null,
              },
            });
            setProgress(null);
            return;
          }
          let validationWave: number | undefined;
          if (comp.validationSims > 0 && r.bestState) {
            const prestige = comp.prestige;
            const { player, enemy } = applyUpgrades(r.bestState.levels, prestige, r.bestState.gemLevels);
            const seed = (Date.now() & 0x7fffffff) + comp.methodIndex * 1000 + comp.replicateIndex;
            const sim = runFullSimulation(player, enemy, comp.validationSims, mulberry32(seed));
            validationWave = sim.avgWave;
          }
          comp.results.push({
            methodId: comp.methods[comp.methodIndex]!,
            replicateIndex: comp.replicateIndex,
            bestWave: r.bestWave,
            validationWave,
            result: optResult,
            statistics: r.statistics ?? {},
            bestWaveBand: r.bestWaveBand,
            bestCurrencyPerHour: r.bestCurrencyPerHour,
          });
          comp.replicateIndex += 1;
          comp.multiStartRun = 0;
          if (comp.replicateIndex < comp.replicates) {
            const sameCfg = getMethodConfig(comp.methods[comp.methodIndex]!, comp.baseN, comp.baseR);
            workerRef.current?.postMessage({
              type: "start",
              payload: {
                budget: comp.budget,
                prestige: comp.prestige,
                initialState: ui.upgrades,
                numCandidates: sameCfg.numCandidates,
                runsPerCombo: sameCfg.runsPerCombo,
                seedBase: 1_000_000 + comp.methodIndex * 500 + comp.replicateIndex * 10,
                waveBandStep: clampInt(ui.waveBandStep ?? 0, 0, 20) || null,
                useRewardMilestones: ui.useRewardMilestones ?? false,
                targetWave: ui.targetWaveOverride ? clampInt(ui.targetWave, 0, 99999) : null,
              },
            });
            setProgress(null);
            return;
          }
          comp.replicateIndex = 0;
          comp.methodIndex += 1;
          if (comp.methodIndex < comp.methods.length) {
            const nextCfg = getMethodConfig(comp.methods[comp.methodIndex]!, comp.baseN, comp.baseR);
            workerRef.current?.postMessage({
              type: "start",
              payload: {
                budget: comp.budget,
                prestige: comp.prestige,
                initialState: ui.upgrades,
                numCandidates: nextCfg.numCandidates,
                runsPerCombo: nextCfg.runsPerCombo,
                seedBase: 1_000_000 + comp.methodIndex * 500,
                waveBandStep: clampInt(ui.waveBandStep ?? 0, 0, 20) || null,
                useRewardMilestones: ui.useRewardMilestones ?? false,
                targetWave: ui.targetWaveOverride ? clampInt(ui.targetWave, 0, 99999) : null,
              },
            });
            setProgress(null);
            return;
          }
          const byMethod = new Map<EventMcComparisonMethodId, ComparisonReplicateRow[]>();
          for (const row of comp.results) {
            const arr = byMethod.get(row.methodId) ?? [];
            arr.push(row);
            byMethod.set(row.methodId, arr);
          }
          function sumStats(values: number[]) {
            if (!values.length) return { mean: 0, std: 0, min: 0, max: 0, median: 0 };
            const mean = values.reduce((a, b) => a + b, 0) / values.length;
            const std = values.length > 1 ? Math.sqrt(values.reduce((s, v) => s + (v - mean) ** 2, 0) / (values.length - 1)) : 0;
            const sorted = values.slice().sort((a, b) => a - b);
            return {
              mean,
              std,
              min: Math.min(...values),
              max: Math.max(...values),
              median: sorted[Math.floor(sorted.length / 2)] ?? 0,
            };
          }
          const methodResults: ComparisonMethodSummary[] = [];
          for (const methodId of comp.methods) {
            const rows = byMethod.get(methodId) ?? [];
            if (rows.length === 0) continue;
            const bestWaves = rows.map((x) => x.bestWave);
            const valWaves = rows.map((x) => x.validationWave).filter((v): v is number => v != null);
            const sBest = sumStats(bestWaves);
            const sVal = valWaves.length > 0 ? sumStats(valWaves) : undefined;
            methodResults.push({
              methodId,
              label: getMethodLabel(methodId),
              replicates: rows,
              summary: {
                meanBest: sBest.mean,
                stdBest: sBest.std,
                minBest: sBest.min,
                maxBest: sBest.max,
                medianBest: sBest.median,
                meanVal: sVal?.mean,
                stdVal: sVal?.std,
              },
            });
          }
          const winner = methodResults.reduce((a, b) => (a.summary.meanBest >= b.summary.meanBest ? a : b), methodResults[0]!);
          const winnerResult = winner.replicates[0]?.result ?? optResult;
          setComparisonResult({ methodResults, winnerId: winner.methodId });
          setResult(winnerResult);
          setPrestigeReachMcResult(null);
          setMcStats(r);
          setAppliedSinceLastOptimize(false);
          comparisonRunRef.current = null;
        } else {
          setResult(optResult);
          setPrestigeReachMcResult(null);
          setMcStats(r);
          setAppliedSinceLastOptimize(false);
        }
        setRunning(false);
        setProgress(null);
        setMcMeta(null);
        return;
      }
      if (msg?.type === "cancelled") {
        comparisonRunRef.current = null;
        setRunning(false);
        setProgress(null);
        setMcMeta(null);
        return;
      }
      if (msg?.type === "error") {
        comparisonRunRef.current = null;
        setRunning(false);
        setProgress(null);
        setMcMeta(null);
        setError(msg.payload?.message ?? "MC failed.");
        return;
      }
    };
  }

  function onOptimizeGuidedMc() {
    setError(null);
    setProgress(null);
    setMcStats(null);
    setAppliedSinceLastOptimize(false);

    const budget: Budget = {
      1: Math.max(0, parseNumber(ui.budget1)),
      2: Math.max(0, parseNumber(ui.budget2)),
      3: Math.max(0, parseNumber(ui.budget3)),
      4: Math.max(0, parseNumber(ui.budget4)),
    };
    const total = budget[1] + budget[2] + budget[3] + budget[4];
    if (total <= 0) {
      setResult(null);
      setPrestigeReachMcResult(null);
      setError("Please enter at least some currency.");
      return;
    }

    const prestige = clampInt(ui.prestige, 0, 999);

    try {
      lastInitialRef.current = copyState(ui.upgrades);
      ensureWorker();
      comparisonRunRef.current = null;
      setRunning(true);
      setMcMeta({ startedAt: Date.now(), totalSims: Math.max(1, clampInt(ui.mcCandidates, 1, 20000)) * Math.max(1, clampInt(ui.mcRunsPerCombo, 1, 2000)) });
      const w = workerRef.current;
      if (!w) {
        setRunning(false);
        return;
      }
      w.postMessage({
        type: "start",
        payload: {
          budget,
          prestige,
          initialState: ui.upgrades,
          numCandidates: Math.max(1, clampInt(ui.mcCandidates, 1, 20000)),
          runsPerCombo: Math.max(1, clampInt(ui.mcRunsPerCombo, 1, 2000)),
          seedBase: null,
          waveBandStep: clampInt(ui.waveBandStep ?? 0, 0, 20) || null,
          useRewardMilestones: ui.useRewardMilestones ?? false,
          targetWave: ui.targetWaveOverride ? clampInt(ui.targetWave, 0, 99999) : null,
        },
      });
    } catch (e) {
      // fallback main-thread
      setRunning(true);
      setMcMeta({ startedAt: Date.now(), totalSims: Math.max(1, ui.mcCandidates) * Math.max(1, ui.mcRunsPerCombo) });
      try {
        const r = monteCarloOptimizeGuided({
          budget,
          prestige,
          initialState: ui.upgrades,
          numRuns: ui.mcCandidates,
          eventRunsPerCombination: Math.max(1, clampInt(ui.mcRunsPerCombo, 1, 2000)),
          seedBase: null,
          waveBandStep: clampInt(ui.waveBandStep ?? 0, 0, 20) || null,
          useRewardMilestones: ui.useRewardMilestones ?? false,
          targetWave: ui.targetWaveOverride ? clampInt(ui.targetWave, 0, 99999) : null,
          progressCallback: (cur: number, total2: number, curWave: number, bestWave: number) => {
            if (cur % 25 === 0 || cur === total2) setProgress({ cur, total: total2, curWave, bestWave });
          },
        });
        const bandMode = r.bestWaveBand != null;
        const byReward = r.tieBreakByRewardMilestones === true;
        const recs = [
          "Monte Carlo Optimization (guided MC)",
          `N=${ui.mcCandidates} candidates, ${ui.mcRunsPerCombo} runs/combo`,
          `Best Wave: ${r.bestWave.toFixed(1)}`,
          ...(bandMode
            ? [
                byReward
                  ? `Reward milestone: ${r.bestWaveBand} (tie-break by currency/h)`
                  : `Wave band: ${r.bestWaveBand} (step ${r.waveBandStep ?? 0}; tie-break by currency/h)`,
                `Currency/h: ${Number(r.bestCurrencyPerHour).toLocaleString(undefined, { maximumFractionDigits: 0 })}`,
              ]
            : []),
          `Average Wave: ${(r.statistics.mean_wave ?? 0).toFixed(1)} ± ${(r.statistics.std_dev_wave ?? 0).toFixed(1)}`,
          `Wave Range: ${(r.statistics.min_wave ?? 0).toFixed(1)} - ${(r.statistics.max_wave ?? 0).toFixed(1)}`,
          `Median Wave: ${(r.statistics.median_wave ?? 0).toFixed(1)}`,
        ];
        setMcStats(r);
        setAppliedSinceLastOptimize(false);
        setPrestigeReachMcResult(null);
        setResult({
          upgrades: r.bestState,
          expectedWave: r.bestWave,
          expectedTime: r.bestTime,
          materialsSpent: r.materialsSpent,
          materialsRemaining: r.materialsRemaining,
          playerStats: r.playerStats,
          enemyStats: r.enemyStats,
          recommendations: recs,
          breakpoints: [],
        });
      } catch (err) {
        setError(err instanceof Error ? err.message : "MC failed.");
      } finally {
        setRunning(false);
        setProgress(null);
        setMcMeta(null);
      }
    }
  }

  function onRunComparison() {
    const methods = (ui.comparisonMethods ?? []).filter((m) => COMPARISON_METHOD_IDS.includes(m));
    if (methods.length === 0) {
      setError("Select at least one algorithm in the Developer comparison window.");
      return;
    }
    const budget: Budget = {
      1: Math.max(0, parseNumber(ui.budget1)),
      2: Math.max(0, parseNumber(ui.budget2)),
      3: Math.max(0, parseNumber(ui.budget3)),
      4: Math.max(0, parseNumber(ui.budget4)),
    };
    const total = budget[1] + budget[2] + budget[3] + budget[4];
    if (total <= 0) {
      setError("Please enter at least some currency.");
      return;
    }
    const prestige = clampInt(ui.prestige, 0, 999);
    const baseN = Math.max(1, clampInt(ui.mcCandidates, 1, 20000));
    const baseR = Math.max(1, clampInt(ui.mcRunsPerCombo, 1, 2000));
    setError(null);
    setProgress(null);
    setComparisonResult(null);
    lastInitialRef.current = copyState(ui.upgrades);
    ensureWorker();
    setRunning(true);
    const replicates = Math.max(1, clampInt(ui.comparisonReplicates ?? 3, 1, 10));
    const validationSims = Math.max(0, clampInt(ui.comparisonValidationSims ?? 0, 0, 2000));
    const totalSims =
      methods.reduce((sum, m) => {
        const cfg = getMethodConfig(m, baseN, baseR);
        return sum + replicates * cfg.seeds * cfg.numCandidates * cfg.runsPerCombo;
      }, 0) + (validationSims > 0 ? methods.length * replicates * validationSims : 0);
    setMcMeta({ startedAt: Date.now(), totalSims });
    comparisonRunRef.current = {
      active: true,
      methods,
      methodIndex: 0,
      replicateIndex: 0,
      multiStartRun: 0,
      results: [],
      budget,
      prestige,
      baseN,
      baseR,
      replicates,
      validationSims,
    };
    const firstCfg = getMethodConfig(methods[0]!, baseN, baseR);
    const w = workerRef.current;
    if (!w) return;
    w.postMessage({
      type: "start",
      payload: {
        budget,
        prestige,
        initialState: ui.upgrades,
        numCandidates: firstCfg.numCandidates,
        runsPerCombo: firstCfg.runsPerCombo,
        seedBase: 1_000_000,
        waveBandStep: clampInt(ui.waveBandStep ?? 0, 0, 20) || null,
        useRewardMilestones: ui.useRewardMilestones ?? false,
        targetWave: ui.targetWaveOverride ? clampInt(ui.targetWave, 0, 99999) : null,
      },
    });
  }

  function onCancel() {
    if (workerRef.current) workerRef.current.postMessage({ type: "cancel" });
    setRunning(false);
    setProgress(null);
    setMcMeta(null);
  }

  function doResetUpgrades() {
    const next = copyState(ui.upgrades);
    next.levels[1].fill(0);
    next.levels[2].fill(0);
    next.levels[3].fill(0);
    next.levels[4].fill(0);
    setUi((s) => ({ ...s, upgrades: next }));
    setResult(null);
    setPrestigeReachMcResult(null);
    setMcStats(null);
    setError(null);
  }

  function onResetUpgradesClick() {
    if (!resetUpgradesArmed) {
      setResetUpgradesArmed(true);
      return;
    }
    setResetUpgradesArmed(false);
    if (!confirmDanger("Confirm reset upgrades? This resets Tier 1–4 currency upgrades only. Prestige and gem upgrades are kept.")) return;
    doResetUpgrades();
  }

  function onAddPoints() {
    if (!result) return;
    // Apply recommended levels directly (same intent as "✨ Add Points!" in Tk GUI).
    setUi((s) => ({ ...s, upgrades: copyState(result.upgrades) }));
    setAppliedSinceLastOptimize(true);
  }

  function applyComparisonResult(optResult: OptimizationResult) {
    setUi((s) => ({ ...s, upgrades: copyState(optResult.upgrades) }));
    setResult(optResult);
    setPrestigeReachMcResult(null);
    setAppliedSinceLastOptimize(true);
  }

  return (
    <div className="container">
      <div className="header">
        <div>
          <h1 className="title">Event Budget Optimizer</h1>
          <p className="subtitle">Saves upgrades/prestige automatically in your browser (localStorage).</p>
          <div className="worldMonumentsBlock">
            <span className="worldMonumentsLabel">Your Max World:</span>
            <span className="mono worldMonumentsValue">{ui.worldMonuments}</span>
            <div className="worldMonumentsButtons">
              {[1, 2, 3, 4].map((n) => (
                <button
                  key={n}
                  type="button"
                  className={ui.worldMonuments === n ? "btn" : "btn btnSecondary"}
                  onClick={() => setUi((s) => ({ ...s, worldMonuments: n }))}
                  title={`${n} World Monument${n === 1 ? "" : "s"}`}
                >
                  {n}
                </button>
              ))}
            </div>
            <Tooltip
              content={{
                title: "Your Max World",
                sections: [
                  {
                    heading: "Reward multiplier",
                    lines: [
                      "All rewards except Gifts, Mythic Chests, and Skins are multiplied by ×2 for each World Monument you build.",
                      "Your Max World 1 = 0 monuments built → ×1. World 2 → ×2, World 3 → ×4, World 4 → ×8.",
                    ],
                  },
                  {
                    heading: "Saved",
                    lines: ["This value is saved automatically in this browser."],
                  },
                ],
              }}
            />
          </div>
        </div>
        <div className="badge">Budget Optimizer • Guided MC</div>
      </div>

      <div className="eventSimTop">
        <div className="budgetBar">
          <div className="panelHeader" style={{ marginBottom: 6 }}>
            <h2 className="panelTitle">
              Currency budget
              <Tooltip
                content={{
                  title: "Currency budget",
                  sections: [
                    { heading: "What is this?", lines: ["Enter your available event currencies (Tier 1–4)."] },
                    { heading: "How it is used", lines: ["The optimizer spends these currencies to suggest which upgrade points to buy."] },
                  ],
                }}
              />
            </h2>
            <p className="panelHint"></p>
          </div>

          <div className="budgetInputs">
            {[1, 2, 3, 4].map((tier) => {
              const icon = currencyIconFilename(tier);
              const v = (tier === 1 ? ui.budget1 : tier === 2 ? ui.budget2 : tier === 3 ? ui.budget3 : ui.budget4) as string;
              return (
                <div className="budgetRow" key={tier}>
                  <Sprite path={icon ? (icon.startsWith("http") ? icon : `sprites/event/${icon}`) : null} alt={`Currency ${tier}`} className="iconSmall" label={icon ?? ""} />
                  <input
                    className="input"
                    inputMode="decimal"
                    placeholder={`Tier ${tier}`}
                    value={v}
                    onChange={(e) =>
                      setUi((s) => {
                        const val = e.target.value;
                        if (tier === 1) return { ...s, budget1: val };
                        if (tier === 2) return { ...s, budget2: val };
                        if (tier === 3) return { ...s, budget3: val };
                        return { ...s, budget4: val };
                      })
                    }
                  />
                </div>
              );
            })}
          </div>

          <Collapsible
            id="event-target-prestige"
            className="eventPlayerStatsDark eventTargetPrestige"
            title="Target Wave (Advanced)"
            defaultExpanded={false}
            headerOverlay={() => (
              <div className="eventTargetPrestigeShaderWrap">
                <SilverHologramCanvas />
              </div>
            )}
          >
            <div className="eventPlayerStatsDarkInner">
              <label className="labelRow">
                <input
                  type="checkbox"
                  checked={ui.targetWaveOverride}
                  onChange={(e) =>
                    setUi((s) => ({ ...s, targetWaveOverride: e.target.checked }))
                  }
                />
                <span>Override simulation with target wave goal</span>
              </label>
              {ui.targetWaveOverride && (
                <div style={{ marginTop: 6, display: "flex", flexDirection: "column", gap: 6 }}>
                  <div className="kv kvCompact">
                    <kbd>Target Wave</kbd>
                    <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
                      {TARGET_WAVE_OPTIONS.map((w) => (
                        <button
                          key={w}
                          type="button"
                          className={ui.targetWave === w ? "eventTargetWaveActive" : ""}
                          onClick={() => setUi((s) => ({ ...s, targetWave: w as TargetWaveOption }))}
                        >
                          Wave {w}
                        </button>
                      ))}
                    </div>
                  </div>
                  <div className="kv kvCompact">
                    <span>Enemy HP at wave {ui.targetWave}</span>
                    <span className="mono">{formatInt(getEnemyHpAtWave(currentEnemyStats, ui.targetWave))}</span>
                  </div>
                </div>
              )}
              <Tooltip
                content={{
                  title: "Target Wave (Advanced)",
                  sections: [
                    {
                      heading: "Target wave",
                      lines: [
                        "When enabled, the optimizer suggests upgrades to get you closer to the target wave (you don't have to reach it).",
                        "If your current attack already one-shots enemies at the target wave, damage-only upgrades (pure atk, crit) are skipped; HP, speed, and atk+HP upgrades are still suggested.",
                        "Wave 250 is the last reward milestone in Event Results, so it is the recommended default goal.",
                      ],
                    },
                  ],
                }}
              />
            </div>
          </Collapsible>

          <Collapsible
            id="event-player-stats"
            className="eventPlayerStatsDark"
            title={
              <span style={{ display: "inline-flex", alignItems: "baseline", gap: 8 }}>
                <span>Player stats</span>
                <span className="small">(info only)</span>
              </span>
            }
            defaultExpanded={false}
          >
            <div className="eventPlayerStatsDarkInner">
              <div className="kv kvCompact">
                <kbd>Max HP</kbd>
              <div className="mono">{formatInt(currentPlayerStats.health)}</div>
              <kbd>Attack Damage</kbd>
              <div className="mono" style={{ display: "flex", alignItems: "center", gap: 6 }}>
                <Tooltip content={{ title: "Max wave one-hit", lines: [maxOneHitWaveTooltipLine] }} />
                <span>{formatInt(currentPlayerStats.atk)}</span>
              </div>
              <kbd>Attack Speed</kbd>
              <div className="mono">{currentPlayerStats.atkSpeed.toFixed(2)}</div>
              <kbd>Move Speed</kbd>
              <div className="mono">{currentPlayerStats.walkSpeed.toFixed(2)}</div>
              <kbd>Crit Chance</kbd>
              <div className="mono">{currentPlayerStats.crit.toFixed(1)}%</div>
              <kbd>Crit Damage</kbd>
              <div className="mono">{currentPlayerStats.critDmg.toFixed(2)}×</div>
              <kbd>2× Currencies</kbd>
              <div className="mono">{currentPlayerStats.x2Money.toFixed(0)}</div>
              <kbd>Event Speed</kbd>
              <div className="mono">{currentPlayerStats.gameSpeed.toFixed(2)}</div>
              <kbd>Block chance</kbd>
              <div className="mono">{formatPct01(currentPlayerStats.blockChance, 1)}</div>
              <kbd>Prestige HP/Dmg</kbd>
              <div className="mono">{(1 + currentPlayerStats.prestigeBonusScale * ui.prestige).toFixed(1)}×</div>
              <kbd>5× Currencies</kbd>
              <div className="mono">{currentPlayerStats.x5Money.toFixed(0)}</div>
              </div>
            </div>
          </Collapsible>

          <div className="btnRow" style={{ marginTop: 0 }}>
            <button className="btn" onClick={onOptimizeGuidedMc} disabled={running || prestigeReachMcRunning}>
              Optimize (Guided MC)
            </button>
            <Tooltip
              content={{
                title: "Optimize (Guided MC)",
                sections: [
                  { heading: "How it works", lines: ["Tries many candidate allocations and evaluates them via simulation."] },
                  { heading: "Total work", lines: ["Total simulations = N candidates × runs per combo."] },
                ],
              }}
            />
            {running ? (
              <button className="btn btnSecondary" onClick={onCancel}>
                Cancel
              </button>
            ) : prestigeReachMcRunning ? (
              <button
                type="button"
                className="btn btnSecondary"
                onClick={() => {
                  prestigeReachCancelRef.current = true;
                  if (workerRef.current) workerRef.current.postMessage({ type: "cancel" });
                }}
              >
                Cancel
              </button>
            ) : null}
          </div>

          {running ? (
            <div className="kv">
              <kbd>Status</kbd>
              <div className="mono">Running…</div>
              <kbd>Progress</kbd>
              <div className="mono">
                {progress ? (
                  <>
                    {progress.cur}/{progress.total} ({Math.floor((progress.cur / progress.total) * 100)}%)
                  </>
                ) : (
                  <>Starting…</>
                )}
              </div>
              <kbd>Current</kbd>
              <div className="mono">{progress ? `Wave ${progress.curWave.toFixed(1)}` : "—"}</div>
              <kbd>Best</kbd>
              <div className="mono">{progress ? `Wave ${progress.bestWave.toFixed(1)}` : "—"}</div>
              <kbd>Runs done</kbd>
              <div className="mono">{progress ? formatInt(progress.cur * ui.mcRunsPerCombo) : "—"}</div>
              <kbd>Total runs</kbd>
              <div className="mono">{progress ? formatInt(progress.total * ui.mcRunsPerCombo) : "—"}</div>
            </div>
          ) : prestigeReachMcRunning ? (
            <div className="kv">
              <kbd>Status</kbd>
              <div className="mono">Running prestige-reach MC…</div>
              <kbd>Simulating</kbd>
              <div className="mono">{prestigeReachMcProgress ? `${prestigeReachMcProgress.hour}h farming` : "…"}</div>
              <kbd>Progress</kbd>
              <div className="mono">
                {prestigeReachMcProgress
                  ? `${Math.floor((prestigeReachMcProgress.currentRun / prestigeReachMcProgress.totalRuns) * 100)}%`
                  : "Starting…"}
              </div>
            </div>
          ) : null}

          <div className="small">
            <span className="mono">
              N={ui.mcCandidates} × runs={ui.mcRunsPerCombo} = {formatInt(ui.mcCandidates * ui.mcRunsPerCombo)} event sims
            </span>
          </div>
        </div>

        <div className="panel panelResults">
          <div className="panelHeader">
            <h2 className="panelTitle">Results</h2>
            <p className="panelHint">{result ? "Calculated." : "Run the optimizer to see recommendations."}</p>
          </div>

          {error ? <div className="error">{error}</div> : null}

          {result ? (
            <>
              <div className="kv" style={{ marginTop: 10 }}>
                <span style={{ display: "inline-flex", alignItems: "center", gap: 6 }}>
                  <kbd>Estimated wave</kbd>
                  <Tooltip
                    content={{
                      title: "Estimated wave",
                      lines: [
                        "Mean wave (from the optimizer runs) reached with the suggested build.",
                        "The value is the average over the evaluation runs for the chosen build; ± is the standard deviation.",
                      ],
                    }}
                  />
                </span>
                <div className="mono" style={{ display: "inline-flex", alignItems: "center", gap: 8 }}>
                  {result.expectedWave.toFixed(1)}
                  {mcStats?.statistics?.std_dev_wave != null && Number.isFinite(mcStats.statistics.std_dev_wave) ? (
                    <span className="small" style={{ color: "var(--muted)" }}>±{mcStats.statistics.std_dev_wave.toFixed(1)}</span>
                  ) : null}
                  <button
                    type="button"
                    className="btn btnSecondary"
                    style={{ padding: "4px 8px", fontSize: 12, minHeight: "auto" }}
                    title="Wave distribution histogram"
                    disabled={waveHistogramLoading}
                    onClick={() => {
                      if (!result) return;
                      setWaveHistogramOpen(true);
                      setWaveHistogramLoading(true);
                      setWaveHistogramSamples(null);
                      setWaveHistogramHpPerWave(null);
                      setTimeout(() => {
                        const rng = mulberry32((Date.now() & 0x7fffffff) >>> 0);
                        const sim = runFullSimulationWithHpPerWave(result.playerStats, result.enemyStats, 500, rng);
                        const waves = sim.results.map((r) => r[0]);
                        setWaveHistogramSamples(waves);
                        setWaveHistogramHpPerWave(sim.hpPerWave.length > 0 ? sim.hpPerWave : null);
                        setWaveHistogramLoading(false);
                      }, 0);
                    }}
                  >
                    {waveHistogramLoading ? "…" : "Chart"}
                  </button>
                </div>
                <span style={{ display: "inline-flex", alignItems: "center", gap: 6 }}>
                  <kbd>Estimated time</kbd>
                  <Tooltip
                    content={{
                      title: "Estimated time",
                      lines: [
                        "Mean time (from the optimizer runs) to complete the run with the suggested build.",
                        "The value is the average over the evaluation runs for the chosen build; ± is the standard deviation.",
                      ],
                    }}
                  />
                </span>
                <div className="mono">
                  {formatTime(result.expectedTime)}
                  {mcStats?.statistics?.std_dev_time != null && Number.isFinite(mcStats.statistics.std_dev_time) ? (
                    <span className="small" style={{ color: "var(--muted)", marginLeft: 6 }}>±{formatTime(mcStats.statistics.std_dev_time)}</span>
                  ) : null}
                </div>
                {mcStats?.bestWaveBand != null ? (
                  <>
                    <span style={{ display: "inline-flex", alignItems: "center", gap: 4 }}>
                      <kbd>{mcStats.tieBreakByRewardMilestones ? "Reward milestone" : "Wave band"}</kbd>
                      {mcStats.tieBreakByRewardMilestones ? (
                        <Tooltip
                          content={{
                            title: "Reward milestone",
                            lines: [
                              "Next reward milestone after your current prestige (you have cleared at least wave " + getPrestigeWaveRequirement(ui.prestige) + ").",
                            ],
                          }}
                        />
                      ) : null}
                    </span>
                    <div className="mono" style={{ display: "flex", alignItems: "center", gap: 6, flexWrap: "wrap" }}>
                      {ui.targetWaveOverride ? (
                        (() => {
                          const wave = ui.targetWave;
                          const info = getRewardMilestoneDisplayLabel(wave, ui.worldMonuments);
                          return (
                            <>
                              Wave {wave}
                              {info ? (
                                <>
                                  {" "}
                                  (
                                  <img
                                    src={info.iconUrl}
                                    alt=""
                                    className="iconSmall"
                                    style={{ width: 18, height: 18, verticalAlign: "middle" }}
                                    referrerPolicy="no-referrer"
                                  />
                                  {info.label})
                                </>
                              ) : null}
                            </>
                          );
                        })()
                      ) : mcStats.tieBreakByRewardMilestones ? (
                        (() => {
                          const nextWave = getNextRewardMilestoneAfterPrestige(ui.prestige);
                          const info = getRewardMilestoneDisplayLabel(nextWave, ui.worldMonuments);
                          return (
                            <>
                              Wave {nextWave}
                              {info ? (
                                <>
                                  {" "}
                                  (
                                  <img
                                    src={info.iconUrl}
                                    alt=""
                                    className="iconSmall"
                                    style={{ width: 18, height: 18, verticalAlign: "middle" }}
                                    referrerPolicy="no-referrer"
                                  />
                                  {info.label})
                                </>
                              ) : null}
                            </>
                          );
                        })()
                      ) : (
                        <>
                          Wave {mcStats.bestWaveBand}
                          {(() => {
                            const info = getRewardMilestoneDisplayLabel(mcStats.bestWaveBand, ui.worldMonuments);
                            return info ? (
                              <>
                                {" "}
                                (
                                <img
                                  src={info.iconUrl}
                                  alt=""
                                  className="iconSmall"
                                  style={{ width: 18, height: 18, verticalAlign: "middle" }}
                                  referrerPolicy="no-referrer"
                                />
                                {info.label})
                              </>
                            ) : null;
                          })()}
                        </>
                      )}
                    </div>
                    <span style={{ display: "inline-flex", alignItems: "center", gap: 6 }}>
                      <kbd>Currency/h</kbd>
                      <Tooltip
                        content={{
                          title: "Currency/h",
                          sections: [
                            {
                              heading: "What it is",
                              lines: [
                                "Income per hour if you continue with the suggested build.",
                                "How much of each currency type (Tier 1–4) you earn per hour with this build.",
                              ],
                            },
                            ...(mcStats.bestCurrencyPerHourByTier
                              ? [
                                  {
                                    heading: "Per tier (per hour)",
                                    lines: ([1, 2, 3, 4] as const).map((tier) => {
                                      const icon = currencyIconFilename(tier);
                                      const val = formatInt(mcStats.bestCurrencyPerHourByTier![tier]);
                                      return (
                                        <span key={tier} style={{ display: "flex", alignItems: "center", gap: 8 }}>
                                          <Sprite
                                            path={icon ? (icon.startsWith("http") ? icon : `sprites/event/${icon}`) : null}
                                            alt={`Currency ${tier}`}
                                            className="iconSmall"
                                            label={icon ?? ""}
                                          />
                                          <span>Tier {tier}: {val}</span>
                                        </span>
                                      );
                                    }),
                                  },
                                ]
                              : []),
                          ],
                        }}
                      />
                    </span>
                    <div className="mono">
                      {Number(mcStats.bestCurrencyPerHour ?? 0).toLocaleString(undefined, { maximumFractionDigits: 0 })}
                    </div>
                  </>
                ) : null}
              </div>

              <div className="sectionTitle">Upgrade plan</div>
              <div className="btnRow">
                <button className="btn btnGood" onClick={onAddPoints} disabled={!result || appliedSinceLastOptimize}>
                  {appliedSinceLastOptimize ? "Applied" : "Add Points!"}
                </button>
                <Tooltip
                  content={{
                    title: "Add Points!",
                    sections: [
                      { heading: "What it does", lines: ["Applies the recommended upgrade points to your current upgrade levels."] },
                      { heading: "Note", lines: ["Disabled after applying, until you run Optimize again."] },
                    ],
                  }}
                />
              </div>
              {[1, 2, 3, 4].map((tier) => {
                const levels = result.upgrades.levels[tier as 1 | 2 | 3 | 4];
                const initial2 = lastInitialRef.current?.levels?.[tier as 1 | 2 | 3 | 4] ?? null;
                const picked = levels
                  .map((lvl, idx) => ({ lvl, idx }))
                  .filter((x) => (initial2 ? x.lvl > (initial2[x.idx] ?? 0) : x.lvl > 0))
                  .map((x) => ({ ...x, add: initial2 ? x.lvl - (initial2[x.idx] ?? 0) : x.lvl }));
                const spent = result.materialsSpent[tier as 1 | 2 | 3 | 4];
                const remaining = result.materialsRemaining[tier as 1 | 2 | 3 | 4];
                return (
                  <div className="tierBlock" key={tier}>
                    <div className="tierHead">
                      <p className="tierTitle">Tier {tier}</p>
                      <p className="small">
                        Spent {formatInt(spent)} • Remaining {formatInt(remaining)}
                      </p>
                    </div>
                    {picked.length ? (
                      <ul className="list">
                        {picked.map(({ idx, add, lvl }) => {
                          const max = getMaxLevelWithCaps(tier as 1 | 2 | 3 | 4, idx, result.upgrades);
                          return (
                            <li key={idx}>
                              <span className="mono" style={{ whiteSpace: "pre-line" }}>{UPGRADE_SHORT_NAMES[tier][idx]}</span> + <span className="mono eventUpgradePlanAdd">{add}</span>
                              <span className="small" style={{ color: "var(--muted)", marginLeft: 6 }}>(→ lvl {lvl}/{max})</span>
                            </li>
                          );
                        })}
                      </ul>
                    ) : (
                      <div className="small">No upgrades purchased in this tier.</div>
                    )}
                  </div>
                );
              })}

              <div className="btnRow" style={{ alignItems: "center", gap: 6 }}>
                <span className="small" style={{ color: "var(--muted)" }}>Recommendations & MC statistics</span>
                <Tooltip
                  content={{
                    title: "Recommendations & MC statistics",
                    sections: [
                      { heading: "Recommendations", lines: result.recommendations },
                      ...(mcStats
                        ? [
                            {
                              heading: "MC statistics",
                              lines: [
                                "Computed over the tried budget points (one wave/time per upgrade allocation), not over individual simulation runs.",
                                `Mean wave: ${(mcStats.statistics.mean_wave ?? 0).toFixed(2)}`,
                                `Std dev wave: ${(mcStats.statistics.std_dev_wave ?? 0).toFixed(2)}`,
                                `Median wave: ${(mcStats.statistics.median_wave ?? 0).toFixed(2)}`,
                                `Wave range: ${(mcStats.statistics.min_wave ?? 0).toFixed(2)} - ${(mcStats.statistics.max_wave ?? 0).toFixed(2)}`,
                                `Mean time: ${(mcStats.statistics.mean_time ?? 0).toFixed(2)}s`,
                                `Std dev time: ${(mcStats.statistics.std_dev_time ?? 0).toFixed(2)}s`,
                              ],
                            },
                          ]
                        : []),
                    ],
                  }}
                />
              </div>

              {(() => {
                const budget1h: Budget =
                  mcStats?.bestCurrencyPerHourByTier != null
                    ? {
                        1: Math.round(mcStats.bestCurrencyPerHourByTier[1]),
                        2: Math.round(mcStats.bestCurrencyPerHourByTier[2]),
                        3: Math.round(mcStats.bestCurrencyPerHourByTier[3]),
                        4: Math.round(mcStats.bestCurrencyPerHourByTier[4]),
                      }
                    : (() => {
                        const mats = calculateMaterials(result.expectedWave, result.playerStats);
                        const scale = result.expectedTime > 0 ? 3600 / result.expectedTime : 0;
                        return {
                          1: Math.round(mats.mat1 * scale),
                          2: Math.round(mats.mat2 * scale),
                          3: Math.round(mats.mat3 * scale),
                          4: Math.round(mats.mat4 * scale),
                        };
                      })();
                const targetWave = ui.targetWaveOverride
                  ? clampInt(ui.targetWave, 0, 99999)
                  : getPrestigeWaveRequirement(ui.prestige + 1);
                const nextPrestigeLabel = ui.prestige + 1;
                const useTargetWaveGoal = ui.targetWaveOverride;
                return (
                  <Collapsible
                    id="event-prestige-1h"
                    title={
                      <span style={{ display: "inline-flex", alignItems: "center", gap: 6 }}>
                        {useTargetWaveGoal ? "Will I reach target wave in X hours farming?" : "Will I reach next prestige in X hours farming?"}
                        <Tooltip
                          content={{
                            title: "Reach target in X hours",
                            sections: [
                              {
                                heading: "What it does",
                                lines: [
                                  "Assumes you apply the suggested build (Add Points) and farm for the selected number of hours.",
                                  "Currency from that farming time is then spent on more upgrades (greedy). MC checks whether that stronger build reaches the target wave.",
                                ],
                              },
                              {
                                heading: "Hours",
                                lines: ["Set 1–24 hours. Only this single scenario is simulated (e.g. 4h farming → one MC run with 4× the per-hour budget)."],
                              },
                              {
                                heading: "Budget shown",
                                lines: ["Per-tier currency per 1h from the suggested build. For Xh the run uses X× that budget."],
                              },
                            ],
                          }}
                        />
                      </span>
                    }
                    defaultExpanded={false}
                  >
                    <div className="small" style={{ marginBottom: 8 }}>
                      Budget per 1h (from suggested build's currency/h): Tier 1 {formatInt(budget1h[1])}, Tier 2 {formatInt(budget1h[2])}, Tier 3 {formatInt(budget1h[3])}, Tier 4 {formatInt(budget1h[4])}.
                      {prestigeReachHoursSelected > 1 ? (
                        <> → After {prestigeReachHoursSelected}h: T1 {formatInt(budget1h[1] * prestigeReachHoursSelected)}, T2 {formatInt(budget1h[2] * prestigeReachHoursSelected)}, T3 {formatInt(budget1h[3] * prestigeReachHoursSelected)}, T4 {formatInt(budget1h[4] * prestigeReachHoursSelected)}.</>
                      ) : null}
                    </div>
                    <div className="small" style={{ marginBottom: 8 }}>
                      {useTargetWaveGoal ? (
                        <>Target wave: <span className="mono">{targetWave}</span></>
                      ) : (
                        <>Next prestige (you are {ui.prestige}): wave <span className="mono">{targetWave}</span> for prestige {nextPrestigeLabel}</>
                      )}
                    </div>
                    <div style={{ display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap" }}>
                        <label className="small" style={{ display: "flex", alignItems: "center", gap: 6 }}>
                          Hours:
                          <input
                            className="input mono"
                            type="number"
                            min={1}
                            max={PRESTIGE_REACH_HOURS_MAX}
                            step={1}
                            value={prestigeReachHoursSelected}
                            onChange={(e) => setPrestigeReachHoursSelected(Math.max(1, Math.min(PRESTIGE_REACH_HOURS_MAX, clampInt(Number(e.target.value), 1, PRESTIGE_REACH_HOURS_MAX))))}
                            disabled={prestigeReachMcRunning}
                            style={{ width: 48 }}
                          />
                        </label>
                        <button
                          className="btn"
                          disabled={prestigeReachMcRunning}
                          onClick={() => {
                            prestigeReachCancelRef.current = false;
                            const hours = Math.max(1, Math.min(PRESTIGE_REACH_HOURS_MAX, prestigeReachHoursSelected));
                            setPrestigeReachMcRunning(true);
                            setPrestigeReachMcResult(null);
                            setPrestigeReachMcProgress({ hour: hours, currentRun: 0, totalRuns: Math.max(1, clampInt(ui.mcCandidates, 1, 10000)) });
                            const initial = copyState(result.upgrades);
                            const prestige = clampInt(ui.prestige, 0, 999);
                            const numCandidates = Math.max(1, clampInt(ui.mcCandidates, 1, 10000));
                            const runsPerCombo = Math.max(1, clampInt(ui.mcRunsPerCombo, 1, 2000));
                            const waveBandStep = clampInt(ui.waveBandStep ?? 0, 0, 20) || null;
                            const useRewardMilestones = ui.useRewardMilestones ?? false;
                            const budgetForHours: Budget = {
                              1: budget1h[1] * hours,
                              2: budget1h[2] * hours,
                              3: budget1h[3] * hours,
                              4: budget1h[4] * hours,
                            };
                            prestigeReachContextRef.current = {
                              hour: hours,
                              results: [],
                              initial,
                              budget1h,
                              targetWave,
                              prestige,
                              numCandidates,
                              runsPerCombo,
                              waveBandStep,
                              useRewardMilestones,
                            };
                            workerJobRef.current = "prestigeReach";
                            ensureWorker();
                            workerRef.current?.postMessage({
                              type: "start",
                              payload: {
                                budget: budgetForHours,
                                prestige,
                                initialState: initial,
                                numCandidates,
                                runsPerCombo,
                                seedBase: null,
                                waveBandStep,
                                useRewardMilestones,
                                targetWave: ui.targetWaveOverride ? clampInt(ui.targetWave, 0, 99999) : null,
                              },
                            });
                          }}
                        >
                          {prestigeReachMcRunning ? "Running MC…" : "Run MC"}
                        </button>
                        {prestigeReachMcRunning ? (
                          <button
                            type="button"
                            className="btn btnSecondary"
                            onClick={() => {
                              prestigeReachCancelRef.current = true;
                              if (workerRef.current) workerRef.current.postMessage({ type: "cancel" });
                            }}
                          >
                            Cancel
                          </button>
                        ) : null}
                      </div>
                      {prestigeReachMcRunning && prestigeReachMcProgress ? (
                        <div className="kv small" style={{ marginTop: 8 }}>
                          <kbd>Simulating</kbd>
                          <div className="mono">{prestigeReachMcProgress.hour}h farming</div>
                          <kbd>Progress</kbd>
                          <div className="mono">
                            {Math.floor((prestigeReachMcProgress.currentRun / prestigeReachMcProgress.totalRuns) * 100)}%
                          </div>
                        </div>
                      ) : null}
                      {prestigeReachMcResult && prestigeReachMcResult.length > 0 ? (
                        <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
                          {prestigeReachMcResult[0]!.probability <= PRESTIGE_REACH_SIGNIFICANT ? (
                            <div className="mono" style={{ color: "var(--muted)" }}>
                              {useTargetWaveGoal
                                ? `Even with ${prestigeReachHoursSelected}h farming, chance to reach target wave is ≤95%.`
                                : `Even with ${prestigeReachHoursSelected}h farming, chance to reach next Prestige is ≤95%.`}
                            </div>
                          ) : null}
                          <div className="mono">
                            {prestigeReachHoursSelected}h: {prestigeReachMcResult[0]!.successCount}/{prestigeReachMcResult[0]!.totalRuns} runs reached wave ≥ {prestigeReachMcResult[0]!.targetWave} →{" "}
                            <strong>{(prestigeReachMcResult[0]!.probability * 100).toFixed(1)}%</strong> chance. Mean wave: {prestigeReachMcResult[0]!.meanWave.toFixed(1)}.
                          </div>
                        </div>
                      ) : null}
                  </Collapsible>
                );
              })()}
            </>
          ) : (
            <div className="small">Tip: your inputs are auto-saved in this browser.</div>
          )}
        </div>
      </div>

      <div className="eventSimBottom">
        <div className="eventSimCurrentUpgradesWrap">
          <div className="panel">
            <div className="panelHeader">
              <h2 className="panelTitle">Current Upgrades</h2>
            <p className="panelHint">
              Total points: <span className="mono">{totalPoints}</span>
            </p>
          </div>

          <div className="form">
            <div className="prestigeBlock">
              <div className="row">
                <div className="label">
                  <span className="prestigeLabel">
                    Prestige
                    <Tooltip
                      content={{
                        title: "Prestige",
                        sections: [
                          { heading: "What it affects", lines: ["Unlocks upgrades and affects gem upgrade max levels."] },
                          { heading: "Saved", lines: ["This value is saved automatically in this browser."] },
                        ],
                      }}
                    />
                  </span>
                  <span className="mono prestigeValue">{ui.prestige}</span>
                </div>
                <div className="btnRow" style={{ marginTop: 0 }}>
                  <button
                    className="btn btnSecondary"
                    type="button"
                    onClick={() => setUi((s) => ({ ...s, prestige: clampInt(s.prestige - 1, 0, 999) }))}
                    disabled={ui.prestige <= 0}
                  >
                    −
                  </button>
                  <button
                    className="btn"
                    type="button"
                    onClick={() => setUi((s) => ({ ...s, prestige: clampInt(s.prestige + 1, 0, 999) }))}
                    disabled={ui.prestige >= 999}
                  >
                    +
                  </button>
                  <div className="input" style={{ display: "flex", alignItems: "center", justifyContent: "center", fontWeight: 900 }}>
                    <span className="mono">{ui.prestige}</span>
                  </div>
                </div>
              </div>
            </div>

            <div className="btnRow">
              <button
                className={resetUpgradesArmed ? "btn btnDanger" : "btn btnSecondary"}
                type="button"
                onClick={onResetUpgradesClick}
                title={resetUpgradesArmed ? "Click again to confirm (then confirm dialog)." : "Click once to arm, click again to confirm."}
              >
                {resetUpgradesArmed ? "Confirm Reset" : "Reset upgrades"}
              </button>
              <Tooltip
                content={{
                  title: "Reset upgrades",
                  lines: ["Resets Tier 1–4 currency upgrades only. Prestige and gem upgrades are kept."],
                }}
              />
            </div>

            <div className="small">Tier max levels update automatically based on cap upgrades.</div>

            <div className="tierBlock tierBlockGem">
              <div className="tierHead">
                <p className="tierTitle">
                  Gem upgrades
                  <Tooltip
                    content={{
                      title: "Gem upgrades",
                      sections: [
                        { heading: "What they are", lines: ["Permanent upgrades (not bought with event currency)."] },
                        { heading: "Limits", lines: ["Max level depends on prestige."] },
                      ],
                    }}
                  />
                </p>
                <p className="small">Permanent (not event currency)</p>
              </div>
              <div className="small">
                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 6 }}>
                  {ui.upgrades.gemLevels.map((lvl, idx) => {
                    const max = getGemMaxLevel(ui.prestige, idx);
                    const icon = gemUpgradeIconFilename(idx);
                    return (
                      <div key={idx} style={{ border: "1px solid rgba(255,255,255,0.12)", borderRadius: 10, padding: 6 }}>
                        <div style={{ display: "flex", gap: 6, alignItems: "center" }}>
                          <Sprite path={icon ? `sprites/event/${icon}` : null} alt={GEM_UPGRADE_NAMES[idx] ?? `Gem ${idx + 1}`} label={icon ?? ""} />
                          <div className="mono">{GEM_UPGRADE_NAMES[idx] ?? `Gem ${idx + 1}`}</div>
                        </div>
                        <div className="small">
                          lvl <span className="mono">{lvl}</span> / <span className="mono">{max}</span>
                        </div>
                        <div className="btnRow" style={{ marginTop: 4 }}>
                          <button
                            className="btn btnSecondary"
                            disabled={lvl <= 0}
                            onClick={() => {
                              setUi((s) => {
                                const next = copyState(s.upgrades);
                                next.gemLevels[idx] = Math.max(0, next.gemLevels[idx] - 1);
                                return { ...s, upgrades: next };
                              });
                            }}
                          >
                            −
                          </button>
                          <button
                            className="btn"
                            disabled={lvl >= max}
                            onClick={() => {
                              setUi((s) => {
                                const next = copyState(s.upgrades);
                                const max2 = getGemMaxLevel(s.prestige, idx);
                                next.gemLevels[idx] = Math.min(max2, next.gemLevels[idx] + 1);
                                return { ...s, upgrades: next };
                              });
                            }}
                          >
                            +
                          </button>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            </div>

            {[1, 2, 3, 4].map((tier) => {
              const t = tier as 1 | 2 | 3 | 4;
              const levels = ui.upgrades.levels[t];
              const tempState = ui.upgrades;
              return (
                <div className="tierBlock" key={tier}>
                  <div className="tierHead">
                    <p className="tierTitle">Tier {tier}</p>
                    <p className="small">Currency {tier}</p>
                  </div>
                  <div className="small">
                    {levels.map((lvl, idx) => {
                      const unlocked = ui.prestige >= PRESTIGE_UNLOCKED[t][idx];
                      const canAdd = canAllocateUpgrade(t, idx, tempState);
                      const max = getMaxLevelWithCaps(t, idx, tempState);
                      const baseCost = COSTS[t][idx];
                      const nextCost = Math.round(baseCost * 1.25 ** lvl);
                      const icon = upgradeIconFilename(tier, idx);
                      const rowClass = unlocked ? "" : "lockedRow";
                      return (
                        <div key={idx} className={`eventUpgradeRow ${rowClass}`}>
                          <div style={{ display: "flex", gap: 8, alignItems: "center", minWidth: 0 }}>
                            <Sprite path={icon ? `sprites/event/${icon}` : null} alt={UPGRADE_SHORT_NAMES[t][idx].replace(/\n/g, ", ")} label={icon ?? ""} />
                            <div style={{ flex: 1, minWidth: 0 }}>
                              <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
                                <span className="mono" style={{ whiteSpace: "pre-line" }}>{UPGRADE_SHORT_NAMES[t][idx]}</span>
                                {unlocked ? (
                                  <>
                                    <span className="small">
                                      lvl{" "}
                                      <span className="heatNum mono" style={heatStyle(lvl)}>
                                        {lvl}
                                      </span>{" "}
                                      / <span className="mono">{max}</span> • next <span className="mono">{formatInt(nextCost)}</span>
                                    </span>
                                  </>
                                ) : (
                                  <span className="small">
                                    <span className="pillLocked">LOCKED</span> <span className="lockedText">until prestige {PRESTIGE_UNLOCKED[t][idx]}</span>
                                  </span>
                                )}
                              </div>
                            </div>
                          </div>
                          <div style={{ display: "flex", gap: 8, alignItems: "center", flexShrink: 0 }}>
                            {unlocked ? (
                              <>
                                <span className="eventUpgradeLevelBadge mono" style={heatStyle(lvl)} title={`Level ${lvl} / ${max}`}>
                                  {lvl}/{max}
                                </span>
                                <button
                                  className="btn btnSecondary"
                                  disabled={lvl <= 0}
                                  onClick={() => {
                                    setUi((s) => {
                                      const next = copyState(s.upgrades);
                                      next.levels[t][idx] = Math.max(0, next.levels[t][idx] - 5);
                                      return { ...s, upgrades: next };
                                    });
                                  }}
                                  title="-5"
                                >
                                  −5
                                </button>
                                <button
                                  className="btn btnSecondary"
                                  disabled={lvl <= 0}
                                  onClick={() => {
                                    setUi((s) => {
                                      const next = copyState(s.upgrades);
                                      if (next.levels[t][idx] > 0) next.levels[t][idx] -= 1;
                                      return { ...s, upgrades: next };
                                    });
                                  }}
                                  title="-1"
                                >
                                  −
                                </button>
                                <button
                                  className="btn"
                                  disabled={lvl >= max || !canAdd}
                                  onClick={() => {
                                    setUi((s) => {
                                      const next = copyState(s.upgrades);
                                      if (!canAllocateUpgrade(t, idx, next)) return s;
                                      const max2 = getMaxLevelWithCaps(t, idx, next);
                                      if (next.levels[t][idx] < max2) next.levels[t][idx] += 1;
                                      return { ...s, upgrades: next };
                                    });
                                  }}
                                  title={!canAdd ? "Put at least 1 point in the previous upgrade in this tier first" : "+1"}
                                >
                                  +
                                </button>
                                <button
                                  className="btn"
                                  disabled={lvl >= max || !canAdd}
                                  onClick={() => {
                                    setUi((s) => {
                                      const next = copyState(s.upgrades);
                                      if (!canAllocateUpgrade(t, idx, next)) return s;
                                      const max2 = getMaxLevelWithCaps(t, idx, next);
                                      next.levels[t][idx] = Math.min(max2, next.levels[t][idx] + 5);
                                      return { ...s, upgrades: next };
                                    });
                                  }}
                                  title={!canAdd ? "Put at least 1 point in the previous upgrade in this tier first" : "+5"}
                                >
                                  +5
                                </button>
                              </>
                            ) : (
                              <span className="eventUpgradeLevelBadge small">—</span>
                            )}
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>
              );
            })}
            <div className="row2">
              <div className="row">
                <div className="label">
                  <span>
                    MC candidates (N)
                    <Tooltip
                      content={{
                        title: "MC candidates (N)",
                        sections: [
                          { heading: "Meaning", lines: ["How many different upgrade allocations are tried."] },
                          { heading: "Accuracy", lines: ["Higher N improves search quality (better chance to find a strong build)."] },
                        ],
                      }}
                    />
                  </span>
                  <span className="mono">{ui.mcCandidates}</span>
                </div>
                <input
                  className="input"
                  type="number"
                  min={1}
                  step={1}
                  disabled={!ui.devOnlyMcTuning}
                  value={ui.mcCandidates}
                  onChange={(e) => setUi((s) => ({ ...s, mcCandidates: clampInt(Number(e.target.value), 1, 20000) }))}
                />
              </div>
              <div className="row">
                <div className="label">
                  <span>
                    Runs per combo
                    <Tooltip
                      content={{
                        title: "Runs per combo",
                        sections: [
                          { heading: "Meaning", lines: ["How many simulation runs are averaged per candidate allocation."] },
                          { heading: "Accuracy", lines: ["Higher runs reduces randomness/noise (more stable results)."] },
                        ],
                      }}
                    />
                  </span>
                  <span className="mono">{ui.mcRunsPerCombo}</span>
                </div>
                <input
                  className="input"
                  type="number"
                  min={1}
                  max={2000}
                  step={1}
                  disabled={!ui.devOnlyMcTuning}
                  value={ui.mcRunsPerCombo}
                  onChange={(e) => setUi((s) => ({ ...s, mcRunsPerCombo: clampInt(Number(e.target.value), 1, 2000) }))}
                />
              </div>
              <label className="toggle" style={{ display: "flex", alignItems: "center", gap: 8 }}>
                <input
                  type="checkbox"
                  checked={ui.useRewardMilestones}
                  onChange={(e) => setUi((s) => ({ ...s, useRewardMilestones: e.target.checked }))}
                />
                <span>
                  Tie-break by reward milestones (currency/h)
                  <Tooltip
                    content={{
                      title: "Tie-break by reward milestones",
                      sections: [
                        {
                          heading: "What it does",
                          lines: [
                            "Band = highest reward wave you reach (e.g. 40 = Seasonal Miner, 42 = 5 Blue Cows).",
                            "Among builds that reach the same reward wave, the one with more currency per hour wins.",
                          ],
                        },
                        {
                          heading: "Off",
                          lines: ["Uncheck to use a fixed wave step instead, or no tie-break (wave + time only)."],
                        },
                      ],
                    }}
                  />
                </span>
              </label>
              <div className="row">
                <div className="label">
                  <span>
                    Wave band step (if reward milestones off)
                    <Tooltip
                      content={{
                        title: "Wave band step",
                        sections: [
                          {
                            heading: "When to use",
                            lines: [
                              "Only used when 'Tie-break by reward milestones' is off.",
                              "E.g. step 5: waves 40–44 count as same band; tie-break by currency/h.",
                            ],
                          },
                          { heading: "Off", lines: ["0 = no tie-break. Optimizer picks by highest wave and shortest time only."] },
                        ],
                      }}
                    />
                  </span>
                  <span className="mono">{ui.waveBandStep}</span>
                </div>
                <input
                  className="input"
                  type="number"
                  min={0}
                  max={20}
                  step={1}
                  disabled={ui.useRewardMilestones}
                  value={ui.waveBandStep}
                  onChange={(e) => setUi((s) => ({ ...s, waveBandStep: clampInt(Number(e.target.value), 0, 20) }))}
                />
              </div>
            </div>

            <label className="toggle">
              <input type="checkbox" checked={ui.devOnlyMcTuning} onChange={(e) => setUi((s) => ({ ...s, devOnlyMcTuning: e.target.checked }))} />
              For developers only (unlock MC tuning)
              <Tooltip
                content={{
                  title: "For developers only",
                  lines: ["These settings can make the optimizer extremely slow.", "Leave them locked for normal usage."],
                }}
              />
            </label>

            {SHOW_COMPARISON ? (
              <div style={{ marginTop: 12 }}>
                <button
                  type="button"
                  className="btn btnSecondary"
                  onClick={() => setComparisonWindowOpen(true)}
                  disabled={running}
                >
                  Developer: Compare algorithms
                </button>
                <Tooltip
                  content={{
                    title: "Developer: Compare algorithms",
                    lines: [
                      "Opens a sub-window to run and compare multiple MC algorithms (e.g. Wide 2×N, Stable 2×runs, Multi-start).",
                      "For debugging and tuning; results and upgrade differences are shown in the sub-window.",
                    ],
                  }}
                />
              </div>
            ) : null}
          </div>
        </div>
        </div>
      </div>

      {SHOW_COMPARISON && comparisonWindowOpen
        ? createPortal(
            <div
              className="modalOverlay"
              style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.5)", display: "flex", alignItems: "center", justifyContent: "center", zIndex: 10000 }}
              onMouseDown={() => setComparisonWindowOpen(false)}
              role="dialog"
              aria-modal="true"
              aria-labelledby="comparison-modal-title"
            >
              <div
                className="panel"
                style={{
                  maxWidth: 960,
                  maxHeight: "90vh",
                  overflow: "auto",
                  margin: 16,
                  background: "#e3f2fd",
                  boxShadow: "0 8px 32px rgba(0,0,0,0.25)",
                  borderRadius: 8,
                }}
                onMouseDown={(e) => e.stopPropagation()}
              >
                <div className="panelHeader" style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: 8 }}>
                  <div>
                    <h2 id="comparison-modal-title" className="panelTitle">Developer: Compare algorithms</h2>
                    <p className="panelHint">Run multiple MC algorithms with same base N/runs; compare stats and upgrade suggestions. Algorithms may use 2×N or 2×runs.</p>
                  </div>
                  <button type="button" className="btn btnSecondary" onClick={() => setComparisonWindowOpen(false)}>
                    Close
                  </button>
                </div>

                <div style={{ marginTop: 16 }}>
                  <div className="label" style={{ marginBottom: 8 }}>Algorithms to run (same budget / base params)</div>
                  <div style={{ display: "flex", flexWrap: "wrap", gap: 12 }}>
                    {COMPARISON_METHOD_IDS.map((id) => {
                      const methods = ui.comparisonMethods ?? [];
                      return (
                        <label key={id} className="toggle" style={{ fontWeight: "normal" }}>
                          <input
                            type="checkbox"
                            checked={methods.includes(id)}
                            disabled={running}
                            onChange={(e) => {
                              if (e.target.checked) setUi((s) => ({ ...s, comparisonMethods: [...(s.comparisonMethods ?? []), id] }));
                              else setUi((s) => ({ ...s, comparisonMethods: (s.comparisonMethods ?? []).filter((m) => m !== id) }));
                            }}
                          />
                          <span>{getMethodLabel(id)}</span>
                        </label>
                      );
                    })}
                  </div>
                  <div style={{ display: "flex", flexWrap: "wrap", gap: 16, marginTop: 12, alignItems: "center" }}>
                    <div className="row">
                      <div className="label">
                        <span>Replicates per algorithm</span>
                        <span className="mono">{ui.comparisonReplicates ?? 3}</span>
                      </div>
                      <input
                        className="input"
                        type="number"
                        min={1}
                        max={10}
                        disabled={running}
                        value={ui.comparisonReplicates ?? 3}
                        onChange={(e) => setUi((s) => ({ ...s, comparisonReplicates: clampInt(Number(e.target.value), 1, 10) }))}
                      />
                    </div>
                    <div className="row">
                      <div className="label">
                        <span>Validation sims (0 = off)</span>
                        <span className="mono">{ui.comparisonValidationSims ?? 0}</span>
                      </div>
                      <input
                        className="input"
                        type="number"
                        min={0}
                        max={2000}
                        disabled={running}
                        value={ui.comparisonValidationSims ?? 0}
                        onChange={(e) => setUi((s) => ({ ...s, comparisonValidationSims: clampInt(Number(e.target.value), 0, 2000) }))}
                      />
                    </div>
                <span className="small" style={{ maxWidth: 320 }}>
                  Replicates = how often each algorithm is run (reproducibility). Use 5–10 if the winner varies between runs. Validation = extra sims on best candidate (predictability).
                </span>
              </div>
              <div className="btnRow" style={{ marginTop: 12 }}>
                <button type="button" className="btn" onClick={onRunComparison} disabled={running || (ui.comparisonMethods ?? []).length === 0}>
                  Run comparison
                </button>
                {running ? (
                  <button type="button" className="btn btnSecondary" onClick={onCancel}>
                    Cancel
                  </button>
                ) : null}
              </div>
              {running && progress ? (
                <div className="kv" style={{ marginTop: 12 }}>
                  <kbd>Progress</kbd>
                  <div className="mono">{progress.cur}/{progress.total} ({Math.floor((progress.cur / progress.total) * 100)}%)</div>
                  <kbd>Best wave</kbd>
                  <div className="mono">{progress.bestWave.toFixed(1)}</div>
                </div>
              ) : null}
            </div>

            {comparisonResult ? (
              <>
                <div className="sectionTitle" style={{ marginTop: 24 }}>Reproducibility &amp; winner (sustainable best = highest mean across replicates)</div>
                <p className="small" style={{ marginTop: 4, marginBottom: 8 }}>
                  Winner can vary between runs when mean differences are small. Use more replicates (e.g. 5–10) for a stable ranking.
                </p>
                {(() => {
                  const sorted = [...comparisonResult.methodResults].sort((a, b) => b.summary.meanBest - a.summary.meanBest);
                  const first = sorted[0];
                  const second = sorted[1];
                  const diff = first && second ? first.summary.meanBest - second.summary.meanBest : 0;
                  const pooledStd = first && second
                    ? Math.sqrt((first.summary.stdBest ** 2 + second.summary.stdBest ** 2) / 2)
                    : 0;
                  const withinNoise = pooledStd > 0 && diff < 1.5 * pooledStd;
                  return withinNoise ? (
                    <p className="small" style={{ marginBottom: 8, padding: "8px 10px", background: "rgba(255,180,0,0.15)", borderRadius: 6 }}>
                      <strong>Top 2 within noise</strong> (diff = {diff.toFixed(2)}, pooled std ≈ {pooledStd.toFixed(2)}). Run more replicates for a stable ranking, or pick by <strong>lowest Std(val)</strong> for predictability (build generalizes best).
                    </p>
                  ) : null;
                })()}
                <div style={{ overflowX: "auto" }}>
                  <table style={{ width: "100%", minWidth: 640, borderCollapse: "collapse", marginTop: 8 }}>
                    <thead>
                      <tr>
                        <th style={{ textAlign: "left", padding: "6px 8px", borderBottom: "1px solid var(--border)" }}>Method</th>
                        <th style={{ textAlign: "right", padding: "6px 8px", borderBottom: "1px solid var(--border)" }}>Mean(best)</th>
                        <th style={{ textAlign: "right", padding: "6px 8px", borderBottom: "1px solid var(--border)" }}>Std(best)</th>
                        <th style={{ textAlign: "right", padding: "6px 8px", borderBottom: "1px solid var(--border)" }}>Min–Max</th>
                        <th style={{ textAlign: "right", padding: "6px 8px", borderBottom: "1px solid var(--border)" }}>Median</th>
                        {comparisonResult.methodResults.some((m) => m.replicates[0]?.bestWaveBand != null) ? (
                          <>
                            <th style={{ textAlign: "right", padding: "6px 8px", borderBottom: "1px solid var(--border)" }}>Reward band</th>
                            <th style={{ textAlign: "right", padding: "6px 8px", borderBottom: "1px solid var(--border)" }}>Currency/h</th>
                          </>
                        ) : null}
                        {comparisonResult.methodResults.some((m) => m.summary.meanVal != null) ? (
                          <>
                            <th style={{ textAlign: "right", padding: "6px 8px", borderBottom: "1px solid var(--border)" }}>Mean(val)</th>
                            <th style={{ textAlign: "right", padding: "6px 8px", borderBottom: "1px solid var(--border)" }}>Std(val)</th>
                          </>
                        ) : null}
                        <th style={{ padding: "6px 8px", borderBottom: "1px solid var(--border)" }} />
                      </tr>
                    </thead>
                    <tbody>
                      {comparisonResult.methodResults.map((row) => {
                        const rep0 = row.replicates[0];
                        return (
                          <tr key={row.methodId}>
                            <td style={{ padding: "6px 8px", borderBottom: "1px solid var(--border)" }}>
                              {row.label}
                              {row.methodId === comparisonResult.winnerId ? <span className="badge" style={{ marginLeft: 6 }}>sustainable best</span> : null}
                            </td>
                            <td style={{ textAlign: "right", padding: "6px 8px", borderBottom: "1px solid var(--border)" }} className="mono">{row.summary.meanBest.toFixed(2)}</td>
                            <td style={{ textAlign: "right", padding: "6px 8px", borderBottom: "1px solid var(--border)" }} className="mono">{row.summary.stdBest.toFixed(2)}</td>
                            <td style={{ textAlign: "right", padding: "6px 8px", borderBottom: "1px solid var(--border)" }} className="mono">{row.summary.minBest.toFixed(1)}–{row.summary.maxBest.toFixed(1)}</td>
                            <td style={{ textAlign: "right", padding: "6px 8px", borderBottom: "1px solid var(--border)" }} className="mono">{row.summary.medianBest.toFixed(1)}</td>
                            {comparisonResult.methodResults.some((m) => m.replicates[0]?.bestWaveBand != null) ? (
                              <>
                                <td style={{ textAlign: "right", padding: "6px 8px", borderBottom: "1px solid var(--border)" }} className="mono">
                                  {rep0?.bestWaveBand != null ? rep0.bestWaveBand : "—"}
                                </td>
                                <td style={{ textAlign: "right", padding: "6px 8px", borderBottom: "1px solid var(--border)" }} className="mono">
                                  {rep0?.bestCurrencyPerHour != null
                                    ? Number(rep0.bestCurrencyPerHour).toLocaleString(undefined, { maximumFractionDigits: 0 })
                                    : "—"}
                                </td>
                              </>
                            ) : null}
                            {comparisonResult.methodResults.some((m) => m.summary.meanVal != null) ? (
                              <>
                                <td style={{ textAlign: "right", padding: "6px 8px", borderBottom: "1px solid var(--border)" }} className="mono">
                                  {row.summary.meanVal != null ? row.summary.meanVal.toFixed(2) : "—"}
                                </td>
                                <td style={{ textAlign: "right", padding: "6px 8px", borderBottom: "1px solid var(--border)" }} className="mono">
                                  {row.summary.stdVal != null ? row.summary.stdVal.toFixed(2) : "—"}
                                </td>
                              </>
                            ) : null}
                            <td style={{ padding: "6px 8px", borderBottom: "1px solid var(--border)" }}>
                              {rep0 ? (
                                <button type="button" className="btn btnSecondary" onClick={() => applyComparisonResult(rep0.result)}>Apply</button>
                              ) : null}
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>

                <div className="sectionTitle" style={{ marginTop: 24 }}>Plot: best wave per replicate (reproducibility)</div>
                <p className="small" style={{ marginTop: 4 }}>Each point = one replicate. Lower std = more reproducible. Sustainable best = highest mean.</p>
                {(() => {
                  const W = 700;
                  const H = 260;
                  const padL = 50;
                  const padR = 20;
                  const padT = 20;
                  const padB = 36;
                  const plotW = W - padL - padR;
                  const plotH = H - padT - padB;
                  const methods = comparisonResult.methodResults;
                  const allWaves = methods.flatMap((m) => m.replicates.map((r) => r.bestWave));
                  const yMin = Math.min(...allWaves, 0);
                  const yMax = Math.max(...allWaves, 1);
                  const yRange = yMax - yMin || 1;
                  const yScale = (v: number) => padT + plotH - ((v - yMin) / yRange) * plotH;
                  const jitter = 12;
                  return (
                    <svg width={W} height={H} style={{ display: "block", marginTop: 8 }} aria-label="Best wave per replicate by algorithm">
                      <line x1={padL} y1={padT} x2={padL} y2={padT + plotH} stroke="var(--border, #ccc)" strokeWidth={1} />
                      <line x1={padL} y1={padT + plotH} x2={padL + plotW} y2={padT + plotH} stroke="var(--border, #ccc)" strokeWidth={1} />
                      {[yMin, yMin + yRange * 0.25, yMin + yRange * 0.5, yMin + yRange * 0.75, yMax].map((v, i) => (
                        <g key={i}>
                          <line x1={padL - 4} y1={yScale(v)} x2={padL} y2={yScale(v)} stroke="var(--border, #ccc)" strokeWidth={1} />
                          <text x={padL - 8} y={yScale(v) + 4} textAnchor="end" fontSize={10} fill="var(--text, #333)">{v.toFixed(1)}</text>
                        </g>
                      ))}
                      {methods.map((method, mi) => {
                        const bandW = plotW / methods.length;
                        const cx = padL + bandW * (mi + 0.5);
                        const meanY = yScale(method.summary.meanBest);
                        return (
                          <g key={method.methodId}>
                            <line x1={cx - bandW / 2 + jitter} y1={meanY} x2={cx + bandW / 2 - jitter} y2={meanY} stroke="var(--good, #2e7d32)" strokeWidth={2} strokeDasharray="4,2" />
                            {method.replicates.map((rep, ri) => {
                              const j = (ri / Math.max(1, method.replicates.length)) * 2 * jitter - jitter;
                              return (
                                <circle key={ri} cx={cx + j} cy={yScale(rep.bestWave)} r={4} fill={method.methodId === comparisonResult.winnerId ? "var(--good, #2e7d32)" : "var(--tier2, #64748b)"} />
                              );
                            })}
                            <text x={cx} y={padT + plotH + 20} textAnchor="middle" fontSize={10} fill="var(--text, #333)" style={{ maxWidth: bandW - 8 }}>{method.label}</text>
                          </g>
                        );
                      })}
                    </svg>
                  );
                })()}

                <div className="sectionTitle" style={{ marginTop: 24 }}>Upgrade comparison (representative = first replicate per algorithm)</div>
                <p className="small" style={{ marginTop: 4 }}>Each column is one algorithm; differing values are highlighted.</p>
                <div style={{ overflowX: "auto", marginTop: 8 }}>
                  <table style={{ width: "100%", minWidth: 400, borderCollapse: "collapse", fontSize: "0.9em" }}>
                    <thead>
                      <tr>
                        <th style={{ textAlign: "left", padding: "4px 8px", borderBottom: "1px solid var(--border)" }}>Upgrade</th>
                        {comparisonResult.methodResults.map((row) => (
                          <th key={row.methodId} style={{ textAlign: "right", padding: "4px 8px", borderBottom: "1px solid var(--border)" }}>{row.label}</th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {([1, 2, 3, 4] as const).flatMap((tier) => {
                        const arr = comparisonResult.methodResults[0]?.replicates[0]?.result.upgrades.levels[tier] ?? [];
                        return arr.map((_, idx) => {
                          const levels = comparisonResult.methodResults.map((m) => m.replicates[0]?.result.upgrades.levels[tier]?.[idx] ?? 0);
                          const allSame = levels.length <= 1 || levels.every((l) => l === levels[0]);
                          const name = UPGRADE_SHORT_NAMES[tier]?.[idx] ?? `[${idx}]`;
                          return (
                            <tr key={`${tier}-${idx}`}>
                              <td style={{ padding: "4px 8px", borderBottom: "1px solid var(--border)", whiteSpace: "pre-line" }}>T{tier} {name}</td>
                              {comparisonResult.methodResults.map((row) => (
                                <td
                                  key={row.methodId}
                                  style={{
                                    textAlign: "right",
                                    padding: "4px 8px",
                                    borderBottom: "1px solid var(--border)",
                                    backgroundColor: !allSame ? "rgba(255,200,0,0.12)" : undefined,
                                  }}
                                  className="mono"
                                >
                                  {row.replicates[0]?.result.upgrades.levels[tier]?.[idx] ?? 0}
                                </td>
                              ))}
                            </tr>
                          );
                        });
                      })}
                    </tbody>
                  </table>
                </div>
              </>
            ) : null}
              </div>
            </div>,
            document.body
          )
        : null}

      {waveHistogramOpen ? (
        <div
          style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.45)", display: "flex", alignItems: "center", justifyContent: "center", zIndex: 10000 }}
          onClick={() => setWaveHistogramOpen(false)}
          role="dialog"
          aria-modal="true"
          aria-label="Wave distribution histogram"
        >
          <div
            className="panel"
            style={{ maxWidth: 520, margin: 16, boxShadow: "0 8px 32px rgba(0,0,0,0.25)", borderRadius: 8 }}
            onClick={(e) => e.stopPropagation()}
          >
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12 }}>
              <div className="mono" style={{ fontWeight: 900, fontSize: 14 }}>Wave distribution (suggested build)</div>
              <button type="button" className="btn btnSecondary" onClick={() => setWaveHistogramOpen(false)}>
                Close
              </button>
            </div>
            <p className="small" style={{ marginBottom: 10, color: "var(--muted)" }}>
              Distribution of max wave reached over 500 runs with the current suggested skill allocation.
            </p>
            {waveHistogramLoading ? (
              <div style={{ padding: "24px 0", textAlign: "center", color: "var(--muted)" }}>Calculating…</div>
            ) : waveHistogramSamples?.length ? (
              (() => {
                const xs = waveHistogramSamples.map((x) => Number(x)).filter((x) => Number.isFinite(x));
                if (!xs.length) return <div className="small" style={{ color: "var(--muted)" }}>No data.</div>;
                const min = Math.floor(Math.min(...xs));
                const max = Math.ceil(Math.max(...xs));
                const bins = Array.from({ length: max - min + 1 }, (_, i) => min + i);
                const counts = new Array(bins.length).fill(0);
                for (const v of xs) {
                  const idx = Math.max(0, Math.min(bins.length - 1, Math.floor(v) - min));
                  counts[idx] += 1;
                }
                const maxC = Math.max(1, ...counts);
                const W = 480;
                const H = 200;
                const pad = 10;
                const axisH = 28;
                const plotH = H - pad * 2 - axisH;
                const barW = (W - pad * 2) / bins.length;
                const totalSamples = xs.length;
                return (
                  <div style={{ marginTop: 8 }}>
                    <svg width="100%" viewBox={`0 0 ${W} ${H}`} style={{ display: "block" }} aria-label="Wave distribution histogram">
                      {bins.map((bin, i) => {
                        const c = counts[i] ?? 0;
                        const h = maxC > 0 ? (plotH * c) / maxC : 0;
                        const x = pad + i * barW;
                        const y = H - pad - axisH - h;
                        const pct = totalSamples > 0 ? (100 * c) / totalSamples : 0;
                        return (
                          <g key={bin}>
                            <rect
                              x={x}
                              y={y}
                              width={Math.max(1, barW - 1)}
                              height={h}
                              fill="rgba(92,107,192,0.55)"
                              stroke="rgba(15,23,42,0.2)"
                              strokeWidth={0.5}
                            >
                              <title>Wave {bin}: {c} ({pct.toFixed(1)}%)</title>
                            </rect>
                            {c > 0 && h >= 14 ? (
                              <text
                                x={x + barW / 2}
                                y={y + h / 2}
                                textAnchor="middle"
                                dominantBaseline="middle"
                                fontSize="9"
                                fontWeight="700"
                                fill={h > plotH * 0.4 ? "rgba(255,255,255,0.95)" : "rgba(15,23,42,0.9)"}
                              >
                                {c}
                              </text>
                            ) : null}
                          </g>
                        );
                      })}
                      <line x1={pad} x2={W - pad} y1={H - pad - axisH} y2={H - pad - axisH} stroke="rgba(15,23,42,0.2)" strokeWidth={1} />
                      {(() => {
                        const tickStep = Math.max(1, Math.ceil(bins.length / 10));
                        const tickIndices = [0, ...Array.from({ length: Math.ceil((bins.length - 1) / tickStep) }, (_, j) => Math.min((j + 1) * tickStep, bins.length - 1))];
                        return tickIndices.map((i) => {
                          const bin = bins[i];
                          const x = pad + (i + 0.5) * barW;
                          return (
                            <g key={bin}>
                              <line x1={x} x2={x} y1={H - pad - axisH} y2={H - pad - axisH + 4} stroke="rgba(15,23,42,0.25)" strokeWidth={1} />
                              <text x={x} y={H - pad - 6} textAnchor="middle" fontSize="10" fontWeight="700" fill="rgba(71,85,105,0.9)">
                                {bin}
                              </text>
                            </g>
                          );
                        });
                      })()}
                    </svg>
                    <div className="small" style={{ marginTop: 6, color: "var(--muted)", textAlign: "center" }}>
                      Max wave reached (N=500)
                    </div>
                    {waveHistogramHpPerWave && waveHistogramHpPerWave.length > 0 ? (
                      (() => {
                        const rows = waveHistogramHpPerWave;
                        const W2 = 480;
                        const H2 = 200;
                        const pad2 = 10;
                        const axisH2 = 28;
                        const plotH2 = H2 - pad2 * 2 - axisH2;
                        const xMin = Math.min(...rows.map((r) => r.wave));
                        const xMax = Math.max(...rows.map((r) => r.wave));
                        const yMax = Math.min(100, Math.ceil(Math.max(...rows.map((r) => r.meanLostPct + r.stdLostPct)) * 1.1) || 100);
                        const scaleX = (w: number) => pad2 + ((w - xMin) / (xMax - xMin || 1)) * (W2 - pad2 * 2);
                        const scaleY = (pct: number) => H2 - pad2 - axisH2 - (pct / yMax) * plotH2;
                        const meanPath = "M " + rows.map((r) => `${scaleX(r.wave)},${scaleY(r.meanLostPct)}`).join(" L ");
                        const upperPoints = rows.map((r) => `${scaleX(r.wave)},${scaleY(Math.min(100, r.meanLostPct + r.stdLostPct))}`);
                        const lowerPoints = rows.map((r) => `${scaleX(r.wave)},${scaleY(Math.max(0, r.meanLostPct - r.stdLostPct))}`);
                        const bandPath = "M " + upperPoints.join(" L ") + " L " + lowerPoints.slice().reverse().join(" L ") + " Z";
                        return (
                          <div style={{ marginTop: 20, paddingTop: 16, borderTop: "1px solid rgba(15,23,42,0.12)" }}>
                            <div className="small" style={{ marginBottom: 8, color: "var(--muted)", textAlign: "center" }}>
                              HP lost % at end of wave (mean ± SD, N=500)
                            </div>
                            <svg width="100%" viewBox={`0 0 ${W2} ${H2}`} style={{ display: "block" }} aria-label="HP lost percent by wave">
                              <path d={`M ${bandPath}`} fill="rgba(220, 80, 70, 0.2)" stroke="none" />
                              <path d={meanPath} fill="none" stroke="rgba(200, 60, 50, 0.9)" strokeWidth={2} strokeLinejoin="round" />
                              <line x1={pad2} x2={W2 - pad2} y1={H2 - pad2 - axisH2} y2={H2 - pad2 - axisH2} stroke="rgba(15,23,42,0.2)" strokeWidth={1} />
                              <line x1={pad2} x2={pad2} y1={pad2} y2={H2 - pad2 - axisH2} stroke="rgba(15,23,42,0.2)" strokeWidth={1} />
                              {[0, 0.25, 0.5, 0.75, 1].map((t) => {
                                const y = H2 - pad2 - axisH2 - t * plotH2;
                                const pct = (t * yMax).toFixed(0);
                                return (
                                  <g key={t}>
                                    <line x1={pad2} x2={pad2 - 4} y1={y} y2={y} stroke="rgba(15,23,42,0.25)" strokeWidth={1} />
                                    <text x={pad2 - 6} y={y + 4} textAnchor="end" fontSize="9" fill="rgba(71,85,105,0.9)">{pct}%</text>
                                  </g>
                                );
                              })}
                              {[0, 0.25, 0.5, 0.75, 1].map((t) => {
                                const x = pad2 + t * (W2 - pad2 * 2);
                                const w = Math.round(xMin + t * (xMax - xMin));
                                return (
                                  <g key={t}>
                                    <line x1={x} x2={x} y1={H2 - pad2 - axisH2} y2={H2 - pad2 - axisH2 + 4} stroke="rgba(15,23,42,0.25)" strokeWidth={1} />
                                    <text x={x} y={H2 - pad2 - 6} textAnchor="middle" fontSize="10" fontWeight="700" fill="rgba(71,85,105,0.9)">{w}</text>
                                  </g>
                                );
                              })}
                            </svg>
                          </div>
                        );
                      })()
                    ) : null}
                  </div>
                );
              })()
            ) : (
              <div className="small" style={{ color: "var(--muted)" }}>No data.</div>
            )}
          </div>
        </div>
      ) : null}
    </div>
  );
}

