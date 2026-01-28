import type { EvBreakdown, EvBreakdownEntry, TotalEv } from "../../lib/gemev/freebieEv";

type SegmentKey = "base" | "jackpot" | "refresh_base" | "refresh_jackpot";

const COLORS: Record<SegmentKey, string> = {
  base: "#2E86AB",
  jackpot: "#A23B72",
  refresh_base: "#F18F01",
  refresh_jackpot: "#C73E1D",
};

function sumEntry(e: EvBreakdownEntry): number {
  return e.base + e.jackpot + e.refresh_base + e.refresh_jackpot;
}

function pct(part: number, total: number): number {
  if (!Number.isFinite(part) || !Number.isFinite(total) || total <= 0) return 0;
  return (part / total) * 100.0;
}

function fmt1(x: number): string {
  if (!Number.isFinite(x)) return "—";
  return x.toFixed(1);
}

function clamp(n: number, min: number, max: number): number {
  return Math.max(min, Math.min(max, n));
}

function LegendSwatch(props: { kind: SegmentKey }) {
  const { kind } = props;
  const W = 18;
  const H = 12;
  const id = `sw_${kind}_${Math.random().toString(16).slice(2)}`;
  const fill =
    kind === "base"
      ? COLORS.base
      : kind === "jackpot"
        ? `url(#${id})`
        : kind === "refresh_base"
          ? `url(#${id})`
          : `url(#${id})`;

  return (
    <svg width={W} height={H} viewBox={`0 0 ${W} ${H}`} style={{ display: "block" }}>
      <defs>
        {kind === "jackpot" ? (
          <pattern id={id} width="8" height="8" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">
            <rect width="8" height="8" fill={COLORS.jackpot} opacity={0.85} />
            <line x1="0" y1="0" x2="0" y2="8" stroke="rgba(255,255,255,0.55)" strokeWidth="3" />
          </pattern>
        ) : null}
        {kind === "refresh_base" ? (
          <pattern id={id} width="10" height="10" patternUnits="userSpaceOnUse">
            <rect width="10" height="10" fill={COLORS.refresh_base} opacity={0.85} />
            <circle cx="3" cy="3" r="1.4" fill="rgba(255,255,255,0.65)" />
            <circle cx="8" cy="7" r="1.4" fill="rgba(255,255,255,0.65)" />
          </pattern>
        ) : null}
        {kind === "refresh_jackpot" ? (
          <pattern id={id} width="10" height="10" patternUnits="userSpaceOnUse">
            <rect width="10" height="10" fill={COLORS.refresh_jackpot} opacity={0.85} />
            <path d="M0 0 L10 10 M10 0 L0 10" stroke="rgba(255,255,255,0.55)" strokeWidth="1.6" />
          </pattern>
        ) : null}
      </defs>
      <rect x="0.5" y="0.5" width={W - 1} height={H - 1} rx="2" fill={kind === "base" ? COLORS.base : fill} stroke="rgba(15,23,42,0.35)" />
    </svg>
  );
}

export function ContribLegend() {
  const legendItems: Array<{ label: string; key: SegmentKey }> = [
    { label: "Base", key: "base" },
    { label: "Jackpot", key: "jackpot" },
    { label: "Refresh (Base)", key: "refresh_base" },
    { label: "Refresh (Jackpot)", key: "refresh_jackpot" },
  ];

  return (
    <div className="gemEvLegend">
      <div className="mono" style={{ fontWeight: 900, marginBottom: 8 }}>
        Legend
      </div>
      <div style={{ display: "grid", gap: 8 }}>
        {legendItems.map((it) => (
          <div key={it.key} className="gemEvLegendRow">
            <LegendSwatch kind={it.key} />
            <div style={{ fontWeight: 800, color: "rgba(15,23,42,0.82)" }}>{it.label}</div>
          </div>
        ))}
      </div>
    </div>
  );
}

export function ContribBarChart(props: { ev: TotalEv; breakdown: EvBreakdown }) {
  const { ev, breakdown } = props;

  const categories = [
    "Gems\n(Base)",
    "Stonks\nEV",
    "Skill\nShards",
    "Founder\nSupply\nDrop",
    "Gem\nBomb",
    "Founder\nBomb",
  ] as const;

  const normalKeys = ["gems_base", "stonks_ev", "skill_shards_ev"] as const;
  const founderSpeed = breakdown.founder_speed_boost;
  const founderGems = breakdown.founder_gems;
  const gemBomb = breakdown.gem_bomb_gems;
  const founderBomb = breakdown.founder_bomb_boost;

  const valuesTop: number[] = [
    ev.gems_base,
    ev.stonks_ev,
    ev.skill_shards_ev,
    ev.founder_speed_boost + ev.founder_gems,
    ev.gem_bomb_gems,
    ev.founder_bomb_boost,
  ];
  const pcts: number[] = [
    pct(ev.gems_base, ev.total),
    pct(ev.stonks_ev, ev.total),
    pct(ev.skill_shards_ev, ev.total),
    pct(ev.founder_speed_boost + ev.founder_gems, ev.total),
    pct(ev.gem_bomb_gems, ev.total),
    pct(ev.founder_bomb_boost, ev.total),
  ];

  const stackForIndex = (i: number): { speed: EvBreakdownEntry | null; gems: EvBreakdownEntry | null; entry: EvBreakdownEntry } => {
    if (i <= 2) return { speed: null, gems: null, entry: breakdown[normalKeys[i]!] };
    if (i === 3) return { speed: founderSpeed, gems: founderGems, entry: founderSpeed };
    if (i === 4) return { speed: null, gems: null, entry: gemBomb };
    return { speed: null, gems: null, entry: founderBomb };
  };

  // Determine max bar height (Founder Supply includes speed + gems).
  const maxVal = Math.max(
    1,
    ...normalKeys.map((k) => sumEntry(breakdown[k])),
    sumEntry(founderSpeed) + sumEntry(founderGems),
    sumEntry(gemBomb),
    sumEntry(founderBomb),
  );

  // SVG layout
  const W = 860;
  const H = 360;
  const padL = 64;
  const padR = 16;
  const padT = 34;
  const padB = 92;
  const plotW = W - padL - padR;
  const plotH = H - padT - padB;

  const barW = 74;
  const gap = (plotW - categories.length * barW) / Math.max(1, categories.length - 1);
  const scaleY = plotH / maxVal;

  const gridLines = 5;
  const yTicks = Array.from({ length: gridLines + 1 }, (_, i) => i / gridLines);

  function yOf(v: number): number {
    return padT + plotH - v * scaleY;
  }

  function hOf(v: number): number {
    return v * scaleY;
  }

  function fillFor(seg: SegmentKey): string {
    if (seg === "base") return COLORS.base;
    if (seg === "jackpot") return "url(#patJackpot)";
    if (seg === "refresh_base") return "url(#patRefreshBase)";
    return "url(#patRefreshJackpot)";
  }

  return (
    <svg
      width="100%"
      viewBox={`0 0 ${W} ${H}`}
      style={{
        display: "block",
        background: "#ffffff",
        borderRadius: 10,
        border: "1px solid rgba(15,23,42,0.10)",
      }}
      role="img"
      aria-label="EV contributions bar chart"
    >
      <defs>
        {/* Jackpot: diagonal hatch */}
        <pattern id="patJackpot" width="8" height="8" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">
          <rect width="8" height="8" fill={COLORS.jackpot} opacity={0.85} />
          <line x1="0" y1="0" x2="0" y2="8" stroke="rgba(255,255,255,0.55)" strokeWidth="3" />
        </pattern>
        {/* Refresh base: dotted */}
        <pattern id="patRefreshBase" width="10" height="10" patternUnits="userSpaceOnUse">
          <rect width="10" height="10" fill={COLORS.refresh_base} opacity={0.85} />
          <circle cx="3" cy="3" r="1.4" fill="rgba(255,255,255,0.65)" />
          <circle cx="8" cy="7" r="1.4" fill="rgba(255,255,255,0.65)" />
        </pattern>
        {/* Refresh jackpot: cross hatch */}
        <pattern id="patRefreshJackpot" width="10" height="10" patternUnits="userSpaceOnUse">
          <rect width="10" height="10" fill={COLORS.refresh_jackpot} opacity={0.85} />
          <path d="M0 0 L10 10 M10 0 L0 10" stroke="rgba(255,255,255,0.55)" strokeWidth="1.6" />
        </pattern>
      </defs>

      {/* Grid + Y labels */}
      {yTicks.map((t, i) => {
        const v = t * maxVal;
        const y = yOf(v);
        return (
          <g key={i}>
            <line x1={padL} y1={y} x2={W - padR} y2={y} stroke="rgba(15,23,42,0.08)" strokeDasharray="4 4" />
            <text x={padL - 10} y={y + 4} textAnchor="end" fontSize={11} fill="rgba(71,85,105,0.9)" fontFamily="var(--mono)">
              {v.toFixed(0)}
            </text>
          </g>
        );
      })}

      {/* Axes */}
      <line x1={padL} y1={padT} x2={padL} y2={padT + plotH} stroke="rgba(15,23,42,0.22)" />
      <line x1={padL} y1={padT + plotH} x2={W - padR} y2={padT + plotH} stroke="rgba(15,23,42,0.22)" />

      {/* Bars */}
      {categories.map((label, i) => {
        const x0 = padL + i * (barW + gap);
        const { speed, gems, entry } = stackForIndex(i);

        // Build segment list for this bar.
        const segs: Array<{ key: SegmentKey; v: number; y: number; h: number; bottom: number }> = [];
        let bottom = 0;
        (["base", "jackpot", "refresh_base", "refresh_jackpot"] as const).forEach((k) => {
          const v = entry[k];
          const h = hOf(v);
          const y = yOf(bottom + v);
          segs.push({ key: k, v, y, h, bottom });
          bottom += v;
        });

        let founderSpeedTotal = 0;
        let founderGemsTotal = 0;
        let segsGems: Array<{ key: SegmentKey; v: number; y: number; h: number; bottom: number }> = [];
        if (i === 3 && speed && gems) {
          founderSpeedTotal = sumEntry(speed);
          // top stack for gems is offset by founderSpeedTotal
          let b2 = founderSpeedTotal;
          segsGems = (["base", "jackpot", "refresh_base", "refresh_jackpot"] as const).map((k) => {
            const v = gems[k];
            const h = hOf(v);
            const y = yOf(b2 + v);
            const out = { key: k, v, y, h, bottom: b2 };
            b2 += v;
            return out;
          });
          founderGemsTotal = sumEntry(gems);
        }

        const totalBarHeight = i === 3 ? founderSpeedTotal + founderGemsTotal : sumEntry(entry);
        const topY = yOf(totalBarHeight);

        const valueLabel = `${fmt1(valuesTop[i] ?? 0)}\n(${fmt1(pcts[i] ?? 0)}%)`;
        const valueBoxW = 66;
        const valueBoxH = 30;
        const boxX = x0 + barW / 2 - valueBoxW / 2;
        const boxY = clamp(topY - valueBoxH - 6, 8, padT + plotH - valueBoxH - 2);

        return (
          <g key={i}>
            {/* bar border */}
            <rect
              x={x0}
              y={yOf(totalBarHeight)}
              width={barW}
              height={hOf(totalBarHeight)}
              fill="none"
              stroke="rgba(15,23,42,0.55)"
              strokeWidth={1}
              rx={2}
            />

            {segs.map((s) =>
              s.v > 0 ? (
                <rect
                  key={s.key}
                  x={x0}
                  y={s.y}
                  width={barW}
                  height={Math.max(0, s.h)}
                  fill={fillFor(s.key)}
                  stroke="rgba(15,23,42,0.45)"
                  strokeWidth={0.6}
                />
              ) : null,
            )}

            {segsGems.map((s) =>
              s.v > 0 ? (
                <rect
                  key={`g_${s.key}`}
                  x={x0}
                  y={s.y}
                  width={barW}
                  height={Math.max(0, s.h)}
                  fill={fillFor(s.key)}
                  stroke="rgba(15,23,42,0.45)"
                  strokeWidth={0.6}
                />
              ) : null,
            )}

            {/* Founder inner labels (Speed / Gems) */}
            {i === 3 ? (
              <>
                {founderSpeedTotal > 0 && hOf(founderSpeedTotal) >= 26 ? (
                  <text
                    x={x0 + barW / 2}
                    y={yOf(founderSpeedTotal / 2)}
                    textAnchor="middle"
                    fontSize={10}
                    fontWeight={900}
                    fill="rgba(15,23,42,0.85)"
                    style={{ pointerEvents: "none" }}
                  >
                    Speed: {fmt1(ev.founder_speed_boost)}
                  </text>
                ) : null}
                {founderGemsTotal > 0 && hOf(founderGemsTotal) >= 26 ? (
                  <text
                    x={x0 + barW / 2}
                    y={yOf(founderSpeedTotal + founderGemsTotal / 2)}
                    textAnchor="middle"
                    fontSize={10}
                    fontWeight={900}
                    fill="rgba(15,23,42,0.85)"
                    style={{ pointerEvents: "none" }}
                  >
                    Gems: {fmt1(ev.founder_gems)}
                  </text>
                ) : null}
              </>
            ) : null}

            {/* value box */}
            <rect x={boxX} y={boxY} width={valueBoxW} height={valueBoxH} rx={8} fill="rgba(255,255,255,0.92)" stroke="rgba(71,85,105,0.45)" />
            <text x={x0 + barW / 2} y={boxY + 12} textAnchor="middle" fontSize={11} fontWeight={900} fill="rgba(15,23,42,0.92)" fontFamily="var(--mono)">
              {fmt1(valuesTop[i] ?? 0)}
            </text>
            <text x={x0 + barW / 2} y={boxY + 24} textAnchor="middle" fontSize={10} fontWeight={800} fill="rgba(71,85,105,0.9)">
              ({fmt1(pcts[i] ?? 0)}%)
            </text>

            {/* x labels */}
            <text x={x0 + barW / 2} y={padT + plotH + 22} textAnchor="middle" fontSize={11} fontWeight={900} fill="rgba(15,23,42,0.85)">
              {label.split("\n")[0]}
            </text>
            {label.split("\n").slice(1).map((line, li) => (
              <text
                key={li}
                x={x0 + barW / 2}
                y={padT + plotH + 22 + (li + 1) * 12}
                textAnchor="middle"
                fontSize={11}
                fontWeight={900}
                fill="rgba(15,23,42,0.85)"
              >
                {line}
              </text>
            ))}
          </g>
        );
      })}
    </svg>
  );
}

