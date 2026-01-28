import { useEffect, useMemo, useState } from "react";
import "./gemev.css";
import { Tooltip } from "../../components/Tooltip";
import { assetUrl } from "../../lib/assets";
import { loadJson, saveJson } from "../../lib/storage";
import {
  calculateEvBreakdown,
  calculateGiftEvBreakdown,
  calculateGiftEvPerGift,
  calculateTotalEvPerHour,
  defaultGameParameters,
  type GameParameters,
} from "../../lib/gemev/freebieEv";
import { ContribBarChart } from "./ContribBarChart";

type SavedStateV1 = {
  params: Partial<GameParameters>;
  stonks_enabled: boolean;
};

const STORAGE_KEY = "obeliskfarm:web:gemev_save.json:v1";

function clampInt(n: number, min: number, max: number): number {
  if (!Number.isFinite(n)) return min;
  return Math.max(min, Math.min(max, Math.trunc(n)));
}

function clamp(n: number, min: number, max: number): number {
  if (!Number.isFinite(n)) return min;
  return Math.max(min, Math.min(max, n));
}

function parseNumber(raw: string): number {
  const cleaned = raw.trim().replaceAll(",", ".").replaceAll(" ", "");
  if (!cleaned) return 0;
  const n = Number(cleaned);
  return Number.isFinite(n) ? n : 0;
}

function fmt1(n: number): string {
  if (!Number.isFinite(n)) return "—";
  return n.toFixed(1);
}

function fmtPct(n: number, total: number): string {
  if (!Number.isFinite(n) || !Number.isFinite(total) || total <= 0) return "0.0%";
  return `${((n / total) * 100).toFixed(1)}%`;
}

function Sprite(props: { path: string | null; alt: string; className?: string; label?: string }) {
  const { path, alt, className, label } = props;
  const [ok, setOk] = useState(true);
  if (!path || !ok) return <span className="iconPlaceholder" title={`Missing sprite: ${label ?? alt}`}>?</span>;
  return <img className={className ?? "icon"} src={assetUrl(path)} alt={alt} onError={() => setOk(false)} title={alt} />;
}

function Stepper(props: {
  label: React.ReactNode;
  value: number;
  onChange: (next: number) => void;
  step?: number;
  min?: number;
  max?: number;
  inputMode?: "decimal" | "numeric";
  decimals?: number;
}) {
  const { label, value, onChange, step = 1, min = -Infinity, max = Infinity, inputMode = "decimal", decimals = 2 } = props;
  const shown = Number.isFinite(value) ? String(value) : "";
  return (
    <div className="gemEvRow">
      <div className="label">
        <span>{label}</span>
        <span className="mono">{Number.isFinite(value) ? value.toFixed(decimals) : "—"}</span>
      </div>
      <div className="gemEvStepper">
        <button className="btn btnSecondary gemEvStepBtn" type="button" onClick={() => onChange(clamp(value - step, min, max))}>
          −
        </button>
        <input
          className="input gemEvInput"
          inputMode={inputMode}
          value={shown}
          onChange={(e) => {
            const n = parseNumber(e.target.value);
            onChange(clamp(n, min, max));
          }}
        />
        <button className="btn gemEvStepBtn" type="button" onClick={() => onChange(clamp(value + step, min, max))}>
          +
        </button>
      </div>
    </div>
  );
}

function CardToggles(props: { value: number; onChange: (lvl: number) => void }) {
  const { value, onChange } = props;
  const cur = clampInt(value, 0, 3);
  const mk = (lvl: 1 | 2 | 3, label: string) => (
    <button
      type="button"
      className={`btn btnSecondary gemEvCardBtn ${cur === lvl ? "cardBtnActive" : ""}`}
      onClick={() => onChange(cur === lvl ? 0 : lvl)}
    >
      {label} {cur === lvl ? "✓" : ""}
    </button>
  );
  return (
    <div className="gemEvCardRow">
      <span className="small">Recharge:</span>
      {mk(1, "Card")}
      {mk(2, "Gild")}
      {mk(3, "Poly")}
    </div>
  );
}

export function GemEv() {
  const initial = useMemo(() => {
    const base = defaultGameParameters();
    const saved = loadJson<SavedStateV1>(STORAGE_KEY);
    const merged: GameParameters = { ...base, ...(saved?.params ?? {}) };
    const stonks_enabled = saved?.stonks_enabled ?? true;
    return { params: merged, stonks_enabled };
  }, []);

  const [params, setParams] = useState<GameParameters>(initial.params);
  const [stonksEnabled, setStonksEnabled] = useState<boolean>(initial.stonks_enabled);
  const [chartOpen, setChartOpen] = useState(false);

  // autosave
  useEffect(() => {
    const t = window.setTimeout(() => {
      const payload: SavedStateV1 = { params, stonks_enabled: stonksEnabled };
      saveJson(STORAGE_KEY, payload);
    }, 250);
    return () => window.clearTimeout(t);
  }, [params, stonksEnabled]);

  // ESC closes the chart modal (matches other modules' modal behavior)
  useEffect(() => {
    function onKeyDown(ev: KeyboardEvent) {
      if (ev.key === "Escape") setChartOpen(false);
    }
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, []);

  // Apply desktop semantics: stonks is a checkbox and uses fixed chance/bonus when enabled.
  // Also keep "fixed" desktop constants (they exist in params but are not editable in the UI).
  const effectiveParams = useMemo<GameParameters>(() => {
    const p: GameParameters = { ...params };

    // Stonks semantics
    p.stonks_chance = stonksEnabled ? 0.01 : 0.0;
    p.stonks_bonus_gems = 200.0;

    // Fixed desktop constants
    p.founder_gems_base = 10.0;
    p.founder_gems_chance = 0.01;
    p.founder_speed_multiplier = 2.0;
    p.founder_speed_duration_minutes = 5.0;
    p.battery_bomb_charges_per_charge = 2.0;
    p.battery_bomb_cap_increase_chance = 0.001;
    p.founder_bomb_charges_per_drop = 2.0;

    // Clamp common percent inputs
    p.freebie_claim_percentage = clamp(p.freebie_claim_percentage, 0, 100);
    p.skill_shard_chance = clamp(p.skill_shard_chance, 0, 1);
    p.jackpot_chance = clamp(p.jackpot_chance, 0, 1);
    p.instant_refresh_chance = clamp(p.instant_refresh_chance, 0, 1);
    p.free_bomb_chance = clamp(p.free_bomb_chance, 0, 0.99);
    p.gem_bomb_gem_chance = clamp(p.gem_bomb_gem_chance, 0, 1);
    p.cherry_bomb_triple_charge_chance = clamp(p.cherry_bomb_triple_charge_chance, 0, 1);
    p.d20_bomb_refill_chance = clamp(p.d20_bomb_refill_chance, 0, 1);
    p.founder_bomb_speed_chance = clamp(p.founder_bomb_speed_chance, 0, 1);

    // Clamp "levels"
    p.vip_lounge_level = clampInt(p.vip_lounge_level, 1, 7);
    p.jackpot_rolls = clampInt(p.jackpot_rolls, 1, 999);
    p.total_bomb_types = clampInt(p.total_bomb_types, 2, 64);
    p.d20_bomb_charges_distributed = clampInt(p.d20_bomb_charges_distributed, 0, 9999);
    p.obelisk_level = clampInt(p.obelisk_level, 0, 999);

    // Recharge card levels
    p.gem_bomb_recharge_card_level = clampInt(p.gem_bomb_recharge_card_level, 0, 3);
    p.cherry_bomb_recharge_card_level = clampInt(p.cherry_bomb_recharge_card_level, 0, 3);
    p.battery_bomb_recharge_card_level = clampInt(p.battery_bomb_recharge_card_level, 0, 3);
    p.d20_bomb_recharge_card_level = clampInt(p.d20_bomb_recharge_card_level, 0, 3);
    p.founder_bomb_recharge_card_level = clampInt(p.founder_bomb_recharge_card_level, 0, 3);

    // Ensure positive time values
    p.freebie_timer_minutes = clamp(p.freebie_timer_minutes, 0.1, 10_000);
    p.gem_bomb_recharge_seconds = clamp(p.gem_bomb_recharge_seconds, 0.1, 10_000);
    p.cherry_bomb_recharge_seconds = clamp(p.cherry_bomb_recharge_seconds, 0.1, 10_000);
    p.battery_bomb_recharge_seconds = clamp(p.battery_bomb_recharge_seconds, 0.1, 10_000);
    p.d20_bomb_recharge_seconds = clamp(p.d20_bomb_recharge_seconds, 0.1, 10_000);
    p.founder_bomb_interval_seconds = clamp(p.founder_bomb_interval_seconds, 0.1, 10_000);
    p.founder_bomb_speed_multiplier = clamp(p.founder_bomb_speed_multiplier, 0.1, 100);
    p.founder_bomb_speed_duration_seconds = clamp(p.founder_bomb_speed_duration_seconds, 0, 10_000);

    return p;
  }, [params, stonksEnabled]);

  const ev = useMemo(() => calculateTotalEvPerHour(effectiveParams), [effectiveParams]);
  const breakdown = useMemo(() => calculateEvBreakdown(effectiveParams), [effectiveParams]);
  const giftEv = useMemo(() => calculateGiftEvPerGift(effectiveParams), [effectiveParams]);
  const giftBreakdown = useMemo(() => calculateGiftEvBreakdown(effectiveParams), [effectiveParams]);

  const marginal = useMemo(() => {
    const p2: GameParameters = { ...effectiveParams, freebie_gems_base: effectiveParams.freebie_gems_base + 1.0 };
    const ev2 = calculateTotalEvPerHour(p2);
    return ev2.total - ev.total;
  }, [effectiveParams, ev.total]);

  const giftTooltip = useMemo(() => {
    const total = giftBreakdown.total || 0;
    const entries: Array<{ label: string; key: keyof typeof giftBreakdown }> = [
      { label: "Gems (20-40)", key: "gems_20_40" },
      { label: "Gems (30-65)", key: "gems_30_65" },
      { label: "Skill Shards", key: "skill_shards" },
      { label: "Blue Cow", key: "blue_cow" },
      { label: "2× Speed Boost", key: "speed_boost" },
      { label: "Rare Roll Gems", key: "rare_gems" },
      { label: "Recursive Gifts", key: "recursive_gifts" },
    ];
    return {
      title: "Gift-EV (per 1 opened gift)",
      sections: [
        {
          heading: "Breakdown (value + share)",
          lines: entries.map(({ label, key }) => {
            const v = Number(giftBreakdown[key] ?? 0);
            return `• ${label}: ${fmt1(v)} Gems (${fmtPct(v, total)})`;
          }),
        },
        {
          heading: "Total",
          lines: [`• ${fmt1(total)} Gems per Gift`],
        },
      ],
    };
  }, [giftBreakdown]);

  const freebieInfo = useMemo(
    () => ({
      title: "FREEBIE Parameters",
      sections: [
        { heading: "Base", lines: ["Freebie Gems (Base), Freebie Timer, Claim % (per day)."] },
        { heading: "Special drops", lines: ["Skill Shards: chance + gem-equivalent value.", "Stonks: 1% chance for +200 Gems (toggle)."] },
        { heading: "Multipliers", lines: ["Jackpot: chance for additional rolls.", "Refresh: chance for instant refresh (geometric series)."] },
      ],
    }),
    [],
  );

  const founderInfo = useMemo(
    () => ({
      title: "FOUNDER SUPPLY DROP",
      sections: [
        { heading: "VIP Lounge", lines: ["Interval: 60 − 2×(Level−1) minutes", "Double: 12% at L2, +6% per level", "Triple: 16% at L7"] },
        { heading: "Rewards (desktop assumptions)", lines: ["Founder Gems: fixed 10 Gems/drop", "Founder Speed: 2× for 5 minutes (time saved → more freebies)", "1/1234 chance: 10 gifts per supply drop"] },
        { heading: "Obelisk", lines: ["Obelisk Level affects bonus gems and Gift-EV multipliers."] },
      ],
    }),
    [],
  );

  const bombsInfo = useMemo(
    () => ({
      title: "BOMB MECHANICS",
      sections: [
        {
          heading: "Free Bomb Chance",
          lines: ["Chance that a bomb click consumes 0 charges.", "Applies to the entire dump (all charges at once).", "Affects all bomb types."],
        },
        {
          heading: "Strategy cycle",
          lines: ["Gem (to create space) → [Cherry → Battery → D20 → Gem] repeat.", "Battery and D20 can recursively refill each other and Cherry."],
        },
      ],
    }),
    [],
  );

  return (
    <div className="container">
      <div className="header">
        <div>
          <h1 className="title">Gem EV Calculator</h1>
          <p className="subtitle">Matches the desktop Gem EV layout: colored sections + contribution bar chart + Gift-EV.</p>
        </div>
        <div className="badge">Freebies • Founder • Bombs</div>
      </div>

      <div className="grid gemEvGrid">
        {/* Left: parameters */}
        <div className="panel gemEvLeftPanel">
          <div className="panelHeader">
            <h2 className="panelTitle">Parameters</h2>
            <p className="panelHint">Autosaved in this browser.</p>
          </div>

          <div className="gemEvSection tierHeader1">
            <div className="gemEvSectionHeader">
              <div className="gemEvSectionTitle">
                <Sprite path="sprites/common/gem.png" alt="Freebie" className="iconSmall" />
                <span className="mono">FREEBIE</span>
                <Tooltip content={freebieInfo} />
              </div>
            </div>

            <div className="gemEvSectionBody">
              <Stepper
                label={
                  <>
                    Freebie Gems (Base)
                    <span className="gemEvMarginal">+1 EV: {fmt1(marginal)} Gems/h</span>
                  </>
                }
                value={params.freebie_gems_base}
                onChange={(v) => setParams((s) => ({ ...s, freebie_gems_base: v }))}
                step={1}
                min={0}
                max={9999}
                decimals={1}
              />
              <Stepper
                label="Freebie Timer (Minutes)"
                value={params.freebie_timer_minutes}
                onChange={(v) => setParams((s) => ({ ...s, freebie_timer_minutes: v }))}
                step={0.5}
                min={0.1}
                max={9999}
                decimals={1}
              />
              <Stepper
                label="Freebie Claim (% per Day)"
                value={params.freebie_claim_percentage}
                onChange={(v) => setParams((s) => ({ ...s, freebie_claim_percentage: v }))}
                step={1}
                min={0}
                max={100}
                decimals={1}
              />

              <div className="gemEvDivider" />

              <div className="gemEvInlineHead">
                <Sprite path="sprites/common/skill_shard.png" alt="Skill shards" className="iconSmall" />
                <span className="mono">Skill Shards (Freebie)</span>
              </div>
              <Stepper
                label="Skill Shard Chance (%)"
                value={params.skill_shard_chance * 100}
                onChange={(v) => setParams((s) => ({ ...s, skill_shard_chance: v / 100 }))}
                step={1}
                min={0}
                max={100}
                decimals={1}
              />
              <Stepper
                label="Skill Shard Value (Gems)"
                value={params.skill_shard_value_gems}
                onChange={(v) => setParams((s) => ({ ...s, skill_shard_value_gems: v }))}
                step={0.5}
                min={0}
                max={9999}
                decimals={1}
              />

              <div className="gemEvDivider" />

              <div className="gemEvInlineHead">
                <Sprite path="sprites/common/stonks_tree.png" alt="Stonks" className="iconSmall" />
                <span className="mono">Stonks (Freebie)</span>
              </div>
              <label className="toggle" style={{ marginTop: 4 }}>
                <input type="checkbox" checked={stonksEnabled} onChange={(e) => setStonksEnabled(e.target.checked)} />
                Stonks enabled (1% chance, 200 Gems bonus)
              </label>

              <div className="gemEvDivider" />

              <div className="gemEvInlineHead">
                <span className="mono">Jackpot (Freebie)</span>
              </div>
              <Stepper
                label="Jackpot Chance (%)"
                value={params.jackpot_chance * 100}
                onChange={(v) => setParams((s) => ({ ...s, jackpot_chance: v / 100 }))}
                step={1}
                min={0}
                max={100}
                decimals={1}
              />
              <Stepper
                label="Jackpot Rolls"
                value={params.jackpot_rolls}
                onChange={(v) => setParams((s) => ({ ...s, jackpot_rolls: clampInt(v, 1, 9999) }))}
                step={1}
                min={1}
                max={9999}
                inputMode="numeric"
                decimals={0}
              />

              <div className="gemEvDivider" />

              <div className="gemEvInlineHead">
                <span className="mono">Refresh (Freebie)</span>
              </div>
              <Stepper
                label="Instant Refresh Chance (%)"
                value={params.instant_refresh_chance * 100}
                onChange={(v) => setParams((s) => ({ ...s, instant_refresh_chance: v / 100 }))}
                step={1}
                min={0}
                max={99}
                decimals={1}
              />
            </div>
          </div>

          <div className="gemEvSection tierHeader2">
            <div className="gemEvSectionHeader">
              <div className="gemEvSectionTitle">
                <Sprite path="sprites/event/founderbomb.png" alt="Founder" className="iconSmall" />
                <span className="mono">FOUNDER SUPPLY DROP</span>
                <Tooltip content={founderInfo} />
              </div>
            </div>
            <div className="gemEvSectionBody">
              <Stepper
                label="VIP Lounge Level (1–7)"
                value={params.vip_lounge_level}
                onChange={(v) => setParams((s) => ({ ...s, vip_lounge_level: clampInt(v, 1, 7) }))}
                step={1}
                min={1}
                max={7}
                inputMode="numeric"
                decimals={0}
              />
              <Stepper
                label="Obelisk Level"
                value={params.obelisk_level}
                onChange={(v) => setParams((s) => ({ ...s, obelisk_level: clampInt(v, 0, 999) }))}
                step={1}
                min={0}
                max={999}
                inputMode="numeric"
                decimals={0}
              />
            </div>
          </div>

          <div className="gemEvSection tierHeader3">
            <div className="gemEvSectionHeader">
              <div className="gemEvSectionTitle">
                <Sprite path="sprites/event/founderbomb.png" alt="Bombs" className="iconSmall" />
                <span className="mono">BOMBS</span>
                <Tooltip content={bombsInfo} />
              </div>
            </div>
            <div className="gemEvSectionBody">
              <Stepper
                label="Free Bomb Chance (%)"
                value={params.free_bomb_chance * 100}
                onChange={(v) => setParams((s) => ({ ...s, free_bomb_chance: v / 100 }))}
                step={1}
                min={0}
                max={99}
                decimals={1}
              />

              <div className="gemEvDivider" />

              <div className="gemEvSubSection">
                <div className="gemEvSubHeader">
                  <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                    <span className="mono" style={{ fontWeight: 900 }}>
                      Founder Bomb
                    </span>
                    <Sprite path="sprites/event/founderbomb.png" alt="Founder Bomb" className="iconSmall" />
                  </div>
                  <CardToggles value={params.founder_bomb_recharge_card_level} onChange={(lvl) => setParams((s) => ({ ...s, founder_bomb_recharge_card_level: lvl }))} />
                </div>

                <Stepper
                  label="Founder Bomb Interval (Seconds)"
                  value={params.founder_bomb_interval_seconds}
                  onChange={(v) => setParams((s) => ({ ...s, founder_bomb_interval_seconds: v }))}
                  step={1}
                  min={0.1}
                  max={9999}
                  decimals={1}
                />
                <Stepper
                  label="Speed Chance (%)"
                  value={params.founder_bomb_speed_chance * 100}
                  onChange={(v) => setParams((s) => ({ ...s, founder_bomb_speed_chance: v / 100 }))}
                  step={1}
                  min={0}
                  max={100}
                  decimals={1}
                />
                <Stepper
                  label="Speed Multiplier"
                  value={params.founder_bomb_speed_multiplier}
                  onChange={(v) => setParams((s) => ({ ...s, founder_bomb_speed_multiplier: v }))}
                  step={0.5}
                  min={0.1}
                  max={20}
                  decimals={1}
                />
                <Stepper
                  label="Speed Duration (Seconds)"
                  value={params.founder_bomb_speed_duration_seconds}
                  onChange={(v) => setParams((s) => ({ ...s, founder_bomb_speed_duration_seconds: v }))}
                  step={1}
                  min={0}
                  max={9999}
                  decimals={1}
                />
              </div>

              <div className="gemEvDivider" />

              <div className="gemEvInlineHead">
                <span className="mono">Cherry → Battery → D20 → Gem Cycle</span>
              </div>
              <Stepper
                label="Total Bomb Types"
                value={params.total_bomb_types}
                onChange={(v) => setParams((s) => ({ ...s, total_bomb_types: clampInt(v, 2, 64) }))}
                step={1}
                min={2}
                max={64}
                inputMode="numeric"
                decimals={0}
              />

              <div className="gemEvDivider" />

              <div className="gemEvBombBlock">
                <div className="gemEvBombHeader">
                  <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
                    <span className="mono" style={{ fontWeight: 900 }}>
                      Gem Bomb
                    </span>
                    <Sprite path="sprites/event/gembomb.png" alt="Gem Bomb" className="iconSmall" />
                  </div>
                  <CardToggles value={params.gem_bomb_recharge_card_level} onChange={(lvl) => setParams((s) => ({ ...s, gem_bomb_recharge_card_level: lvl }))} />
                </div>
                <Stepper
                  label="Recharge (Seconds)"
                  value={params.gem_bomb_recharge_seconds}
                  onChange={(v) => setParams((s) => ({ ...s, gem_bomb_recharge_seconds: v }))}
                  step={1}
                  min={0.1}
                  max={9999}
                  decimals={1}
                />
                <Stepper
                  label="Gem Chance per Charge (%)"
                  value={params.gem_bomb_gem_chance * 100}
                  onChange={(v) => setParams((s) => ({ ...s, gem_bomb_gem_chance: v / 100 }))}
                  step={0.5}
                  min={0}
                  max={100}
                  decimals={1}
                />
              </div>

              <div className="gemEvDivider" />

              <div className="gemEvBombBlock">
                <div className="gemEvBombHeader">
                  <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
                    <span className="mono" style={{ fontWeight: 900 }}>
                      Cherry Bomb
                    </span>
                    <Sprite path="sprites/event/cherrybomb.png" alt="Cherry Bomb" className="iconSmall" />
                  </div>
                  <CardToggles value={params.cherry_bomb_recharge_card_level} onChange={(lvl) => setParams((s) => ({ ...s, cherry_bomb_recharge_card_level: lvl }))} />
                </div>
                <Stepper
                  label="Recharge (Seconds)"
                  value={params.cherry_bomb_recharge_seconds}
                  onChange={(v) => setParams((s) => ({ ...s, cherry_bomb_recharge_seconds: v }))}
                  step={1}
                  min={0.1}
                  max={9999}
                  decimals={1}
                />
                <Stepper
                  label="3× Charges Chance (%)"
                  value={params.cherry_bomb_triple_charge_chance * 100}
                  onChange={(v) => setParams((s) => ({ ...s, cherry_bomb_triple_charge_chance: v / 100 }))}
                  step={1}
                  min={0}
                  max={100}
                  decimals={1}
                />
              </div>

              <div className="gemEvDivider" />

              <div className="gemEvBombBlock">
                <div className="gemEvBombHeader">
                  <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
                    <span className="mono" style={{ fontWeight: 900 }}>
                      Battery Bomb
                    </span>
                    <Sprite path="sprites/common/battery_bomb.png" alt="Battery Bomb" className="iconSmall" label="sprites/common/battery_bomb.png" />
                  </div>
                  <CardToggles value={params.battery_bomb_recharge_card_level} onChange={(lvl) => setParams((s) => ({ ...s, battery_bomb_recharge_card_level: lvl }))} />
                </div>
                <Stepper
                  label="Recharge (Seconds)"
                  value={params.battery_bomb_recharge_seconds}
                  onChange={(v) => setParams((s) => ({ ...s, battery_bomb_recharge_seconds: v }))}
                  step={1}
                  min={0.1}
                  max={9999}
                  decimals={1}
                />
              </div>

              <div className="gemEvDivider" />

              <div className="gemEvBombBlock">
                <div className="gemEvBombHeader">
                  <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
                    <span className="mono" style={{ fontWeight: 900 }}>
                      D20 Bomb
                    </span>
                    <Sprite path="sprites/common/d20_bomb.png" alt="D20 Bomb" className="iconSmall" label="sprites/common/d20_bomb.png" />
                  </div>
                  <CardToggles value={params.d20_bomb_recharge_card_level} onChange={(lvl) => setParams((s) => ({ ...s, d20_bomb_recharge_card_level: lvl }))} />
                </div>
                <Stepper
                  label="Recharge (Seconds)"
                  value={params.d20_bomb_recharge_seconds}
                  onChange={(v) => setParams((s) => ({ ...s, d20_bomb_recharge_seconds: v }))}
                  step={1}
                  min={0.1}
                  max={9999}
                  decimals={1}
                />
                <Stepper
                  label="Charges Distributed"
                  value={params.d20_bomb_charges_distributed}
                  onChange={(v) => setParams((s) => ({ ...s, d20_bomb_charges_distributed: clampInt(v, 0, 9999) }))}
                  step={1}
                  min={0}
                  max={9999}
                  inputMode="numeric"
                  decimals={0}
                />
                <Stepper
                  label="Refill Chance (%)"
                  value={params.d20_bomb_refill_chance * 100}
                  onChange={(v) => setParams((s) => ({ ...s, d20_bomb_refill_chance: v / 100 }))}
                  step={0.5}
                  min={0}
                  max={100}
                  decimals={1}
                />
              </div>
            </div>
          </div>
        </div>

        {/* Right: results + chart */}
        <div className="rightColumn">
          <div className="panel panelResults">
            <div className="panelHeader">
              <h2 className="panelTitle">Results</h2>
              <p className="panelHint">Updates instantly.</p>
            </div>

            <div className="kv" style={{ background: "rgba(227,242,253,0.65)" }}>
              <kbd>TOTAL</kbd>
              <div className="mono" style={{ fontWeight: 900 }}>
                {fmt1(ev.total)} Gem-Equivalent/h
              </div>
              <kbd>Gift-EV</kbd>
              <div className="mono" style={{ display: "flex", alignItems: "center", gap: 8 }}>
                <span style={{ fontWeight: 900 }}>{fmt1(giftEv)} Gems per Gift</span>
                <Tooltip content={giftTooltip} />
              </div>
            </div>

            <div className="small" style={{ marginTop: 10 }}>
              Founder supply split: Speed <span className="mono">{fmt1(ev.founder_speed_boost)}</span> • Gems{" "}
              <span className="mono">{fmt1(ev.founder_gems)}</span>
            </div>

            <div className="btnRow" style={{ marginTop: 12 }}>
              <button className="btn" type="button" onClick={() => setChartOpen(true)}>
                OVERVIEW CHART
              </button>
              <Tooltip
                content={{
                  title: "Overview chart",
                  lines: ["Opens the stacked contributions bar chart (Base / Jackpot / Refresh)."],
                }}
              />
            </div>
          </div>
        </div>
      </div>

      {chartOpen ? (
        <div className="modalOverlay" onMouseDown={() => setChartOpen(false)}>
          <div className="modalWindow" onMouseDown={(e) => e.stopPropagation()}>
            <div className="modalHeader">
              <div>
                <div className="mono" style={{ fontWeight: 900 }}>
                  Overview Chart
                </div>
                <div className="small">Stacked: Base / Jackpot / Refresh (Base) / Refresh (Jackpot)</div>
              </div>
              <div style={{ display: "flex", gap: 8 }}>
                <button className="btn btnSecondary" type="button" onClick={() => setChartOpen(false)}>
                  Close
                </button>
              </div>
            </div>
            <div className="modalBody">
              <ContribBarChart ev={ev} breakdown={breakdown} />
            </div>
          </div>
        </div>
      ) : null}
    </div>
  );
}

