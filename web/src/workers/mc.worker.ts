import { monteCarloOptimizeGuided } from "../lib/event/monteCarloOptimizer";
import type { Budget, UpgradeState } from "../lib/event/optimizer";

type StartMessage = {
  type: "start";
  payload: {
    budget: Budget;
    prestige: number;
    initialState: UpgradeState;
    numCandidates: number;
    runsPerCombo: number;
    seedBase: number | null;
  };
};

type CancelMessage = { type: "cancel" };

type InMessage = StartMessage | CancelMessage;

let cancelled = false;

self.onmessage = (ev: MessageEvent<InMessage>) => {
  const msg = ev.data;
  if (msg.type === "cancel") {
    cancelled = true;
    return;
  }
  if (msg.type !== "start") return;

  cancelled = false;

  const { budget, prestige, initialState, numCandidates, runsPerCombo, seedBase } = msg.payload;

  try {
    const res = monteCarloOptimizeGuided({
      budget,
      prestige,
      initialState,
      numRuns: numCandidates,
      eventRunsPerCombination: runsPerCombo,
      seedBase,
      progressCallback: (cur, total, curWave, bestWave) => {
        if (cancelled) throw new Error("cancelled");
        if (cur % 10 === 0 || cur === total) {
          (self as unknown as Worker).postMessage({
            type: "progress",
            payload: { cur, total, curWave, bestWave },
          });
        }
      },
    });

    (self as unknown as Worker).postMessage({ type: "done", payload: res });
  } catch (e) {
    if (String(e).includes("cancelled")) {
      (self as unknown as Worker).postMessage({ type: "cancelled" });
      return;
    }
    (self as unknown as Worker).postMessage({ type: "error", payload: { message: e instanceof Error ? e.message : String(e) } });
  }
};

