import { useEffect, useMemo, useState } from "react";
import "./stargazing.css";
import { Tooltip } from "../../components/Tooltip";
import { assetUrl } from "../../lib/assets";
import { loadJson, saveJson } from "../../lib/storage";
import { StargazingCalculator, type PlayerStats } from "../../lib/stargazing/calculator";

type UiStats = {
  floor_clears_per_minute: number;
  star_spawn_rate_mult: number;
  auto_catch_chance: number; // %
  double_star_chance: number; // %
  triple_star_chance: number; // %
  super_star_spawn_rate_mult: number;
  triple_super_star_chance: number; // %
  super_star_10x_chance: number; // %
  star_supernova_chance: number; // %
  star_supernova_mult: number;
  star_supergiant_chance: number; // %
  star_supergiant_mult: number;
  star_radiant_chance: number; // %
  star_radiant_mult: number;
  super_star_supernova_chance: number; // %
  super_star_supernova_mult: number;
  super_star_supergiant_chance: number; // %
  super_star_supergiant_mult: number;
  super_star_radiant_chance: number; // %
  super_star_radiant_mult: number;
  all_star_mult: number;
  novagiant_combo_mult: number;
};

type SavedStateV1 = {
  stats: Partial<UiStats>;
  ctrl_f_stars_enabled: boolean;
};

const STORAGE_KEY = "obeliskfarm:web:stargazing_save.json:v1";

function clamp(n: number, min: number, max: number): number {
  if (!Number.isFinite(n)) return min;
  return Math.max(min, Math.min(max, n));
}

function parseNumber(raw: string): number | null {
  const cleaned = raw.trim().replaceAll(",", ".").replaceAll(" ", "");
  if (!cleaned) return null;
  const n = Number(cleaned);
  return Number.isFinite(n) ? n : null;
}

function endsWithDecimalSeparator(raw: string): boolean {
  const t = raw.trim();
  return t.endsWith(".") || t.endsWith(",");
}

function fmt4(n: number): string {
  if (!Number.isFinite(n)) return "—";
  return n.toFixed(4);
}

function Sprite(props: { paths: string[]; alt: string; className?: string; label?: string }) {
  const { paths, alt, className, label } = props;
  const [idx, setIdx] = useState(0);
  const path = paths[idx] ?? null;
  if (!path) return <span className="iconPlaceholder" title={`Missing sprite: ${label ?? alt}`}>?</span>;
  return (
    <img
      className={className ?? "icon"}
      src={assetUrl(path)}
      alt={alt}
      title={alt}
      onError={() => setIdx((s) => (s + 1 < paths.length ? s + 1 : s))}
    />
  );
}

function Stepper(props: {
  label: React.ReactNode;
  iconEmoji?: string;
  value: number;
  onChange: (next: number) => void;
  step?: number;
  min?: number;
  max?: number;
  inputMode?: "decimal" | "numeric";
  decimals?: number;
}) {
  const { label, iconEmoji, value, onChange, step = 1, min = -Infinity, max = Infinity, inputMode = "decimal", decimals = 2 } = props;
  const [raw, setRaw] = useState<string>(Number.isFinite(value) ? String(value) : "");

  // Keep input in sync when value changes via +/- buttons or external state updates.
  useEffect(() => {
    setRaw(Number.isFinite(value) ? String(value) : "");
  }, [value]);

  function commitFromRaw(nextRaw: string) {
    const trimmed = nextRaw.trim();
    // If user clears the input, treat it as 0 (consistent & predictable).
    if (!trimmed) {
      const v0 = clamp(0, min, max);
      onChange(v0);
      setRaw(String(v0));
      return;
    }
    const parsed = parseNumber(nextRaw);
    if (parsed === null) {
      // Revert to last valid value.
      setRaw(Number.isFinite(value) ? String(value) : "");
      return;
    }
    const v = clamp(parsed, min, max);
    onChange(v);
    setRaw(String(v));
  }

  return (
    <div className="sgRow">
      <div className="sgLabel">
        <div className="sgLabelLeft">
          {iconEmoji ? (
            <span className="navEmoji" aria-hidden="true" style={{ width: 18, fontSize: 14 }}>
              {iconEmoji}
            </span>
          ) : null}
          <span className="sgLabelName">{label}</span>
        </div>
        <span className="mono">{Number.isFinite(value) ? value.toFixed(decimals) : "—"}</span>
      </div>
      <div className="sgStepper">
        <button
          className="btn btnSecondary sgBtn"
          type="button"
          onClick={() => {
            const v = clamp(value - step, min, max);
            onChange(v);
            setRaw(String(v));
          }}
        >
          −
        </button>
        <input
          className="input"
          inputMode={inputMode}
          value={raw}
          onChange={(e) => {
            const nextRaw = e.target.value;
            setRaw(nextRaw);
            // Let the user type "1." / "0," without immediately collapsing it to "1".
            if (endsWithDecimalSeparator(nextRaw)) return;
            const parsed = parseNumber(nextRaw);
            if (parsed === null) return;
            onChange(clamp(parsed, min, max));
          }}
          onBlur={() => commitFromRaw(raw)}
          onKeyDown={(e) => {
            if (e.key === "Enter") {
              e.currentTarget.blur();
            }
          }}
        />
        <button
          className="btn sgBtn"
          type="button"
          onClick={() => {
            const v = clamp(value + step, min, max);
            onChange(v);
            setRaw(String(v));
          }}
        >
          +
        </button>
      </div>
    </div>
  );
}

function defaultUiStats(): UiStats {
  // Desktop defaults (`StargazingWindow.reset_to_defaults()`):
  return {
    floor_clears_per_minute: 2.0, // 120/hour = 2/min
    star_spawn_rate_mult: 1.0,
    auto_catch_chance: 0.0,
    double_star_chance: 0.0,
    triple_star_chance: 0.0,
    super_star_spawn_rate_mult: 1.0,
    triple_super_star_chance: 0.0,
    super_star_10x_chance: 0.0,
    star_supernova_chance: 0.0,
    star_supernova_mult: 10.0,
    star_supergiant_chance: 0.0,
    star_supergiant_mult: 3.0,
    star_radiant_chance: 0.0,
    star_radiant_mult: 10.0,
    super_star_supernova_chance: 0.0,
    super_star_supernova_mult: 10.0,
    super_star_supergiant_chance: 0.0,
    super_star_supergiant_mult: 3.0,
    super_star_radiant_chance: 0.0,
    super_star_radiant_mult: 10.0,
    all_star_mult: 1.0,
    novagiant_combo_mult: 1.0,
  };
}

export function Stargazing() {
  const initial = useMemo(() => {
    const base = defaultUiStats();
    const saved = loadJson<SavedStateV1>(STORAGE_KEY);
    const merged: UiStats = { ...base, ...(saved?.stats ?? {}) };
    const ctrl_f_stars_enabled = saved?.ctrl_f_stars_enabled ?? false;
    return { stats: merged, ctrl_f_stars_enabled };
  }, []);

  const [ui, setUi] = useState<UiStats>(initial.stats);
  const [ctrlF, setCtrlF] = useState<boolean>(initial.ctrl_f_stars_enabled);

  // autosave (matches other web modules; close to desktop intent)
  useEffect(() => {
    const t = window.setTimeout(() => {
      const payload: SavedStateV1 = { stats: ui, ctrl_f_stars_enabled: ctrlF };
      saveJson(STORAGE_KEY, payload);
    }, 250);
    return () => window.clearTimeout(t);
  }, [ui, ctrlF]);

  const stats = useMemo<PlayerStats>(() => {
    const floor_clears_per_hour = clamp(ui.floor_clears_per_minute, 0, 1_000_000) * 60.0;
    return {
      floor_clears_per_hour,
      star_spawn_rate_mult: clamp(ui.star_spawn_rate_mult, 0, 1_000_000),
      auto_catch_chance: clamp(ui.auto_catch_chance, 0, 100) / 100,
      double_star_chance: clamp(ui.double_star_chance, 0, 100) / 100,
      triple_star_chance: clamp(ui.triple_star_chance, 0, 100) / 100,
      super_star_spawn_rate_mult: clamp(ui.super_star_spawn_rate_mult, 0, 1_000_000),
      triple_super_star_chance: clamp(ui.triple_super_star_chance, 0, 100) / 100,
      super_star_10x_chance: clamp(ui.super_star_10x_chance, 0, 100) / 100,
      star_supernova_chance: clamp(ui.star_supernova_chance, 0, 100) / 100,
      star_supernova_mult: clamp(ui.star_supernova_mult, 0, 1_000_000),
      star_supergiant_chance: clamp(ui.star_supergiant_chance, 0, 100) / 100,
      star_supergiant_mult: clamp(ui.star_supergiant_mult, 0, 1_000_000),
      star_radiant_chance: clamp(ui.star_radiant_chance, 0, 100) / 100,
      star_radiant_mult: clamp(ui.star_radiant_mult, 0, 1_000_000),
      super_star_supernova_chance: clamp(ui.super_star_supernova_chance, 0, 100) / 100,
      super_star_supernova_mult: clamp(ui.super_star_supernova_mult, 0, 1_000_000),
      super_star_supergiant_chance: clamp(ui.super_star_supergiant_chance, 0, 100) / 100,
      super_star_supergiant_mult: clamp(ui.super_star_supergiant_mult, 0, 1_000_000),
      super_star_radiant_chance: clamp(ui.super_star_radiant_chance, 0, 100) / 100,
      super_star_radiant_mult: clamp(ui.super_star_radiant_mult, 0, 1_000_000),
      all_star_mult: clamp(ui.all_star_mult, 0, 1_000_000),
      novagiant_combo_mult: clamp(ui.novagiant_combo_mult, 0, 1_000_000),
      ctrl_f_stars_enabled: ctrlF,
    };
  }, [ui, ctrlF]);

  const summary = useMemo(() => {
    const calc = new StargazingCalculator(stats);
    return calc.get_summary();
  }, [stats]);

  const onlineInfo = useMemo(
    () => ({
      title: "Online Mode",
      sections: [
        { heading: "Meaning", lines: ["Online means you manually catch all stars and follow them through all floors."] },
        { heading: "Auto-catch", lines: ["This corresponds to 100% catch rate (auto-catch is not applied)."] },
      ],
    }),
    [],
  );

  const ctrlFInfo = useMemo(
    () => ({
      title: "CTRL+F Stars Skill",
      sections: [
        { heading: "Effect", lines: ["Multiplies offline gains by 5x for both Stars and Super Stars."] },
        {
          heading: "Mechanics",
          lines: [
            "Each star type spawns on 5 different floors.",
            "Without CTRL+F: you catch the star on 1 floor → offline = auto_catch × online × 0.2",
            "With CTRL+F: you follow the star through all 5 floors → offline = auto_catch × online × 1.0",
          ],
        },
      ],
    }),
    [],
  );

  return (
    <div className="container">
      <div className="header">
        <div>
          <h1 className="title">
            <span style={{ display: "inline-flex", gap: 10, alignItems: "center" }}>
              <Sprite
                paths={["sprites/stargazing/stargazing.png", "sprites/stargazing/stargazing.svg"]}
                alt="Stargazing"
                className="sgHeaderIcon"
                label="sprites/stargazing/stargazing.*"
              />
              <span>Stargazing Calculator</span>
            </span>
          </h1>
          <p className="subtitle">Web port of the desktop Stargazing module (same formulas, autosaves in this browser).</p>
        </div>
        <div className="badge">Stars • Super Stars • CTRL+F</div>
      </div>

      <div className="grid">
        <div className="panel">
          <div className="panelHeader">
            <h2 className="panelTitle">Your stats (from game)</h2>
            <p className="panelHint">Percent inputs are in %.</p>
          </div>

          <div className="sgGrid">
            <div className="sgSection tierHeader2">
              <div className="sgSectionHeader">
                <div className="sgSectionTitle">
                  <span className="mono">Basic Stats</span>
                </div>
              </div>
              <div className="sgRows">
                <Stepper
                  iconEmoji="🏃"
                  label="Floor Clears / min"
                  value={ui.floor_clears_per_minute}
                  onChange={(v) => setUi((s) => ({ ...s, floor_clears_per_minute: v }))}
                  step={0.1}
                  min={0}
                  max={10_000}
                  decimals={2}
                />
                <Stepper
                  iconEmoji="⭐"
                  label="Star Spawn Rate Multiplier (x)"
                  value={ui.star_spawn_rate_mult}
                  onChange={(v) => setUi((s) => ({ ...s, star_spawn_rate_mult: v }))}
                  step={0.05}
                  min={0}
                  max={10_000}
                  decimals={2}
                />
                <Stepper
                  iconEmoji="🧲"
                  label="Auto-Catch Chance (%)"
                  value={ui.auto_catch_chance}
                  onChange={(v) => setUi((s) => ({ ...s, auto_catch_chance: v }))}
                  step={0.5}
                  min={0}
                  max={100}
                  decimals={2}
                />
              </div>
            </div>

            <div className="sgSection tierHeader1">
              <div className="sgSectionHeader">
                <div className="sgSectionTitle">
                  <span className="mono">⭐ Star Multipliers</span>
                </div>
              </div>
              <div className="sgRows">
                <Stepper
                  iconEmoji="➕"
                  label="Double Star Chance (%)"
                  value={ui.double_star_chance}
                  onChange={(v) => setUi((s) => ({ ...s, double_star_chance: v }))}
                  step={0.5}
                  min={0}
                  max={100}
                  decimals={2}
                />
                <Stepper
                  iconEmoji="➕"
                  label="Triple Star Chance (%)"
                  value={ui.triple_star_chance}
                  onChange={(v) => setUi((s) => ({ ...s, triple_star_chance: v }))}
                  step={0.5}
                  min={0}
                  max={100}
                  decimals={2}
                />

                <div className="row2">
                  <Stepper
                    iconEmoji="💥"
                    label="Star Supernova Chance (%)"
                    value={ui.star_supernova_chance}
                    onChange={(v) => setUi((s) => ({ ...s, star_supernova_chance: v }))}
                    step={0.5}
                    min={0}
                    max={100}
                    decimals={2}
                  />
                  <Stepper
                    iconEmoji="✖️"
                    label="Supernova Multiplier (x)"
                    value={ui.star_supernova_mult}
                    onChange={(v) => setUi((s) => ({ ...s, star_supernova_mult: v }))}
                    step={0.5}
                    min={0}
                    max={10_000}
                    decimals={2}
                  />
                </div>

                <div className="row2">
                  <Stepper
                    iconEmoji="🪐"
                    label="Star Supergiant Chance (%)"
                    value={ui.star_supergiant_chance}
                    onChange={(v) => setUi((s) => ({ ...s, star_supergiant_chance: v }))}
                    step={0.5}
                    min={0}
                    max={100}
                    decimals={2}
                  />
                  <Stepper
                    iconEmoji="✖️"
                    label="Supergiant Multiplier (x)"
                    value={ui.star_supergiant_mult}
                    onChange={(v) => setUi((s) => ({ ...s, star_supergiant_mult: v }))}
                    step={0.5}
                    min={0}
                    max={10_000}
                    decimals={2}
                  />
                </div>

                <div className="row2">
                  <Stepper
                    iconEmoji="✨"
                    label="Star Radiant Chance (%)"
                    value={ui.star_radiant_chance}
                    onChange={(v) => setUi((s) => ({ ...s, star_radiant_chance: v }))}
                    step={0.5}
                    min={0}
                    max={100}
                    decimals={2}
                  />
                  <Stepper
                    iconEmoji="✖️"
                    label="Radiant Multiplier (x)"
                    value={ui.star_radiant_mult}
                    onChange={(v) => setUi((s) => ({ ...s, star_radiant_mult: v }))}
                    step={0.5}
                    min={0}
                    max={10_000}
                    decimals={2}
                  />
                </div>
              </div>
            </div>

            <div className="sgSection tierHeader3">
              <div className="sgSectionHeader">
                <div className="sgSectionTitle">
                  <span className="mono">🌟 Super Star Stats</span>
                </div>
              </div>
              <div className="sgRows">
                <Stepper
                  iconEmoji="🌟"
                  label="Super Star Spawn Rate Multiplier (x)"
                  value={ui.super_star_spawn_rate_mult}
                  onChange={(v) => setUi((s) => ({ ...s, super_star_spawn_rate_mult: v }))}
                  step={0.05}
                  min={0}
                  max={10_000}
                  decimals={2}
                />
                <Stepper
                  iconEmoji="➕"
                  label="Triple Super Star Chance (%)"
                  value={ui.triple_super_star_chance}
                  onChange={(v) => setUi((s) => ({ ...s, triple_super_star_chance: v }))}
                  step={0.5}
                  min={0}
                  max={100}
                  decimals={2}
                />
                <Stepper
                  iconEmoji="🔟"
                  label="Super Star 10× Chance (%)"
                  value={ui.super_star_10x_chance}
                  onChange={(v) => setUi((s) => ({ ...s, super_star_10x_chance: v }))}
                  step={0.5}
                  min={0}
                  max={100}
                  decimals={2}
                />

                <div className="row2">
                  <Stepper
                    iconEmoji="💥"
                    label="Super Star Supernova Chance (%)"
                    value={ui.super_star_supernova_chance}
                    onChange={(v) => setUi((s) => ({ ...s, super_star_supernova_chance: v }))}
                    step={0.5}
                    min={0}
                    max={100}
                    decimals={2}
                  />
                  <Stepper
                    iconEmoji="✖️"
                    label="SS Nova Multiplier (x)"
                    value={ui.super_star_supernova_mult}
                    onChange={(v) => setUi((s) => ({ ...s, super_star_supernova_mult: v }))}
                    step={0.5}
                    min={0}
                    max={10_000}
                    decimals={2}
                  />
                </div>

                <div className="row2">
                  <Stepper
                    iconEmoji="🪐"
                    label="Super Star Supergiant Chance (%)"
                    value={ui.super_star_supergiant_chance}
                    onChange={(v) => setUi((s) => ({ ...s, super_star_supergiant_chance: v }))}
                    step={0.5}
                    min={0}
                    max={100}
                    decimals={2}
                  />
                  <Stepper
                    iconEmoji="✖️"
                    label="SS Giant Multiplier (x)"
                    value={ui.super_star_supergiant_mult}
                    onChange={(v) => setUi((s) => ({ ...s, super_star_supergiant_mult: v }))}
                    step={0.5}
                    min={0}
                    max={10_000}
                    decimals={2}
                  />
                </div>

                <div className="row2">
                  <Stepper
                    iconEmoji="✨"
                    label="Super Star Radiant Chance (%)"
                    value={ui.super_star_radiant_chance}
                    onChange={(v) => setUi((s) => ({ ...s, super_star_radiant_chance: v }))}
                    step={0.5}
                    min={0}
                    max={100}
                    decimals={2}
                  />
                  <Stepper
                    iconEmoji="✖️"
                    label="SS Radiant Multiplier (x)"
                    value={ui.super_star_radiant_mult}
                    onChange={(v) => setUi((s) => ({ ...s, super_star_radiant_mult: v }))}
                    step={0.5}
                    min={0}
                    max={10_000}
                    decimals={2}
                  />
                </div>
              </div>
            </div>

            <div className="sgSection tierHeader4">
              <div className="sgSectionHeader">
                <div className="sgSectionTitle">
                  <span className="mono">Global Multipliers</span>
                </div>
              </div>
              <div className="sgRows">
                <Stepper
                  iconEmoji="🌌"
                  label="All Star Multiplier (x)"
                  value={ui.all_star_mult}
                  onChange={(v) => setUi((s) => ({ ...s, all_star_mult: v }))}
                  step={0.05}
                  min={0}
                  max={10_000}
                  decimals={2}
                />
                <Stepper
                  iconEmoji="🤝"
                  label="Novagiant Combo Multiplier (x)"
                  value={ui.novagiant_combo_mult}
                  onChange={(v) => setUi((s) => ({ ...s, novagiant_combo_mult: v }))}
                  step={0.05}
                  min={0}
                  max={10_000}
                  decimals={2}
                />
              </div>
            </div>

            <div className="sgSection" style={{ background: "rgba(227,242,253,0.55)" }}>
              <div className="sgSectionHeader">
                <div className="sgSectionTitle">
                  <span className="mono">CTRL+F Stars</span>
                  <Tooltip content={ctrlFInfo} />
                </div>
              </div>
              <label className="toggle">
                <input type="checkbox" checked={ctrlF} onChange={(e) => setCtrlF(e.target.checked)} />
                Enabled (offline gains ×5)
              </label>
            </div>

            <div className="btnRow">
              <button className="btn btnSecondary" type="button" onClick={() => setUi(defaultUiStats())}>
                Reset to defaults
              </button>
              <Tooltip content={{ title: "Reset", lines: ["Restores the desktop default values for all inputs."] }} />
            </div>
          </div>
        </div>

        <div className="rightColumn">
          <div className="panel panelResults">
            <div className="panelHeader">
              <h2 className="panelTitle">Results</h2>
              <p className="panelHint">Updates instantly.</p>
            </div>

            <div className="kv" style={{ background: "rgba(255,255,255,0.92)" }}>
              <kbd>
                ⭐ Stars/hour (Online)
                <Tooltip content={onlineInfo} />
              </kbd>
              <div className="mono sgResultValueBlue">{fmt4(summary.stars_per_hour_online)}</div>
              <kbd>⭐ Stars/hour (Offline)</kbd>
              <div className="mono sgResultValueBlue">{fmt4(summary.stars_per_hour_offline)}</div>
              <kbd>
                🌟 Super Stars/hour (Online)
                <Tooltip content={onlineInfo} />
              </kbd>
              <div className="mono sgResultValueOrange">{fmt4(summary.super_stars_per_hour_online)}</div>
              <kbd>🌟 Super Stars/hour (Offline)</kbd>
              <div className="mono sgResultValueOrange">{fmt4(summary.super_stars_per_hour_offline)}</div>
            </div>

            <div className="small" style={{ marginTop: 10 }}>
              Spawn events/hour: <span className="mono">{fmt4(summary.star_spawn_rate_per_hour)}</span> • Super-star events/hour:{" "}
              <span className="mono">{fmt4(summary.super_star_spawn_rate_per_hour)}</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

