import { fragmentSimsSummary, stageSimsDetailed, stageSimsSummary, MonteCarloArchaeologySimulator, type CardConfig } from "../lib/archaeology/mc/monteCarlo";
import { mulberry32 } from "../lib/archaeology/mc/prng";

type Msg =
  | { type: "stageSummary"; payload: Parameters<typeof stageSimsSummary>[0] }
  | { type: "fragmentSummary"; payload: Parameters<typeof fragmentSimsSummary>[0] }
  | { type: "stageDetailed"; payload: Parameters<typeof stageSimsDetailed>[0] }
  | {
      type: "stageLite";
      payload: {
        stats: any;
        starting_floor: number;
        n_sims: number;
        options: { use_crit: boolean; enrage_enabled: boolean; flurry_enabled: boolean; quake_enabled: boolean };
        cardCfg: CardConfig | null;
        seed: number;
        targetFrag?: string | null;
      };
    };

function runStageLite(payload: any) {
  // Lite variant to keep transfer sizes small.
  const rng = mulberry32((payload.seed ?? 0) >>> 0);
  const sim = new MonteCarloArchaeologySimulator(rng);
  const max_stage_samples: number[] = [];
  const floors_cleared_samples: number[] = [];
  const xp_per_run_samples: number[] = [];
  const total_fragments_samples: number[] = [];
  const run_duration_seconds_samples: number[] = [];
  const target_frag_samples: number[] = [];
  const tfrag = payload.targetFrag ? String(payload.targetFrag) : null;

  for (let i = 0; i < Math.max(0, Math.trunc(payload.n_sims)); i += 1) {
    const r: any = sim.simulateRun(payload.stats, payload.starting_floor, { ...payload.options, return_block_metrics: false }, payload.cardCfg);
    max_stage_samples.push(Number(r.max_stage_reached ?? 0));
    floors_cleared_samples.push(Number(r.floors_cleared ?? 0));
    xp_per_run_samples.push(Number(r.xp_per_run ?? 0));
    total_fragments_samples.push(Number(r.total_fragments ?? 0));
    run_duration_seconds_samples.push(Number(r.run_duration_seconds ?? 1));
    if (tfrag) target_frag_samples.push(Number(r.fragments?.[tfrag] ?? 0));
  }

  return { max_stage_samples, floors_cleared_samples, xp_per_run_samples, total_fragments_samples, run_duration_seconds_samples, target_frag_samples: tfrag ? target_frag_samples : null };
}

self.onmessage = async (ev: MessageEvent<Msg>) => {
  const msg = ev.data;
  try {
    if (msg.type === "stageSummary") {
      (self as unknown as Worker).postMessage({ type: "ok", payload: stageSimsSummary(msg.payload) });
      return;
    }
    if (msg.type === "fragmentSummary") {
      (self as unknown as Worker).postMessage({ type: "ok", payload: fragmentSimsSummary(msg.payload) });
      return;
    }
    if (msg.type === "stageDetailed") {
      (self as unknown as Worker).postMessage({ type: "ok", payload: stageSimsDetailed(msg.payload) });
      return;
    }
    if (msg.type === "stageLite") {
      const r = runStageLite(msg.payload);
      (self as unknown as Worker).postMessage({ type: "ok", payload: r });
      return;
    }
  } catch (e) {
    (self as unknown as Worker).postMessage({ type: "error", payload: { message: e instanceof Error ? e.message : String(e) } });
  }
};

