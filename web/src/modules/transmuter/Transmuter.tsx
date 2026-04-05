import { useEffect, useMemo, useRef, useState } from "react";
import { Collapsible } from "../../components/Collapsible";
import { Tooltip } from "../../components/Tooltip";
import { loadJson, saveJson } from "../../lib/storage";
import {
  computeTransmuter,
  resolveWikiImageUrl,
  type TransmuterInputs,
} from "./transmuterCalc";
import "./transmuter.css";

const STORAGE_KEY = "obeliskfarm:web:transmuter:v1";
const CREDIT_URL = "https://tabatkins.com/obelisk/transmuter/";

const DEFAULT_INPUTS: TransmuterInputs = {
  free: 0,
  x2: 0,
  x3: 0,
  x5: 0,
  x10: 0,
  x20: 0,
  x100: 0,
  craftcost: 1,
  bop: 1,
  trans: 1,
  transbop: 25,
  bopgold: 0,
  goldchance: 0,
  goldmult: 5,
};

function parseNumber(raw: string): number {
  const cleaned = raw.trim().replaceAll(",", ".").replaceAll(" ", "");
  if (!cleaned) return 0;
  const n = Number(cleaned);
  return Number.isFinite(n) ? n : 0;
}

function clamp(n: number, min: number, max: number): number {
  if (!Number.isFinite(n)) return min;
  return Math.max(min, Math.min(max, n));
}

function mergeLoaded(saved: unknown): TransmuterInputs {
  if (!saved || typeof saved !== "object") return { ...DEFAULT_INPUTS };
  const o = saved as Record<string, unknown>;
  const num = (k: keyof TransmuterInputs, def: number) => {
    const v = o[k];
    return typeof v === "number" && Number.isFinite(v) ? v : def;
  };
  return {
    free: num("free", DEFAULT_INPUTS.free),
    x2: num("x2", DEFAULT_INPUTS.x2),
    x3: num("x3", DEFAULT_INPUTS.x3),
    x5: num("x5", DEFAULT_INPUTS.x5),
    x10: num("x10", DEFAULT_INPUTS.x10),
    x20: num("x20", DEFAULT_INPUTS.x20),
    x100: num("x100", DEFAULT_INPUTS.x100),
    craftcost: num("craftcost", DEFAULT_INPUTS.craftcost),
    bop: num("bop", DEFAULT_INPUTS.bop),
    trans: num("trans", DEFAULT_INPUTS.trans),
    transbop: num("transbop", DEFAULT_INPUTS.transbop),
    bopgold: num("bopgold", DEFAULT_INPUTS.bopgold),
    goldchance: num("goldchance", DEFAULT_INPUTS.goldchance),
    goldmult: num("goldmult", DEFAULT_INPUTS.goldmult),
  };
}

function NumRow(props: {
  label: React.ReactNode;
  value: number;
  onChange: (n: number) => void;
  min?: number;
  max?: number;
  suffix: string;
}) {
  const { label, value, onChange, min = -Infinity, max = Infinity, suffix } = props;
  const isEditingRef = useRef(false);
  /** Two decimal places for display and commit (project numeric-input rule). */
  const decimals = 2;
  const formatDisplay = (v: number) => (Number.isFinite(v) ? v.toFixed(decimals) : "");
  const [raw, setRaw] = useState(() => formatDisplay(value));

  useEffect(() => {
    if (isEditingRef.current) return;
    setRaw(formatDisplay(value));
  }, [value, decimals]);

  function commit() {
    const n = parseNumber(raw);
    const next = clamp(n, min, max);
    const rounded = Number.isFinite(next) ? Number(next.toFixed(decimals)) : next;
    onChange(rounded);
    isEditingRef.current = false;
    setRaw(formatDisplay(rounded));
  }

  return (
    <>
      <div className="transmuterLabel">{label}</div>
      <div className="transmuterField">
        <input
          type="text"
          inputMode="decimal"
          value={raw}
          onFocus={() => {
            isEditingRef.current = true;
          }}
          onChange={(e) => {
            isEditingRef.current = true;
            setRaw(e.target.value);
          }}
          onBlur={() => commit()}
          onKeyDown={(e) => {
            if (e.key === "Enter") {
              e.preventDefault();
              commit();
            }
          }}
          aria-label={typeof label === "string" ? label : undefined}
        />
        <span className="transmuterSuffix">{suffix}</span>
      </div>
    </>
  );
}

function OreInline(props: { name: string; world: number; oreImg: string; barImg: string }) {
  const { name, world, oreImg, barImg } = props;
  const oreSrc = resolveWikiImageUrl(oreImg);
  const barSrc = resolveWikiImageUrl(barImg);
  return (
    <span className="transmuterOreBadge">
      <span className="mono">
        {name} (W{world})
      </span>
      {oreSrc ? <img className="transmuterOrePic" src={oreSrc} alt="" /> : null}
      {barSrc ? <img className="transmuterOrePic" src={barSrc} alt="" /> : null}
    </span>
  );
}

export function Transmuter() {
  const [inputs, setInputs] = useState<TransmuterInputs>(() => mergeLoaded(loadJson<unknown>(STORAGE_KEY)));

  useEffect(() => {
    saveJson(STORAGE_KEY, inputs);
  }, [inputs]);

  const result = useMemo(() => computeTransmuter(inputs), [inputs]);
  const bpFloor = Number.isFinite(result.costTransition) ? Math.floor(result.costTransition) : null;

  function patch<K extends keyof TransmuterInputs>(key: K, v: TransmuterInputs[K]) {
    setInputs((prev) => ({ ...prev, [key]: v }));
  }

  return (
    <div className="transmuterModule">
      <h1 className="transmuterTitle">Transmuter Bomb vs Crafting</h1>
      <p className="transmuterIntro">
        Compare Bomb of Plenty plus manual bar crafting against using Transmuter Bomb directly, for the same stats you would enter in the reference tool.
      </p>
      <p className="transmuterCredits">
        All credits go to{" "}
        <a href={CREDIT_URL} target="_blank" rel="noreferrer noopener">
          {CREDIT_URL}
        </a>
        . This module mirrors that calculator and saves your inputs in this app (browser local storage). I included this calc in my ObeliskFarm tool because I wanted to have everything in one place.
      </p>

      <form
        className="transmuterForm"
        onSubmit={(e) => {
          e.preventDefault();
        }}
      >
        <NumRow label="Free Craft Chance" value={inputs.free} onChange={(n) => patch("free", n)} min={0} max={100} suffix="%" />
        <NumRow label="Double Craft Chance" value={inputs.x2} onChange={(n) => patch("x2", n)} min={0} max={100} suffix="%" />
        <NumRow label="Triple Craft Chance" value={inputs.x3} onChange={(n) => patch("x3", n)} min={0} max={100} suffix="%" />
        <NumRow label="5x Craft Chance" value={inputs.x5} onChange={(n) => patch("x5", n)} min={0} max={100} suffix="%" />
        <NumRow label="10x Craft Chance" value={inputs.x10} onChange={(n) => patch("x10", n)} min={0} max={100} suffix="%" />
        <NumRow label="20x Craft Chance" value={inputs.x20} onChange={(n) => patch("x20", n)} min={0} max={100} suffix="%" />
        <NumRow label="100x Craft Chance" value={inputs.x100} onChange={(n) => patch("x100", n)} min={0} max={100} suffix="%" />
        <NumRow
          label={
            <span className="transmuterLabelWithTip">
              Bar Craft Cost Multi
              <Tooltip
                content={{
                  title: "Bar Craft Cost Multi",
                  sections: [
                    {
                      heading: "What it is",
                      lines: [
                        "The in-game multiplier that lowers how many ores one bar costs (shown on the bar craft UI).",
                      ],
                    },
                    {
                      heading: "In this calc",
                      lines: [
                        "Ore breakpoints use floor(cost × this value), same as the reference tool.",
                        "Enter the value as shown in the game (e.g. 1 or 0.5).",
                      ],
                    },
                  ],
                }}
              />
            </span>
          }
          value={inputs.craftcost}
          onChange={(n) => patch("craftcost", n)}
          min={0}
          max={1}
          suffix="×"
        />
        <NumRow label="Bomb of Plenty Mult" value={inputs.bop} onChange={(n) => patch("bop", n)} min={1} max={1e9} suffix="×" />
        <NumRow label="Transmuter Bomb Mult" value={inputs.trans} onChange={(n) => patch("trans", n)} min={1} max={1e9} suffix="×" />
        <NumRow label="Chance of Trans Applying BoP" value={inputs.transbop} onChange={(n) => patch("transbop", n)} min={0} max={100} suffix="%" />
        <NumRow label="Chance of BoP Turning Ores Gold" value={inputs.bopgold} onChange={(n) => patch("bopgold", n)} min={0} max={100} suffix="%" />
        <NumRow label="Golden Ore Chance" value={inputs.goldchance} onChange={(n) => patch("goldchance", n)} min={0} max={100} suffix="%" />
        <NumRow label="Golden Ore Multi" value={inputs.goldmult} onChange={(n) => patch("goldmult", n)} min={0} max={1e9} suffix="×" />

        <div className="transmuterOutput">
          <p className="transmuterOutputLine">
            Use Bomb of Plenty for{" "}
            {result.lowOre ? <OreInline {...result.lowOre} /> : <span className="mono">nothing</span>} or lower.
          </p>
          <p className="transmuterOutputLine">
            Use Transmuter for{" "}
            {result.highOre ? (
              <OreInline {...result.highOre} />
            ) : (
              <span className="mono">ores above the table</span>
            )}{" "}
            or higher.
          </p>
          <p className="transmuterOutputLine">
            (Breakpoint is a 1× craft cost of{" "}
            <span className="transmuterBreakpoint mono">{bpFloor !== null ? bpFloor : "—"}</span> ores per bar.)
          </p>
        </div>

        <p className="transmuterSpoon">
          If using a spoon to auto-fire both BoP <em>and</em> transmuter, that is better than using either on its own.
        </p>
      </form>

      <Collapsible id="transmuter-notes" title="Notes" className="transmuterNotes" defaultExpanded={false}>
        <div className="transmuterNotesBody">
          <p>
            Several bar-related stats are not used in this calc. Mostly, that is because they apply equally to both strategies, like <code>Bar Output Multi</code>, so
            they are not relevant to choosing between the two.
          </p>
          <p>
            <code>Bar Craft Cost Multi</code> is relevant, but it is already folded into the breakpoint search: ore costs are multiplied by that value before
            comparing to the transition cost (same idea as the reference tool: you match against the cost the game shows for 1× crafts).
          </p>
          <p>
            Golden ore stats matter most once Workshop gives BoP a chance to create golden ore. Before that, natural golden ore chance affects both strategies in
            the same way.
          </p>
        </div>
      </Collapsible>
    </div>
  );
}
