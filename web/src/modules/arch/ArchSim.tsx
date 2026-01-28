import { useEffect, useMemo, useRef, useState, type CSSProperties, type ReactNode } from "react";
import { Collapsible } from "../../components/Collapsible";
import { Tooltip } from "../../components/Tooltip";
import { assetUrl } from "../../lib/assets";
import { formatInt } from "../../lib/format";
import { mulberry32 } from "../../lib/rng";
import { loadJson, saveJson } from "../../lib/storage";
import { BLOCK_COLORS, FRAGMENT_UPGRADES, GEM_COSTS, GEM_UPGRADE_BONUSES } from "../../lib/archaeology/constants";
import { BLOCK_TYPES, getBlockData } from "../../lib/archaeology/blockStats";
import { computeRunSummary, getCalculationStage, getSkillPointCap, getTotalStats } from "../../lib/archaeology/sim";
import { getUpgradeCost } from "../../lib/archaeology/upgradeCosts";
import type { ArchBuild, ArchGemUpgradeKey, BlockTier, BlockType, CardLevel, Skill } from "../../lib/archaeology/types";

const STORAGE_KEY = "obeliskfarm:web:archaeology_save.json:v1";
const MC_LOG_KEY = "obeliskfarm:web:archaeology_mc_results_log.json:v1";
const MC_SETTINGS_KEY = "obeliskfarm:web:archaeology_mc_settings.json:v1";

function clampInt(n: number, min: number, max: number): number {
  if (!Number.isFinite(n)) return min;
  return Math.max(min, Math.min(max, Math.trunc(n)));
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
  };
  mc?: {
    // Present only for real MC runs
    archLevel: number;
    screeningSims: number;
    refinementSims: number;
    targetFrag?: BlockType;
    objective: "stage" | "XP" | "frag";
    objectiveSamples: number[]; // usually 1000 samples
    tieBreak?: {
      mode: "stage" | "XP" | "frag";
      epsilon: number;
      primaryMetric: string;
      tiedAtPrimary: number;
      winnerReason: string;
      top3: Array<{
        label: string;
        primary: number;
        secondary?: number;
        tertiary?: number;
        dist: { strength: number; agility: number; perception: number; intellect: number; luck: number };
      }>;
    };
  };
};

type TieBreakReport = NonNullable<McLogEntry["mc"]>["tieBreak"];

type McSettings = {
  targetFrag: BlockType;
};

function defaultMcSettings(): McSettings {
  return { targetFrag: "common" };
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
    for (const tier of [1, 2, 3] as const) {
      if (getBlockData(tier, bt)) blockCards[`${bt},${tier}`] = 0;
    }
  }
  return {
    goalStage: 1,
    unlockedStage: 1,
    archLevel: 20,
    skillPoints: { strength: 0, agility: 0, perception: 0, intellect: 0, luck: 0 },
    gemUpgrades: { stamina: 0, xp: 0, fragment: 0, arch_xp: 0 },
    fragmentUpgradeLevels: {},
    blockCards,
    miscCardLevel: 0,
    enrageEnabled: true,
    flurryEnabled: true,
    quakeEnabled: true,
    avadaKedaEnabled: false,
    blockBonkerEnabled: false,
  };
}

function toggleCardLevel(cur: CardLevel, next: CardLevel): CardLevel {
  return cur === next ? 0 : next;
}

function formatPct(x: number, digits = 2): string {
  return `${(x * 100).toFixed(digits)}%`;
}

function normalizeSkillsToTotal(sp: Record<Skill, number>, total: number): Record<Skill, number> {
  const order: Skill[] = ["luck", "intellect", "perception", "agility", "strength"];
  const out: Record<Skill, number> = { ...sp };
  let sum = (Object.values(out) as number[]).reduce((a, b) => a + clampInt(Number(b ?? 0), 0, 999), 0);
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
  const [build, setBuild] = useState<ArchBuild>(() => {
    const saved = loadJson<Partial<ArchBuild>>(STORAGE_KEY);
    const base = defaultBuild();
    if (!saved) return base;
    return {
      ...base,
      ...saved,
      // deep-ish merges:
      skillPoints: { ...base.skillPoints, ...(saved.skillPoints ?? {}) },
      gemUpgrades: { ...base.gemUpgrades, ...(saved.gemUpgrades ?? {}) },
      fragmentUpgradeLevels: { ...(saved.fragmentUpgradeLevels ?? {}) },
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
  const [mcSettings, setMcSettings] = useState<McSettings>(() => {
    const raw = (loadJson<any>(MC_SETTINGS_KEY) ?? null) as any;
    const base = defaultMcSettings();
    if (!raw) return base;
    return {
      targetFrag: (raw.targetFrag as BlockType) ?? base.targetFrag,
    };
  });
  function confirmDanger(message: string): boolean {
    try {
      return window.confirm(message);
    } catch {
      return false;
    }
  }

  function heatAlphaFromLevel(level: number): number {
    const lvl = Math.max(0, Math.trunc(level));
    if (lvl <= 0) return 0;
    const maxRef = 50;
    const alpha = (Math.log1p(lvl) / Math.log1p(maxRef)) * 0.28;
    return Math.max(0.06, Math.min(0.28, alpha));
  }

  function heatStyle(level: number): CSSProperties {
    const a = heatAlphaFromLevel(level);
    if (a <= 0) return {};
    const maxRef = 50;
    const t = Math.max(0, Math.min(1, Math.log1p(Math.max(0, level)) / Math.log1p(maxRef)));
    const hue = t < 0.5 ? 120 + (60 - 120) * (t / 0.5) : 60 + (30 - 60) * ((t - 0.5) / 0.5);
    const bg = `hsla(${hue.toFixed(1)}, 85%, 70%, ${a.toFixed(3)})`;
    const border = `hsla(${hue.toFixed(1)}, 85%, 38%, 0.35)`;
    return { backgroundColor: bg, borderColor: border };
  }

  const [mcRunning, setMcRunning] = useState(false);
  const [mcProgress, setMcProgress] = useState<string | null>(null);
  const cancelRef = useRef<{ cancelled: boolean; pool: WorkerPool | null }>({ cancelled: false, pool: null });

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

  const totalSkillPoints = useMemo(() => Object.values(build.skillPoints).reduce((a, b) => a + b, 0), [build.skillPoints]);

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
    const groups: Record<string, Array<[string, any]>> = {};
    for (const [k, info] of sortedFragmentUpgrades) {
      const ct = String((info as any)?.cost_type ?? "misc");
      if (!groups[ct]) groups[ct] = [];
      groups[ct]!.push([k, info]);
    }
    return groups;
  }, [sortedFragmentUpgrades]);

  // Deterministic recommendation panels removed (MC-only UI).

  function setSkill(skill: Skill, delta: number) {
    setBuild((s) => {
      const cap = getSkillPointCap(s, skill);
      const cur = clampInt(Number(s.skillPoints[skill] ?? 0), 0, cap);
      const otherSum = (Object.entries(s.skillPoints) as Array<[Skill, number]>)
        .filter(([k]) => k !== skill)
        .reduce((acc, [, v]) => acc + clampInt(Number(v ?? 0), 0, 999), 0);
      const totalCap = clampInt(Number(s.archLevel ?? 0), 0, 999);
      const maxForSkillByTotal = Math.max(0, totalCap - otherSum);
      const maxAllowed = Math.min(cap, maxForSkillByTotal);
      const next = clampInt(cur + delta, 0, maxAllowed);
      return { ...s, skillPoints: { ...s.skillPoints, [skill]: next } };
    });
  }

  function setGemUpgrade(key: ArchGemUpgradeKey, delta: number) {
    setBuild((s) => {
      const cur = s.gemUpgrades[key] ?? 0;
      const max = GEM_UPGRADE_BONUSES[key].max_level ?? 0;
      const next = clampInt(cur + delta, 0, max);
      return { ...s, gemUpgrades: { ...s.gemUpgrades, [key]: next } };
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
      return { ...s, fragmentUpgradeLevels: copy };
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
      const normalized = normalizeSkillsToTotal(s.skillPoints, lvl);
      return { ...s, archLevel: lvl, skillPoints: normalized };
    });
  }

  type WorkerMsg =
    | { type: "stageSummary"; payload: any }
    | { type: "fragmentSummary"; payload: any }
    | { type: "stageLite"; payload: any };

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
    setMcProgress("Cancelled.");
  }

  function getPolychromeBonus(): number {
    const lvl = clampInt(Number(build.fragmentUpgradeLevels["polychrome_bonus"] ?? 0), 0, 1);
    return 0.15 * lvl;
  }

  const skills = useMemo(() => ["strength", "agility", "perception", "intellect", "luck"] as const, []);

  function sampleDirichletInteger(args: {
    numPoints: number;
    caps: Record<Skill, number>;
    requireStr: boolean;
    rng: () => number;
  }): number[] {
    const { numPoints, caps, requireStr, rng } = args;
    // Exponential trick (Dirichlet with alpha=1): sample w_i ~ Exp(1), normalize.
    const w = skills.map(() => -Math.log(Math.max(1e-12, rng())));
    const sumW = w.reduce((a, b) => a + b, 0) || 1;
    const raw = w.map((x) => (x / sumW) * numPoints);
    const base = raw.map((x, i) => Math.min(caps[skills[i]], Math.max(0, Math.trunc(x))));
    let used = base.reduce((a, b) => a + b, 0);
    let remaining = numPoints - used;

    const frac = raw.map((x, i) => ({ i, f: x - Math.trunc(x) })).sort((a, b) => b.f - a.f);
    let guard = 0;
    while (remaining > 0 && guard++ < 1000) {
      let placed = false;
      for (const it of frac) {
        const si = skills[it.i];
        if (base[it.i] < caps[si]) {
          base[it.i] += 1;
          remaining -= 1;
          placed = true;
          if (remaining <= 0) break;
        }
      }
      if (!placed) break;
    }

    if (requireStr) {
      const strIdx = skills.indexOf("strength");
      if (base[strIdx] <= 0) {
        // Force STR=1 by moving one point from the largest other bucket.
        for (const it of frac) {
          if (it.i === strIdx) continue;
          if (base[it.i] > 0) {
            base[it.i] -= 1;
            base[strIdx] = Math.min(caps.strength, base[strIdx] + 1);
            break;
          }
        }
        if (base[strIdx] <= 0 && caps.strength > 0) base[strIdx] = 1;
      }
    }
    // Fix sum (caps may have reduced allocations)
    used = base.reduce((a, b) => a + b, 0);
    if (used !== numPoints) {
      let diff = numPoints - used;
      let g2 = 0;
      while (diff !== 0 && g2++ < 5000) {
        if (diff > 0) {
          const i = Math.trunc(rng() * base.length);
          const sk = skills[i];
          if (base[i] < caps[sk]) {
            base[i] += 1;
            diff -= 1;
          }
        } else {
          const i = Math.trunc(rng() * base.length);
          if (requireStr && skills[i] === "strength" && base[i] <= 1) continue;
          if (base[i] > 0) {
            base[i] -= 1;
            diff += 1;
          }
        }
      }
    }
    return base;
  }

  function refineAroundAnchor(args: {
    anchor: number[];
    numPoints: number;
    caps: Record<Skill, number>;
    radius: number;
    requireStr: boolean;
    rng: () => number;
  }): number[] {
    const { anchor, numPoints, caps, radius, requireStr, rng } = args;
    const v = anchor.slice();
    for (let i = 0; i < v.length; i += 1) {
      const d = Math.trunc((rng() * (radius * 2 + 1)) - radius);
      const sk = skills[i];
      v[i] = clampInt(v[i] + d, 0, caps[sk]);
    }
    // Fix sum
    let sum = v.reduce((a, b) => a + b, 0);
    let diff = numPoints - sum;
    let guard = 0;
    while (diff !== 0 && guard++ < 5000) {
      const i = Math.trunc(rng() * v.length);
      const sk = skills[i];
      if (diff > 0) {
        if (v[i] < caps[sk]) {
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
    if (requireStr) {
      const strIdx = skills.indexOf("strength");
      if (v[strIdx] <= 0 && caps.strength > 0) v[strIdx] = 1;
    }
    return v;
  }

  async function runMcOptimizer(mode: "frag" | "XP" | "stage") {
    if (mcRunning) return;
    cancelRef.current.cancelled = false;
    const hc = typeof navigator !== "undefined" ? Number((navigator as any).hardwareConcurrency ?? 4) : 4;
    const workerCount = clampInt(Math.max(1, hc - 1), 1, 8);
    const pool = createWorkerPool(workerCount);
    cancelRef.current.pool = pool;
    setMcRunning(true);
    setMcProgress("Starting…");

    const archLevel = clampInt(Number(build.archLevel ?? 0), 0, 999);
    // Always enabled (matches desktop; user should not toggle)
    const screeningSims = 200;
    const refinementSims = 500;
    const targetFrag = mcSettings.targetFrag;

    const caps: Record<Skill, number> = {
      strength: Math.min(archLevel, getSkillPointCap(build, "strength")),
      agility: Math.min(archLevel, getSkillPointCap(build, "agility")),
      perception: Math.min(archLevel, getSkillPointCap(build, "perception")),
      intellect: Math.min(archLevel, getSkillPointCap(build, "intellect")),
      luck: Math.min(archLevel, getSkillPointCap(build, "luck")),
    };

    const baseSamples = Math.max(500, Math.max(1, archLevel) * 20);
    const nSamples = baseSamples * 4;
    const topRatio = 0.05;
    const requireStr = true;

    const seedBase = (Date.now() & 0x7fffffff) >>> 0;
    const rng = mulberry32(seedBase);

    const cardCfg = { blockCards: build.blockCards, polychromeBonus: getPolychromeBonus() };
    const options = { use_crit: true, enrage_enabled: build.enrageEnabled, flurry_enabled: build.flurryEnabled, quake_enabled: build.quakeEnabled };

    type Cand = { dist: number[]; primary: number; secondary: number | null; tertiary: number | null };
    const scores: Cand[] = [];

    const maxPending = Math.max(2, pool.size * 2);
    let completed = 0;

    const submitCandidate = async (dist: number[], simN: number, seed: number) => {
      const b2: ArchBuild = { ...build, skillPoints: { strength: dist[0], agility: dist[1], perception: dist[2], intellect: dist[3], luck: dist[4] } };
      const stats2 = getTotalStats(b2);
      if (mode === "frag") {
        const out = await pool.run({
          type: "fragmentSummary",
          payload: { stats: stats2, starting_floor: 1, n_sims: simN, options, cardCfg, seed, target_frag: targetFrag },
        });
        scores.push({ dist, primary: Number(out.avg_frag_per_hour ?? 0), secondary: null, tertiary: null });
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
        // primary XP/h, tie-break by avg stage then fragments/h
        scores.push({ dist, primary: xpPerHour, secondary: avgMaxStage, tertiary: fragsPerHour });
      } else {
        // primary avg stage, tie-break by fragments/h then XP/h (matches desktop intent)
        scores.push({ dist, primary: avgMaxStage, secondary: fragsPerHour, tertiary: xpPerHour });
      }
    };

    function compareCand(a: Cand, b: Cand): number {
      const eps = 0.01;
      if (Math.abs(a.primary - b.primary) >= eps) return b.primary - a.primary;
      const as = a.secondary ?? -Infinity;
      const bs = b.secondary ?? -Infinity;
      if (Math.abs(as - bs) >= eps) return bs - as;
      const at = a.tertiary ?? -Infinity;
      const bt = b.tertiary ?? -Infinity;
      if (Math.abs(at - bt) >= eps) return bt - at;
      return 0;
    }

    function candToDistMap(dist: number[]): { strength: number; agility: number; perception: number; intellect: number; luck: number } {
      return { strength: dist[0] ?? 0, agility: dist[1] ?? 0, perception: dist[2] ?? 0, intellect: dist[3] ?? 0, luck: dist[4] ?? 0 };
    }

    function makeTieBreakReport(cands: Cand[], best: Cand, eps: number): TieBreakReport {
      const tiedAtPrimary = cands.filter((c) => Math.abs(c.primary - best.primary) < eps).length;
      const hasSecondary = (best.secondary ?? 0) > 0 || cands.some((c) => (c.secondary ?? 0) !== 0);
      const hasTertiary = (best.tertiary ?? 0) > 0 || cands.some((c) => (c.tertiary ?? 0) !== 0);
      const primaryMetric = mode === "stage" ? "avg_max_stage" : mode === "XP" ? "xp_per_hour" : "frag_per_hour";
      let winnerReason = "highest primary score";
      if (tiedAtPrimary > 1 && (mode === "stage" || mode === "XP")) {
        winnerReason = hasTertiary ? "tie-break by secondary then tertiary" : hasSecondary ? "tie-break by secondary" : "tie-break (lexicographic)";
      }
      const top3 = cands.slice(0, 3).map((c, i) => ({
        label: `#${i + 1}`,
        primary: c.primary,
        secondary: c.secondary ?? undefined,
        tertiary: c.tertiary ?? undefined,
        dist: candToDistMap(c.dist),
      }));
      return { mode, epsilon: eps, primaryMetric, tiedAtPrimary, winnerReason, top3 };
    }

    try {
      if (archLevel <= 0) throw new Error("Arch level must be >= 1.");

      // If both screening+refinement are off, just run final sims on current build.
      if (screeningSims <= 0 && refinementSims <= 0) {
        setMcProgress("Final sims (1000) on current build…");

        const bestBuild = build;
        const bestStats = getTotalStats(bestBuild);
        const totalFinal = 1000;
        const chunkSize = clampInt(Math.trunc(totalFinal / Math.max(1, pool.size * 4)), 10, 100);
        let remaining = totalFinal;
        let done = 0;

        const objectiveSamples: number[] = [];
        let sumFloors = 0;
        let sumXp = 0;
        let sumTotalFrags = 0;
        let sumDur = 0;
        let sampleCount = 0;

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
              payload: { stats: bestStats, starting_floor: 1, n_sims: n, options, cardCfg, seed, targetFrag: mode === "frag" ? targetFrag : null },
            })
            .then((out) => {
              const dur: number[] = out.run_duration_seconds_samples ?? [];
              const xp: number[] = out.xp_per_run_samples ?? [];
              const maxs: number[] = out.max_stage_samples ?? [];
              const floors: number[] = out.floors_cleared_samples ?? [];
              const totals: number[] = out.total_fragments_samples ?? [];
              const targ: number[] = out.target_frag_samples ?? [];
              for (let i = 0; i < dur.length; i += 1) {
                const d = Number(dur[i] ?? 1);
                const runsPerHour = d > 0 ? 3600.0 / d : 0;
                if (mode === "XP") objectiveSamples.push(Number(xp[i] ?? 0) * runsPerHour);
                else if (mode === "frag") objectiveSamples.push(Number(targ[i] ?? 0) * runsPerHour);
                else objectiveSamples.push(Number(maxs[i] ?? 0));

                sumDur += d;
                sumXp += Number(xp[i] ?? 0);
                sumFloors += Number(floors[i] ?? 0);
                sumTotalFrags += Number(totals[i] ?? 0);
                sampleCount += 1;
              }
              done += n;
              setMcProgress(`Final sims (${done}/${totalFinal})`);
            });
          tasks.push(t);
          remaining -= n;
        }
        await Promise.all(tasks);
        if (cancelRef.current.cancelled) throw new Error("cancelled");

        const avgFloors = sampleCount > 0 ? sumFloors / sampleCount : 0;
        const avgXp = sampleCount > 0 ? sumXp / sampleCount : 0;
        const avgTotalFrags = sampleCount > 0 ? sumTotalFrags / sampleCount : 0;
        const avgDur = sampleCount > 0 ? sumDur / sampleCount : 1;
        const xpPerHour = avgDur > 0 ? (avgXp * 3600.0) / avgDur : 0;
        const fragmentsPerHour = avgDur > 0 ? (avgTotalFrags * 3600.0) / avgDur : 0;

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
            fragmentsPerRunTotal: avgTotalFrags,
            xpPerHour,
            fragmentsPerHour,
          },
          mc: { archLevel, screeningSims, refinementSims, targetFrag: mode === "frag" ? targetFrag : undefined, objective: mode, objectiveSamples },
        };
        setMcLog((xs) => [entry, ...xs]);
        setActiveLogId(entry.id);
        setMcProgress("Done.");
        return;
      }

      const phase1Sims = screeningSims > 0 ? screeningSims : Math.max(1, refinementSims);
      setMcProgress(`Phase 1: Search (${nSamples} samples, N=${phase1Sims})…`);
      const inFlight = new Set<Promise<void>>();
      for (let i = 0; i < nSamples; i += 1) {
        if (cancelRef.current.cancelled) throw new Error("cancelled");
        const dist = sampleDirichletInteger({ numPoints: archLevel, caps, requireStr, rng });
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
      scores.sort(compareCand);
      const numAnchors = Math.max(1, Math.trunc(scores.length * topRatio));
      const anchors = scores.slice(0, numAnchors);

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
            const dist = refineAroundAnchor({ anchor: anchors[a]!.dist, numPoints: archLevel, caps, radius, requireStr, rng });
            const p = (async () => {
              const b2: ArchBuild = { ...build, skillPoints: { strength: dist[0], agility: dist[1], perception: dist[2], intellect: dist[3], luck: dist[4] } };
              const stats2 = getTotalStats(b2);
              if (mode === "frag") {
                const out = await pool.run({
                  type: "fragmentSummary",
                  payload: { stats: stats2, starting_floor: 1, n_sims: refinementSims, options, cardCfg, seed: seedBase + 100_000 + a * 100 + j, target_frag: targetFrag },
                });
                refined.push({ dist, primary: Number(out.avg_frag_per_hour ?? 0), secondary: null, tertiary: null });
                return;
              }
              const out = await pool.run({
                type: "stageSummary",
                payload: { stats: stats2, starting_floor: 1, n_sims: refinementSims, options, cardCfg, seed: seedBase + 100_000 + a * 100 + j },
              });
              const avgMaxStage = Number(out.avg_max_stage ?? 0);
              const fragsPerHour = Number(out.fragments_per_hour ?? 0);
              const xpPerHour = Number(out.xp_per_hour ?? 0);
              if (mode === "XP") refined.push({ dist, primary: xpPerHour, secondary: avgMaxStage, tertiary: fragsPerHour });
              else refined.push({ dist, primary: avgMaxStage, secondary: fragsPerHour, tertiary: xpPerHour });
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
        refined.sort(compareCand);
        const bestRefined = refined[0] ?? null;
        const bestScreen = scores[0] ?? null;
        best = bestRefined && bestScreen ? (compareCand(bestRefined, bestScreen) <= 0 ? bestRefined : bestScreen) : bestRefined ?? bestScreen ?? undefined;
        bestPool = bestRefined && bestScreen ? (compareCand(bestRefined, bestScreen) <= 0 ? refined : scores) : refined.length ? refined : scores;
      }
      if (!best) throw new Error("No candidates");
      const tieBreakReport = makeTieBreakReport(bestPool, best, 0.01);

      const bestBuild: ArchBuild = {
        ...build,
        skillPoints: { strength: best.dist[0], agility: best.dist[1], perception: best.dist[2], intellect: best.dist[3], luck: best.dist[4] },
      };
      const bestStats = getTotalStats(bestBuild);

      // Phase 3: final 1000 sims
      const totalFinal = 1000;
      setMcProgress(`Phase 3: Final sims (${totalFinal})…`);
      const chunkSize = clampInt(Math.trunc(totalFinal / Math.max(1, pool.size * 4)), 10, 100);
      let remaining = totalFinal;
      let done = 0;

      const objectiveSamples: number[] = [];
      let sumFloors = 0;
      let sumXp = 0;
      let sumTotalFrags = 0;
      let sumDur = 0;
      let sampleCount = 0;

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
            payload: { stats: bestStats, starting_floor: 1, n_sims: n, options, cardCfg, seed, targetFrag: mode === "frag" ? targetFrag : null },
          })
          .then((out) => {
            const dur: number[] = out.run_duration_seconds_samples ?? [];
            const xp: number[] = out.xp_per_run_samples ?? [];
            const maxs: number[] = out.max_stage_samples ?? [];
            const floors: number[] = out.floors_cleared_samples ?? [];
            const totals: number[] = out.total_fragments_samples ?? [];
            const targ: number[] = out.target_frag_samples ?? [];
            for (let i = 0; i < dur.length; i += 1) {
              const d = Number(dur[i] ?? 1);
              const runsPerHour = d > 0 ? 3600.0 / d : 0;
              if (mode === "XP") objectiveSamples.push(Number(xp[i] ?? 0) * runsPerHour);
              else if (mode === "frag") objectiveSamples.push(Number(targ[i] ?? 0) * runsPerHour);
              else objectiveSamples.push(Number(maxs[i] ?? 0));

              sumDur += d;
              sumXp += Number(xp[i] ?? 0);
              sumFloors += Number(floors[i] ?? 0);
              sumTotalFrags += Number(totals[i] ?? 0);
              sampleCount += 1;
            }
            done += n;
            setMcProgress(`Phase 3: Final sims (${done}/${totalFinal})`);
          });
        tasks.push(t);
        remaining -= n;
      }
      await Promise.all(tasks);

      if (cancelRef.current.cancelled) throw new Error("cancelled");

      // Save entry (MC averages from final samples)
      const avgFloors = sampleCount > 0 ? sumFloors / sampleCount : 0;
      const avgXp = sampleCount > 0 ? sumXp / sampleCount : 0;
      const avgTotalFrags = sampleCount > 0 ? sumTotalFrags / sampleCount : 0;
      const avgDur = sampleCount > 0 ? sumDur / sampleCount : 1;
      const xpPerHour = avgDur > 0 ? (avgXp * 3600.0) / avgDur : 0;
      const fragmentsPerHour = avgDur > 0 ? (avgTotalFrags * 3600.0) / avgDur : 0;
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
          fragmentsPerRunTotal: avgTotalFrags,
          xpPerHour,
          fragmentsPerHour,
        },
        mc: { archLevel, screeningSims, refinementSims, targetFrag: mode === "frag" ? targetFrag : undefined, objective: mode, objectiveSamples, tieBreak: tieBreakReport },
      };
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
      setMcRunning(false);
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

  function renderHistogramCard(args: { samples: number[]; kind: "stage" | "rate"; title: string; xLabel: string }): ReactNode {
    const { samples, kind, title, xLabel } = args;
    if (!samples.length) return null;
    const W = 560;
    const H = 184; // extra space for x-axis labels
    const pad = 10;
    const axisH = 26;

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
    const bars = counts.map((c, i) => {
      const h = ((H - pad * 2 - axisH) * c) / maxC;
      const x = pad + i * barW;
      const y = H - pad - axisH - h;
      const binStart = bins[i] ?? 0;
      const binEnd = binStart + step;
      const titleText = kind === "stage" ? `Stage ${Math.floor(binStart)}` : `${binStart.toFixed(1)}–${binEnd.toFixed(1)}`;
      return (
        <rect key={i} x={x} y={y} width={Math.max(1, barW - 1)} height={h} fill="rgba(92,107,192,0.55)">
          <title>{titleText}</title>
        </rect>
      );
    });

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
          <svg width="100%" viewBox={`0 0 ${W} ${H}`} className="histSvg" aria-label={title}>
            {bars}
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

  function renderTieBreakBars(tb: NonNullable<TieBreakReport>): ReactNode {
    if (!tb?.top3?.length) return null;
    // Match desktop visual: grouped horizontal bars for Fragments/h and XP/h with legend outside plot.
    const rows = tb.top3;
    const showFrags = tb.mode !== "frag";
    const showXp = tb.mode !== "frag";
    const maxFrag = Math.max(1, ...rows.map((r) => Number(r.secondary ?? 0)));
    const maxXp = Math.max(1, ...rows.map((r) => Number(r.tertiary ?? 0)));

    const labelFor = (r: (typeof rows)[number]) => {
      const d = r.dist;
      const parts: string[] = [];
      if (d.strength) parts.push(`STR:${d.strength}`);
      if (d.agility) parts.push(`AGI:${d.agility}`);
      if (d.perception) parts.push(`PER:${d.perception}`);
      if (d.intellect) parts.push(`INT:${d.intellect}`);
      if (d.luck) parts.push(`LCK:${d.luck}`);
      return `${r.label}: ${parts.join(" | ") || "All 0"}`;
    };

    return (
      <div className="tbWrap">
        <div className="tbPlot">
          {rows.map((r) => {
            const frag = Number(r.secondary ?? 0);
            const xp = Number(r.tertiary ?? 0);
            const fragPct = Math.max(0, Math.min(1, frag / maxFrag));
            const xpPct = Math.max(0, Math.min(1, xp / maxXp));
            return (
              <div key={r.label} className="tbRow">
                <div className="tbLabel mono">{labelFor(r)}</div>
                <div className="tbBars">
                  {showFrags ? (
                    <div className="tbBarLine">
                      <div className="tbBar tbBarFrag" style={{ width: `${(fragPct * 100).toFixed(1)}%` }} />
                      <div className="tbValue mono">{frag.toFixed(2)}</div>
                    </div>
                  ) : null}
                  {showXp ? (
                    <div className="tbBarLine">
                      <div className="tbBar tbBarXp" style={{ width: `${(xpPct * 100).toFixed(1)}%` }} />
                      <div className="tbValue mono">{xp.toFixed(1)}</div>
                    </div>
                  ) : null}
                </div>
              </div>
            );
          })}
        </div>
        <div className="tbLegend">
          <div className="tbLegendTitle">Legend</div>
          <div className="tbLegendItem">
            <span className="tbSwatch tbSwatchFrag" /> Fragments/h
          </div>
          <div className="tbLegendItem">
            <span className="tbSwatch tbSwatchXp" /> XP/h
          </div>
        </div>
      </div>
    );
  }

  const visibleMcLog = useMemo(() => mcLog.filter((e) => e.mcType !== "det"), [mcLog]);
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

      <div className="panel archSetupPanel" style={{ background: "var(--tier1)" }}>
        <div className="panelHeader" style={{ marginBottom: 8 }}>
          <h2 className="panelTitle">Run setup</h2>
          <p className="panelHint">
            Calc stage: <span className="mono">{calcStage}</span>
          </p>
        </div>

        <div className="archSetupGrid">
          <div className="archSetupCell" style={{ background: "var(--tier1)" }}>
            <div className="label">
              <span>
                Goal stage
                <Tooltip content={{ title: "Goal stage", lines: ["Matches desktop semantics: calculations use (goal stage - 1)."] }} />
              </span>
              <span className="mono">{build.goalStage}</span>
            </div>
            <input className="input" type="number" min={1} step={1} value={build.goalStage} onChange={(e) => setBuild((s) => ({ ...s, goalStage: clampInt(Number(e.target.value), 1, 999) }))} />
          </div>

          <div className="archSetupCell" style={{ background: "var(--tier2)" }}>
            <div className="label">
              <span>
                Unlocked stage
                <Tooltip content={{ title: "Unlocked stage", lines: ["Used to lock upgrades/cards like the desktop UI."] }} />
              </span>
              <span className="mono">{build.unlockedStage}</span>
            </div>
            <input className="input" type="number" min={1} step={1} value={build.unlockedStage} onChange={(e) => setBuild((s) => ({ ...s, unlockedStage: clampInt(Number(e.target.value), 1, 999) }))} />
          </div>

          <div className="archSetupCell" style={{ background: "var(--tier3)" }}>
            <div className="label">
              <span>
                Arch level
                <Tooltip content={{ title: "Arch level", lines: ["Total skill points available to distribute (and used by the MC optimizers)."] }} />
              </span>
              <span className="mono">{build.archLevel}</span>
            </div>
            <input className="input" type="number" min={0} step={1} value={build.archLevel} onChange={(e) => setArchLevel(Number(e.target.value))} />
            <div className="small" style={{ marginTop: 6 }}>
              Points used: <span className="mono">{totalSkillPoints}</span> / <span className="mono">{build.archLevel}</span>
            </div>
          </div>
        </div>

        <div className="btnRow" style={{ marginTop: 10 }}>
          <button className="btn" type="button" onClick={() => setMcWindowOpen(true)}>
            Open Monte Carlo
          </button>
          <button
            className="btn btnSecondary"
            type="button"
            onClick={() => {
              if (!confirmDanger("Reset all Arch settings? This will reset stages, arch level, stats, upgrades, cards, and toggles.")) return;
              setBuild(defaultBuild());
            }}
            disabled={mcRunning}
          >
            Reset all
          </button>
          <button
            className="btn btnSecondary"
            type="button"
            onClick={() => {
              if (!confirmDanger("Reset MC results log? This will delete all saved MC runs in this browser.")) return;
              setMcLog([]);
              setActiveLogId(null);
            }}
            disabled={mcRunning}
          >
            Reset MC log
          </button>
        </div>
      </div>

      <div className="archGrid archGridNoMc">
        {/* Column 1: stats (collapsible) */}
        <div style={{ display: "grid", gap: 12 }}>
          <Collapsible
            id="arch-player-stats"
            title="Player stats"
            defaultExpanded={true}
            headerRight={
              <span className="mono">
                {totalSkillPoints}/{build.archLevel}
              </span>
            }
          >
            <div className="kv" style={{ background: "var(--tier1)" }}>
              <kbd>XP gain</kbd>
              <div className="mono">{stats.xp_gain_total.toFixed(3)}x</div>
              <kbd>Fragment gain</kbd>
              <div className="mono">{stats.fragment_mult.toFixed(3)}x</div>
              <kbd>Damage</kbd>
              <div className="mono">{formatInt(stats.total_damage)}</div>
              <kbd>Armor pen</kbd>
              <div className="mono">{formatInt(stats.armor_pen)}</div>
              <kbd>Stamina</kbd>
              <div className="mono">{formatInt(stats.max_stamina)}</div>
              <kbd>Crit</kbd>
              <div className="mono">{formatPct(stats.crit_chance, 2)}</div>
              <kbd>Crit dmg</kbd>
              <div className="mono">{stats.crit_damage.toFixed(3)}x</div>
              <kbd>Super crit</kbd>
              <div className="mono">{formatPct(stats.super_crit_chance, 2)}</div>
              <kbd>Super crit mult</kbd>
              <div className="mono">{stats.super_crit_dmg_mult.toFixed(3)}x</div>
              <kbd>Ultra crit</kbd>
              <div className="mono">{formatPct(stats.ultra_crit_chance, 2)}</div>
              <kbd>Ultra crit mult</kbd>
              <div className="mono">{stats.ultra_crit_dmg_mult.toFixed(3)}x</div>
              <kbd>One-hit</kbd>
              <div className="mono">{formatPct(stats.one_hit_chance, 3)}</div>
            </div>

            <div className="sectionTitle">Stats</div>
            <div className="small" style={{ marginBottom: 8 }}>
              Spend your <span className="mono">Arch level</span> points here.
            </div>
            {(["strength", "agility", "perception", "intellect", "luck"] as const).map((skill) => {
              const cap = getSkillPointCap(build, skill);
              const v = build.skillPoints[skill];
              const short = skill === "strength" ? "STR" : skill === "agility" ? "AGI" : skill === "perception" ? "PER" : skill === "intellect" ? "INT" : "LCK";
              return (
                <div key={skill} className="row" style={{ marginBottom: 8 }}>
                  <div className="label">
                    <span className="mono">{short}</span>
                    <span className="mono">
                      {v} / {cap}
                    </span>
                  </div>
                  <div className="btnRow" style={{ marginTop: 0 }}>
                    <button className="btn btnSecondary" type="button" onClick={() => setSkill(skill, -1)} disabled={v <= 0}>
                      −
                    </button>
                    <button className="btn" type="button" onClick={() => setSkill(skill, +1)} disabled={v >= cap || totalSkillPoints >= build.archLevel}>
                      +
                    </button>
                    <button className="btn btnSecondary" type="button" onClick={() => setSkill(skill, +5)} disabled={v >= cap || totalSkillPoints >= build.archLevel}>
                      +5
                    </button>
                    <button className="btn btnSecondary" type="button" onClick={() => setSkill(skill, -5)} disabled={v <= 0}>
                      −5
                    </button>
                  </div>
                </div>
              );
            })}

            <div className="sectionTitle">Abilities</div>
            <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
              <button className="btn btnSecondary" type="button" onClick={() => setBuild((s) => ({ ...s, enrageEnabled: !s.enrageEnabled }))}>
                <Sprite path="sprites/archaeology/Archaeology_Ability_Enrage.png" alt="Enrage" className="iconSmall" /> Enrage:{" "}
                <span className="mono">{build.enrageEnabled ? "ON" : "OFF"}</span>
              </button>
              <button className="btn btnSecondary" type="button" onClick={() => setBuild((s) => ({ ...s, flurryEnabled: !s.flurryEnabled }))}>
                <Sprite path="sprites/archaeology/Archaeology_Ability_Flurry.png" alt="Flurry" className="iconSmall" /> Flurry:{" "}
                <span className="mono">{build.flurryEnabled ? "ON" : "OFF"}</span>
              </button>
              <button className="btn btnSecondary" type="button" onClick={() => setBuild((s) => ({ ...s, quakeEnabled: !s.quakeEnabled }))}>
                <Sprite path="sprites/archaeology/Archaeology_Ability_Quake.png" alt="Quake" className="iconSmall" /> Quake:{" "}
                <span className="mono">{build.quakeEnabled ? "ON" : "OFF"}</span>
              </button>
              <button className="btn btnSecondary" type="button" onClick={() => setBuild((s) => ({ ...s, avadaKedaEnabled: !s.avadaKedaEnabled }))}>
                <Sprite path="sprites/archaeology/avadakeda.png" alt="Avada Keda" className="iconSmall" /> Avada Keda:{" "}
                <span className="mono">{build.avadaKedaEnabled ? "ON" : "OFF"}</span>
              </button>
              <button className="btn btnSecondary" type="button" onClick={() => setBuild((s) => ({ ...s, blockBonkerEnabled: !s.blockBonkerEnabled }))}>
                <Sprite path="sprites/archaeology/blockbonker.png" alt="Block Bonker" className="iconSmall" /> Block Bonker:{" "}
                <span className="mono">{build.blockBonkerEnabled ? "ON" : "OFF"}</span>
              </button>
            </div>

            <div className="sectionTitle">Mods</div>
            <div className="small" style={{ marginBottom: 8 }}>
              Mod chances are <span className="mono">per block hit</span> (matches the desktop semantics).
            </div>
            <div className="kv" style={{ background: "var(--tier1)" }}>
              <kbd>Exp mod chance</kbd>
              <div className="mono">{formatPct(stats.exp_mod_chance, 2)}</div>
              <kbd>Exp mod mult (avg)</kbd>
              <div className="mono">{stats.exp_mod_gain.toFixed(2)}x</div>

              <kbd>Loot mod chance</kbd>
              <div className="mono">{formatPct(stats.loot_mod_chance, 2)}</div>
              <kbd>Loot mod mult (avg)</kbd>
              <div className="mono">{stats.loot_mod_multiplier.toFixed(2)}x</div>

              <kbd>Speed mod chance</kbd>
              <div className="mono">{formatPct(stats.speed_mod_chance, 2)}</div>
              <kbd>Speed mod gain</kbd>
              <div className="mono">{stats.speed_mod_gain.toFixed(1)}</div>

              <kbd>Stamina mod chance</kbd>
              <div className="mono">{formatPct(stats.stamina_mod_chance, 2)}</div>
              <kbd>Stamina mod gain (avg)</kbd>
              <div className="mono">{stats.stamina_mod_gain.toFixed(1)}</div>
            </div>
          </Collapsible>
        </div>

        {/* Column 2: upgrades/cards */}
        <div style={{ display: "grid", gap: 12 }}>
          <Collapsible
            id="arch-fragment-upgrades"
            title="Fragment upgrades"
            defaultExpanded={true}
            headerRight={<Sprite path="sprites/common/skill_shard.png" alt="Fragment upgrades" className="iconSmall" />}
          >
            <div className="panel fragmentUpgradesPanel" style={{ background: "var(--tier2)" }}>
              <div className="small" style={{ marginBottom: 10 }}>
                Unlock gating uses <span className="mono">unlockedStage</span>.
              </div>

              {(["common", "rare", "epic", "legendary", "mythic"] as const).map((ct) => {
              const entries = fragmentGroups[ct] ?? [];
              const color = BLOCK_COLORS[ct];
              const icon = `sprites/archaeology/block_${ct}_t1.png`;
              if (!entries.length) return null;
              return (
                <div key={ct} className="fragmentGroup" style={{ borderColor: `rgba(15,23,42,0.12)` }}>
                  <div className="fragmentGroupHeader">
                    <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                      <Sprite path={icon} alt={`${ct} icon`} className="iconSmall" />
                      <div className="mono" style={{ fontWeight: 900, color }}>
                        {ct.toUpperCase()}
                      </div>
                    </div>
                  </div>

                  <div style={{ display: "grid", gap: 8 }}>
                    {entries.map(([key, info]) => {
                      const lvl = clampInt(Number(build.fragmentUpgradeLevels[key] ?? 0), 0, clampInt(Number(info.max_level ?? 0), 0, 999));
                      const maxLvl = clampInt(Number(info.max_level ?? 0), 0, 999);
                      const stageUnlock = clampInt(Number(info.stage_unlock ?? 0), 0, 999);
                      const locked = build.unlockedStage < stageUnlock;
                      const nextCost = getUpgradeCost(key, lvl);
                      return (
                        <div key={key} className="fragmentUpgradeRow" style={heatStyle(lvl)}>
                          <div className="fragmentUpgradeTop">
                            <div className="mono" style={{ fontWeight: 900 }}>
                              {info.display_name}
                            </div>
                            <div className="fragmentUpgradeRight upgradeLevel">
                              <span className="small">lvl</span>{" "}
                              <span className="heatNum mono" style={heatStyle(lvl)}>
                                {lvl}
                              </span>{" "}
                              <span className="small">/</span> <span className="mono">{maxLvl}</span>
                            </div>
                          </div>
                          <div className="small">
                            next cost: <span className="mono">{nextCost == null ? "—" : String(nextCost)}</span>
                            {locked ? (
                              <>
                                {" "}
                                • <span className="pillLocked">LOCKED</span> <span className="lockedText">until stage {stageUnlock}</span>
                              </>
                            ) : null}
                          </div>
                          <div className="btnRow fragmentUpgradeButtons" style={{ marginTop: 8 }}>
                            <button className="btn btnSecondary" type="button" onClick={() => setFragmentUpgrade(key, -5)} disabled={lvl <= 0 || mcRunning}>
                              −5
                            </button>
                            <button className="btn btnSecondary" type="button" onClick={() => setFragmentUpgrade(key, -1)} disabled={lvl <= 0 || mcRunning}>
                              −
                            </button>
                            <button className="btn" type="button" onClick={() => setFragmentUpgrade(key, +1)} disabled={locked || lvl >= maxLvl || mcRunning}>
                              +
                            </button>
                            <button className="btn btnSecondary" type="button" onClick={() => setFragmentUpgrade(key, +5)} disabled={locked || lvl >= maxLvl || mcRunning}>
                              +5
                            </button>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>
              );
            })}
            </div>
          </Collapsible>

          <Collapsible id="arch-gem-upgrades" title="Gem upgrades" defaultExpanded={true} headerRight={<Sprite path="sprites/common/gem.png" alt="Gem" className="iconSmall" />}>
            <div className="panel gemPanel" style={{ background: "var(--tier1)" }}>
              <div className="small" style={{ marginBottom: 10 }}>
                Permanent. Maxed levels are highlighted.
              </div>

              {(["stamina", "xp", "fragment", "arch_xp"] as const).map((k) => {
              const lvl = build.gemUpgrades[k] ?? 0;
              const max = GEM_UPGRADE_BONUSES[k].max_level;
              const nextCost = GEM_COSTS[k][lvl] ?? null;
              const locked = build.unlockedStage < (GEM_UPGRADE_BONUSES[k].stage_unlock ?? 0);
              const maxed = lvl >= max;
              return (
                <div key={k} className={`gemUpgradeRow ${maxed ? "gemUpgradeMaxed" : ""}`} style={maxed ? undefined : heatStyle(lvl)}>
                  <div className="label">
                    <span className="mono">{k}</span>
                    <span className="mono upgradeLevel">
                      <span className="small">lvl</span>{" "}
                      <span className="heatNum mono" style={heatStyle(lvl)}>
                        {lvl}
                      </span>{" "}
                      <span className="small">/</span> <span className="mono">{max}</span>
                    </span>
                  </div>
                  <div className="small">
                    next cost: <span className="mono">{nextCost == null ? "—" : String(nextCost)}</span>
                    {locked ? (
                      <>
                        {" "}
                        • <span className="pillLocked">LOCKED</span> <span className="lockedText">until stage {GEM_UPGRADE_BONUSES[k].stage_unlock}</span>
                      </>
                    ) : null}
                  </div>
                  <div className="btnRow" style={{ marginTop: 8 }}>
                    <button className="btn btnSecondary" type="button" onClick={() => setGemUpgrade(k, -1)} disabled={lvl <= 0 || mcRunning}>
                      −
                    </button>
                    <button className="btn" type="button" onClick={() => setGemUpgrade(k, +1)} disabled={locked || lvl >= max || mcRunning}>
                      +
                    </button>
                  </div>
                </div>
              );
            })}
            </div>
          </Collapsible>

          <Collapsible id="arch-cards" title="Cards" defaultExpanded={true} headerRight={<Sprite path="sprites/archaeology/cards.png" alt="Cards" className="iconSmall" />}>
            <div className="small" style={{ marginBottom: 8 }}>
              Per block type + tier. Card effects: HP −10/−20/−35% and XP +10/+20/+35% (polychrome can be boosted by the Stage 34 fragment upgrade).
            </div>

            <div style={{ display: "grid", gap: 6 }}>
              {BLOCK_TYPES.map((bt) => {
                const color = BLOCK_COLORS[bt];
                return (
                  <div key={bt} style={{ border: "1px solid rgba(15,23,42,0.10)", borderRadius: 10, padding: 10, background: "var(--tier2)" }}>
                    <div style={{ display: "flex", gap: 8, alignItems: "center", marginBottom: 8 }}>
                      <span className="mono" style={{ color, fontWeight: 900 }}>
                        {bt.toUpperCase()}
                      </span>
                    </div>

                    {[1, 2, 3].map((tier) => {
                      const t = tier as BlockTier;
                      if (!getBlockData(t, bt)) return null;
                      const cardKey = `${bt},${t}`;
                      const cur = (build.blockCards[cardKey] ?? 0) as CardLevel;
                      const icon = `sprites/archaeology/block_${bt}_t1.png`;
                      return (
                        <div key={tier} style={{ display: "grid", gridTemplateColumns: "1fr auto", gap: 8, alignItems: "center", marginBottom: 6 }}>
                          <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
                            <Sprite path={icon} alt={`${bt} icon`} className="iconSmall" />
                            <div className="mono">
                              {bt} T{tier}
                            </div>
                          </div>
                          <div style={{ display: "flex", gap: 6, justifyContent: "flex-end", flexWrap: "wrap" }}>
                            <button
                              className={`btn btnSecondary ${cur === 1 ? "cardBtnActive" : ""}`}
                              type="button"
                              onClick={() => setBlockCard(bt, t, 1)}
                              style={{ padding: "6px 10px" }}
                            >
                              Card {cur === 1 ? "✓" : ""}
                            </button>
                            <button
                              className={`btn btnSecondary ${cur === 2 ? "cardBtnActive" : ""}`}
                              type="button"
                              onClick={() => setBlockCard(bt, t, 2)}
                              style={{ padding: "6px 10px" }}
                            >
                              Gild {cur === 2 ? "✓" : ""}
                            </button>
                            <button
                              className={`btn btnSecondary ${cur === 3 ? "cardBtnActive" : ""}`}
                              type="button"
                              onClick={() => setBlockCard(bt, t, 3)}
                              style={{ padding: "6px 10px" }}
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

              <div style={{ border: "1px solid rgba(15,23,42,0.10)", borderRadius: 10, padding: 10, background: "var(--tier2)" }}>
                <div className="label">
                  <span className="mono">Misc card (ability cooldown)</span>
                  <span className="mono">{build.miscCardLevel === 0 ? "OFF" : build.miscCardLevel === 1 ? "Card" : build.miscCardLevel === 2 ? "Gild" : "Poly"}</span>
                </div>
                <div className="small">Card: −3% cooldown • Gild: −6% • Poly: −10%</div>
                <div className="btnRow" style={{ marginTop: 8 }}>
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
              <div style={{ display: "flex", gap: 8 }}>
                <button className="btn btnSecondary" type="button" onClick={() => setMcWindowOpen(false)}>
                  Close
                </button>
              </div>
            </div>
            <div className="modalBody modalBodyWide">
              <div className="mcModalGrid">
                <div className="panel mcPanel" style={{ background: "var(--tier3)" }}>
                  <div className="panelHeader">
                    <h2 className="panelTitle">Monte Carlo</h2>
                    <p className="panelHint">
                      Multi-core • unbiased from <span className="mono">Stage 1</span>
                    </p>
                  </div>

                  <label className="toggle">
                    <input type="checkbox" checked={true} disabled={true} />
                    Screening phase (fast)
                  </label>
                  <label className="toggle" style={{ marginTop: 6 }}>
                    <input type="checkbox" checked={true} disabled={true} />
                    Refinement phase (accurate)
                  </label>

                  <div className="mcCards">
                    <div className="mcCard mcCardStage">
                      <div className="mcCardTitle">Stage Push Optimizer</div>
                      <div className="small">Objective: maximize average max stage.</div>
                      <div className="btnRow" style={{ marginTop: 10 }}>
                        <button className="btn" type="button" disabled={mcRunning} onClick={() => runMcOptimizer("stage")}>
                          Run MC
                        </button>
                        {mcRunning ? (
                          <button className="btn btnSecondary" type="button" onClick={cancelMc}>
                            Cancel
                          </button>
                        ) : null}
                      </div>
                    </div>

                    <div className="mcCard mcCardXp">
                      <div className="mcCardTitle">XP Optimizer</div>
                      <div className="small">Objective: maximize XP/hour.</div>
                      <div className="btnRow" style={{ marginTop: 10 }}>
                        <button className="btn" type="button" disabled={mcRunning} onClick={() => runMcOptimizer("XP")}>
                          Run MC
                        </button>
                        {mcRunning ? (
                          <button className="btn btnSecondary" type="button" onClick={cancelMc}>
                            Cancel
                          </button>
                        ) : null}
                      </div>
                    </div>

                    <div className="mcCard mcCardFrag">
                      <div className="mcCardTitle">Fragment Farmer</div>
                      <div className="small">Objective: maximize target fragments/hour.</div>
                      <div className="row" style={{ marginTop: 8 }}>
                        <div className="label">
                          <span>Target fragment</span>
                          <span className="mono">{mcSettings.targetFrag.toUpperCase()}</span>
                        </div>
                        <select
                          className="input"
                          disabled={mcRunning}
                          value={mcSettings.targetFrag}
                          onChange={(e) => setMcSettings((s) => ({ ...s, targetFrag: e.target.value as BlockType }))}
                        >
                          {(["common", "rare", "epic", "legendary", "mythic"] as const).map((t) => (
                            <option key={t} value={t}>
                              {t.toUpperCase()}
                            </option>
                          ))}
                        </select>
                      </div>
                      <div className="btnRow" style={{ marginTop: 10 }}>
                        <button className="btn" type="button" disabled={mcRunning} onClick={() => runMcOptimizer("frag")}>
                          Run MC
                        </button>
                        {mcRunning ? (
                          <button className="btn btnSecondary" type="button" onClick={cancelMc}>
                            Cancel
                          </button>
                        ) : null}
                      </div>
                    </div>
                  </div>
                </div>

                <div className="mcLogPanel">
                  <div className="mcLogHeader">
                    <div className="mcLogTitle">MC Results Log</div>
                    <div style={{ display: "flex", gap: 8 }}>
                      <button
                        className="btn btnSecondary"
                        type="button"
                        style={{ padding: "6px 10px", background: "#ffffff" }}
                        onClick={() => {
                          if (!confirmDanger("Reset MC results log? This will delete all saved MC runs in this browser.")) return;
                          setMcLog([]);
                          setActiveLogId(null);
                        }}
                        disabled={mcRunning}
                      >
                        Reset
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
                              <th className="mono">Objective</th>
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
                              const obj =
                                e.mc?.objective ?? (e.mcType === "stage" ? "stage" : e.mcType === "XP" ? "XP" : "frag");
                              const target = e.mc?.targetFrag ?? null;
                              const sObj = sampleStats(e.mc?.objectiveSamples ?? []);
                              const objLabel =
                                obj === "stage" ? "Max stage" : obj === "XP" ? "XP/h" : `${(target ?? "frag").toUpperCase()}/h`;
                              const objVal = obj === "stage" ? sObj.mean.toFixed(2) : obj === "XP" ? sObj.mean.toFixed(1) : sObj.mean.toFixed(2);

                              const rowClass = `${active ? "active " : ""}${idx % 2 === 1 ? "zebra" : ""}`.trim();
                              return (
                                <>
                                  <tr key={`${e.id}:row`} className={rowClass}>
                                    <td className="mono time">{new Date(e.createdAt).toLocaleString()}</td>
                                    <td className="run">
                                      <span className={`mcTypePill mcTypePill_${e.mcType}`}>{e.mcType.toUpperCase()}</span>{" "}
                                      <span className="label">{e.label}</span>
                                    </td>
                                    <td className="mono">
                                      <span className="small">{objLabel}</span> <span className="mono">{objVal}</span>
                                    </td>
                                    <td className="mono num">{e.metrics.floorsPerRun.toFixed(2)}</td>
                                    <td className="mono num">{Math.round(e.metrics.xpPerHour)}</td>
                                    <td className="mono num">{e.metrics.fragmentsPerHour.toFixed(1)}</td>
                                    <td className="actions" />
                                  </tr>
                                  <tr key={`${e.id}:actions`} className={`${rowClass} mcActionsRow`.trim()}>
                                    <td className="actionsCell" colSpan={7}>
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
                                          className="btn btnSecondary"
                                          type="button"
                                          onClick={() => {
                                            if (!confirmDanger("Delete this saved MC run?")) return;
                                            setMcLog((xs) => xs.filter((x) => x.id !== e.id));
                                            if (active) setActiveLogId(null);
                                            if (openLogId === e.id) setOpenLogId(null);
                                          }}
                                        >
                                          Delete
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
                  {openLog.label} • {openLog.mcType.toUpperCase()}
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
              <div className="kv">
                <kbd>Goal stage</kbd>
                <div className="mono">{openLog.build.goalStage}</div>
                <kbd>Unlocked</kbd>
                <div className="mono">{openLog.build.unlockedStage}</div>
                <kbd>Arch level</kbd>
                <div className="mono">{openLog.build.archLevel}</div>
                <kbd>Floors/run</kbd>
                <div className="mono">{openLog.metrics.floorsPerRun.toFixed(3)}</div>
                <kbd>XP/run</kbd>
                <div className="mono">{openLog.metrics.xpPerRun.toFixed(3)}</div>
                <kbd>XP/h</kbd>
                <div className="mono">{Math.round(openLog.metrics.xpPerHour)}</div>
                <kbd>Frag/h</kbd>
                <div className="mono">{openLog.metrics.fragmentsPerHour.toFixed(1)}</div>
              </div>

              {openLog.mc ? (
                <div style={{ marginTop: 12, display: "grid", gap: 10 }}>
                  <div className="sectionTitle">MC details</div>
                  <div className="small">
                    Objective:{" "}
                    <span className="mono">
                      {openLog.mc.objective === "stage"
                        ? "Max stage"
                        : openLog.mc.objective === "XP"
                          ? "XP/hour"
                          : `${openLog.mc.targetFrag?.toUpperCase() ?? "FRAG"}/hour`}
                    </span>
                  </div>
                  <div className="small">
                    {(() => {
                      const s = sampleStats(openLog.mc?.objectiveSamples ?? []);
                      return (
                        <>
                          Mean ± std: <span className="mono">{s.mean.toFixed(2)}</span> ± <span className="mono">{s.std.toFixed(2)}</span> (min{" "}
                          <span className="mono">{s.min.toFixed(2)}</span>, max <span className="mono">{s.max.toFixed(2)}</span>)
                        </>
                      );
                    })()}
                  </div>
                  <div>
                    {renderHistogramCard({
                      samples: openLog.mc?.objectiveSamples ?? [],
                      kind: openLog.mc.objective === "stage" ? "stage" : "rate",
                      title:
                        openLog.mc.objective === "stage"
                          ? "Distribution of Maximum Stage Reached (1000 MC simulations)"
                          : openLog.mc.objective === "XP"
                            ? "Distribution of XP per Hour (1000 MC simulations)"
                            : "Distribution of Fragments per Hour (1000 MC simulations)",
                      xLabel:
                        openLog.mc.objective === "stage"
                          ? "Max Stage Reached"
                          : openLog.mc.objective === "XP"
                            ? "XP per Hour"
                            : "Fragments per Hour",
                    })}
                  </div>

                  {openLog.mc.tieBreak ? (
                    <div style={{ marginTop: 6 }}>
                      <div className="sectionTitle">Tie-break</div>
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
                                STR {c.dist.strength} • AGI {c.dist.agility} • PER {c.dist.perception} • INT {c.dist.intellect} • LCK {c.dist.luck}
                              </div>
                            </li>
                          ))}
                        </ul>
                      ) : null}
                    </div>
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

