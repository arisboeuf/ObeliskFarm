import { useEffect, useMemo, useRef, useState, type CSSProperties } from "react";
import { formatInt, formatTime } from "../../lib/format";
import { loadJson, saveJson } from "../../lib/storage";
import { COSTS, GEM_UPGRADE_NAMES, PRESTIGE_UNLOCKED, UPGRADE_SHORT_NAMES } from "../../lib/event/constants";
import {
  copyState,
  createEmptyState,
  getMaxLevelWithCaps,
  type Budget,
  type OptimizationResult,
  type UpgradeState,
} from "../../lib/event/optimizer";
import { monteCarloOptimizeGuided, type MCOptimizationResult } from "../../lib/event/monteCarloOptimizer";
import { getGemMaxLevel } from "../../lib/event/simulation";
import { assetUrl } from "../../lib/assets";
import { currencyIconFilename, gemUpgradeIconFilename, upgradeIconFilename } from "../../lib/event/icons";
import { Tooltip } from "../../components/Tooltip";

type SavedStateV1 = { prestige: number; upgrade_levels: Record<string, number[]>; gem_levels: number[] };

type UiState = {
  prestige: number;
  // Budgets (NOT saved, mirroring desktop save behavior)
  budget1: string;
  budget2: string;
  budget3: string;
  budget4: string;
  // Upgrade editor state (saved)
  upgrades: UpgradeState;
  // MC controls
  mcCandidates: number;
  mcRunsPerCombo: number;
  devOnlyMcTuning: boolean;
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
  return (
    <img
      className={className ?? "icon"}
      src={assetUrl(path)}
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
      budget1: "",
      budget2: "",
      budget3: "",
      budget4: "",
      upgrades: base,
      mcCandidates: 2000,
      mcRunsPerCombo: 500,
      devOnlyMcTuning: false,
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
  const workerRef = useRef<Worker | null>(null);
  const lastInitialRef = useRef<UpgradeState | null>(null);

  // autosave (matches desktop save schema: prestige + upgrade_levels + gem_levels; NOT budgets)
  useEffect(() => {
    const t = window.setTimeout(() => {
      const payload: SavedStateV1 = {
        prestige: ui.prestige,
        upgrade_levels: {
          "1": ui.upgrades.levels[1].slice(),
          "2": ui.upgrades.levels[2].slice(),
          "3": ui.upgrades.levels[3].slice(),
          "4": ui.upgrades.levels[4].slice(),
        },
        gem_levels: ui.upgrades.gemLevels.slice(),
      };
      saveJson(STORAGE_KEY, payload);
    }, 250);
    return () => window.clearTimeout(t);
  }, [ui.prestige, ui.upgrades]);

  const totalPoints = useMemo(() => {
    return ([1, 2, 3, 4] as const).reduce((acc, tier) => acc + ui.upgrades.levels[tier].reduce((a, b) => a + b, 0), 0);
  }, [ui.upgrades]);

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
      setError("Please enter at least some currency.");
      return;
    }

    const prestige = clampInt(ui.prestige, 0, 999);

    // Prefer worker to keep UI responsive. Fallback to main-thread if worker fails.
    try {
      lastInitialRef.current = copyState(ui.upgrades);
      if (!workerRef.current) {
        workerRef.current = new Worker(new URL("../../workers/mc.worker.ts", import.meta.url), { type: "module" });
        workerRef.current.onmessage = (ev: MessageEvent<any>) => {
          const msg = ev.data;
          if (msg?.type === "progress") {
            setProgress(msg.payload);
            return;
          }
          if (msg?.type === "done") {
            setRunning(false);
            setProgress(null);
            setMcMeta(null);
            const r: MCOptimizationResult = msg.payload;
            setMcStats(r);
            setAppliedSinceLastOptimize(false);
            // Convert to OptimizationResult-ish view (like desktop does)
            setResult({
              upgrades: r.bestState,
              expectedWave: r.bestWave,
              expectedTime: r.bestTime,
              materialsSpent: r.materialsSpent,
              materialsRemaining: r.materialsRemaining,
              playerStats: r.playerStats,
              enemyStats: r.enemyStats,
              recommendations: [
                "Monte Carlo Optimization (guided MC)",
                `N=${ui.mcCandidates} candidates, ${ui.mcRunsPerCombo} runs/combo`,
                `Best Wave: ${r.bestWave.toFixed(1)}`,
                `Average Wave: ${(r.statistics.mean_wave ?? 0).toFixed(1)} ± ${(r.statistics.std_dev_wave ?? 0).toFixed(1)}`,
                `Wave Range: ${(r.statistics.min_wave ?? 0).toFixed(1)} - ${(r.statistics.max_wave ?? 0).toFixed(1)}`,
                `Median Wave: ${(r.statistics.median_wave ?? 0).toFixed(1)}`,
              ],
              breakpoints: [],
            });
            return;
          }
          if (msg?.type === "cancelled") {
            setRunning(false);
            setProgress(null);
            setMcMeta(null);
            return;
          }
          if (msg?.type === "error") {
            setRunning(false);
            setProgress(null);
            setMcMeta(null);
            setError(msg.payload?.message ?? "MC failed.");
            return;
          }
        };
      }

      setRunning(true);
      setMcMeta({ startedAt: Date.now(), totalSims: Math.max(1, clampInt(ui.mcCandidates, 1, 20000)) * Math.max(1, clampInt(ui.mcRunsPerCombo, 1, 500)) });
      workerRef.current.postMessage({
        type: "start",
        payload: {
          budget,
          prestige,
          initialState: ui.upgrades,
          numCandidates: Math.max(1, clampInt(ui.mcCandidates, 1, 20000)),
          runsPerCombo: Math.max(1, clampInt(ui.mcRunsPerCombo, 1, 500)),
          seedBase: null,
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
          eventRunsPerCombination: ui.mcRunsPerCombo,
          seedBase: null,
          progressCallback: (cur: number, total2: number, curWave: number, bestWave: number) => {
            if (cur % 25 === 0 || cur === total2) setProgress({ cur, total: total2, curWave, bestWave });
          },
        });
        setMcStats(r);
        setAppliedSinceLastOptimize(false);
        setResult({
          upgrades: r.bestState,
          expectedWave: r.bestWave,
          expectedTime: r.bestTime,
          materialsSpent: r.materialsSpent,
          materialsRemaining: r.materialsRemaining,
          playerStats: r.playerStats,
          enemyStats: r.enemyStats,
          recommendations: [
            "Monte Carlo Optimization (guided MC)",
            `N=${ui.mcCandidates} candidates, ${ui.mcRunsPerCombo} runs/combo`,
            `Best Wave: ${r.bestWave.toFixed(1)}`,
            `Average Wave: ${(r.statistics.mean_wave ?? 0).toFixed(1)} ± ${(r.statistics.std_dev_wave ?? 0).toFixed(1)}`,
            `Wave Range: ${(r.statistics.min_wave ?? 0).toFixed(1)} - ${(r.statistics.max_wave ?? 0).toFixed(1)}`,
            `Median Wave: ${(r.statistics.median_wave ?? 0).toFixed(1)}`,
          ],
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

  function onCancel() {
    if (workerRef.current) workerRef.current.postMessage({ type: "cancel" });
    setRunning(false);
    setProgress(null);
    setMcMeta(null);
  }

  function onResetUpgrades() {
    const next = copyState(ui.upgrades);
    next.levels[1].fill(0);
    next.levels[2].fill(0);
    next.levels[3].fill(0);
    next.levels[4].fill(0);
    setUi((s) => ({ ...s, upgrades: next }));
    setResult(null);
    setMcStats(null);
    setError(null);
  }

  function onAddPoints() {
    if (!result) return;
    // Apply recommended levels directly (same intent as "✨ Add Points!" in Tk GUI).
    setUi((s) => ({ ...s, upgrades: copyState(result.upgrades) }));
    setAppliedSinceLastOptimize(true);
  }

  return (
    <div className="container">
      <div className="header">
        <div>
          <h1 className="title">Event Budget Optimizer</h1>
          <p className="subtitle">Saves upgrades/prestige automatically in your browser (localStorage).</p>
        </div>
        <div className="badge">Budget Optimizer • Guided MC</div>
      </div>

      <div className="grid">
        <div className="panel">
          <div className="panelHeader">
            <h2 className="panelTitle">Current Upgrades</h2>
            <p className="panelHint">
              Total points: <span className="mono">{totalPoints}</span>
            </p>
          </div>

          <div className="form">
            <div className="row">
              <div className="label">
                <span>
                  Prestige
                  <Tooltip
                    content={{
                      title: "Prestige",
                      sections: [
                        { heading: "What it affects", lines: ["Unlocks upgrades and affects gem upgrade max levels."] },
                        { heading: "Saved", lines: ["This value is saved automatically (like the desktop tool)."] },
                      ],
                    }}
                  />
                </span>
                <span className="mono">{ui.prestige}</span>
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
                <div className="input" style={{ display: "flex", alignItems: "center", justifyContent: "center", fontWeight: 900 }}>
                  <span className="mono">{ui.prestige}</span>
                </div>
                <button
                  className="btn"
                  type="button"
                  onClick={() => setUi((s) => ({ ...s, prestige: clampInt(s.prestige + 1, 0, 999) }))}
                  disabled={ui.prestige >= 999}
                >
                  +
                </button>
              </div>
            </div>

            <div className="btnRow">
              <button className="btn btnSecondary" onClick={onResetUpgrades}>
                Reset upgrades
              </button>
              <Tooltip
                content={{
                  title: "Reset upgrades",
                  lines: ["Resets Tier 1–4 currency upgrades only. Prestige and gem upgrades are kept."],
                }}
              />
            </div>

            <div className="small">Tier max levels update automatically based on cap upgrades.</div>

            <div className="tierBlock">
              <div className="tierHead">
                <p className="tierTitle">
                  Gem upgrades
                  <Tooltip
                    content={{
                      title: "Gem upgrades",
                      sections: [
                        { heading: "What they are", lines: ["Permanent upgrades (not bought with event currency)."] },
                        { heading: "Limits", lines: ["Max level depends on prestige (matches the desktop rules)."] },
                      ],
                    }}
                  />
                </p>
                <p className="small">Permanent (not event currency)</p>
              </div>
              <div className="small">
                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8 }}>
                  {ui.upgrades.gemLevels.map((lvl, idx) => {
                    const max = getGemMaxLevel(ui.prestige, idx);
                    const icon = gemUpgradeIconFilename(idx);
                    return (
                      <div key={idx} style={{ border: "1px solid rgba(255,255,255,0.12)", borderRadius: 10, padding: 10 }}>
                        <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
                          <Sprite path={icon ? `sprites/event/${icon}` : null} alt={GEM_UPGRADE_NAMES[idx] ?? `Gem ${idx + 1}`} label={icon ?? ""} />
                          <div className="mono">{GEM_UPGRADE_NAMES[idx] ?? `Gem ${idx + 1}`}</div>
                        </div>
                        <div className="small">
                          lvl <span className="mono">{lvl}</span> / <span className="mono">{max}</span>
                        </div>
                        <div className="btnRow" style={{ marginTop: 8 }}>
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
                      const max = getMaxLevelWithCaps(t, idx, tempState);
                      const baseCost = COSTS[t][idx];
                      const nextCost = Math.round(baseCost * 1.25 ** lvl);
                      const icon = upgradeIconFilename(tier, idx);
                      const rowClass = unlocked ? "" : "lockedRow";
                      return (
                        <div
                          key={idx}
                          className={rowClass}
                          style={{
                            display: "grid",
                            gridTemplateColumns: "1fr auto auto",
                            gap: 8,
                            alignItems: "center",
                            marginBottom: 6,
                            border: "1px solid rgba(15,23,42,0.08)",
                            borderRadius: 8,
                            padding: "6px 8px",
                            transition: "background-color 120ms ease",
                          }}
                        >
                          <div>
                            <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
                              <Sprite path={icon ? `sprites/event/${icon}` : null} alt={UPGRADE_SHORT_NAMES[t][idx]} label={icon ?? ""} />
                              <div className="mono">{UPGRADE_SHORT_NAMES[t][idx]}</div>
                            </div>
                            <div className="small">
                              {unlocked ? (
                                <>
                                  lvl{" "}
                                  <span className="heatNum mono" style={heatStyle(lvl)}>
                                    {lvl}
                                  </span>{" "}
                                  / <span className="mono">{max}</span> • next cost <span className="mono">{formatInt(nextCost)}</span>
                                </>
                              ) : (
                                <>
                                  <span className="pillLocked">LOCKED</span> <span className="lockedText">until prestige {PRESTIGE_UNLOCKED[t][idx]}</span>
                                </>
                              )}
                            </div>
                          </div>
                          <button
                            className="btn btnSecondary"
                            disabled={!unlocked || lvl <= 0}
                            onClick={() => {
                              setUi((s) => {
                                const next = copyState(s.upgrades);
                                if (next.levels[t][idx] > 0) next.levels[t][idx] -= 1;
                                return { ...s, upgrades: next };
                              });
                            }}
                          >
                            −
                          </button>
                          <button
                            className="btn"
                            disabled={!unlocked || lvl >= max}
                            onClick={() => {
                              setUi((s) => {
                                const next = copyState(s.upgrades);
                                const max2 = getMaxLevelWithCaps(t, idx, next);
                                if (next.levels[t][idx] < max2) next.levels[t][idx] += 1;
                                return { ...s, upgrades: next };
                              });
                            }}
                          >
                            +
                          </button>
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
                  step={1}
                  disabled={!ui.devOnlyMcTuning}
                  value={ui.mcRunsPerCombo}
                  onChange={(e) => setUi((s) => ({ ...s, mcRunsPerCombo: clampInt(Number(e.target.value), 1, 500) }))}
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
          </div>
        </div>

        <div className="rightColumn">
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
                    <Sprite path={icon ? `sprites/event/${icon}` : null} alt={`Currency ${tier}`} className="iconSmall" label={icon ?? ""} />
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

            <div className="btnRow" style={{ marginTop: 0 }}>
              <button className="btn" onClick={onOptimizeGuidedMc} disabled={running}>
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
                  <kbd>Estimated wave</kbd>
                  <div className="mono">{result.expectedWave.toFixed(1)}</div>
                  <kbd>Estimated time</kbd>
                  <div className="mono">{formatTime(result.expectedTime)}</div>
                  <kbd>Final ATK</kbd>
                  <div className="mono">{formatInt(result.playerStats.atk)}</div>
                  <kbd>Final HP</kbd>
                  <div className="mono">{formatInt(result.playerStats.health)}</div>
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
                          {picked.map(({ idx, add }) => (
                            <li key={idx}>
                              <span className="mono">{UPGRADE_SHORT_NAMES[tier][idx]}</span> + <span className="mono">{add}</span>
                            </li>
                          ))}
                        </ul>
                      ) : (
                        <div className="small">No upgrades purchased in this tier.</div>
                      )}
                    </div>
                  );
                })}

                <div className="sectionTitle">Recommendations</div>
                <ul className="list">
                  {result.recommendations.map((line, i) => (
                    <li key={i}>{line}</li>
                  ))}
                </ul>

                {mcStats ? (
                  <>
                    <div className="sectionTitle">MC statistics</div>
                    <div className="kv">
                      <kbd>Mean wave</kbd>
                      <div className="mono">{(mcStats.statistics.mean_wave ?? 0).toFixed(2)}</div>
                      <kbd>Std dev wave</kbd>
                      <div className="mono">{(mcStats.statistics.std_dev_wave ?? 0).toFixed(2)}</div>
                      <kbd>Median wave</kbd>
                      <div className="mono">{(mcStats.statistics.median_wave ?? 0).toFixed(2)}</div>
                      <kbd>Wave range</kbd>
                      <div className="mono">
                        {(mcStats.statistics.min_wave ?? 0).toFixed(2)} - {(mcStats.statistics.max_wave ?? 0).toFixed(2)}
                      </div>
                      <kbd>Mean time</kbd>
                      <div className="mono">{(mcStats.statistics.mean_time ?? 0).toFixed(2)}s</div>
                      <kbd>Std dev time</kbd>
                      <div className="mono">{(mcStats.statistics.std_dev_time ?? 0).toFixed(2)}s</div>
                    </div>
                  </>
                ) : null}
              </>
            ) : (
              <div className="small">Tip: your inputs are auto-saved in this browser.</div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

