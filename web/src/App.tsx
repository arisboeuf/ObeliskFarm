import { useMemo, useState } from "react";
import { assetUrl } from "./lib/assets";
import { Tooltip } from "./components/Tooltip";
import { EventSim } from "./modules/event/EventSim";
import { ArchSim } from "./modules/arch/ArchSim";
import { GemEv } from "./modules/gemev/GemEv";
import { Stargazing } from "./modules/stargazing/Stargazing";

type ModuleId = "event" | "arch" | "gemev" | "stargazing";
const SUPPORT_URL = "https://buymeacoffee.com/arisboeuf";

function Sprite(props: { path: string; alt: string; className?: string }) {
  return <img className={props.className ?? "icon"} src={assetUrl(props.path)} alt={props.alt} />;
}

export function App() {
  const [active, setActive] = useState<ModuleId>("event");

  const modules = useMemo(
    () =>
      [
        { id: "event" as const, label: "Event Simulator", icon: "sprites/event/event_button.png" },
        { id: "arch" as const, label: "Archaeology Simulator", icon: "sprites/archaeology/archaeology.png" },
        { id: "gemev" as const, label: "Gem EV Calculator", icon: "sprites/common/gem.png" },
        { id: "stargazing" as const, label: "Stargazing Calculator", icon: "sprites/stargazing/stargazing.svg" },
      ] as const,
    [],
  );

  return (
    <div className="appShell">
      <div className="topNav">
        <div className="topNavBrand">
          <Sprite path="sprites/common/gem.png" alt="ObeliskFarm" className="icon" />
          <div>
            <div className="topNavTitle">ObeliskFarm (Web)</div>
            <div className="topNavSubtitle">Choose a module.</div>
          </div>
        </div>

        <div className="topNavButtons">
          {modules.map((m) => (
            <button
              key={m.id}
              type="button"
              className={`navTile ${active === m.id ? "navTileActive" : ""}`}
              onClick={() => setActive(m.id)}
            >
              <Sprite path={m.icon} alt={m.label} className="icon" />
              <span className="navTileLabel">
                <span>{m.label}</span>
                {(m.id === "event" || m.id === "arch") && (
                  <span className="navWorkingHorse" aria-hidden="true" title="Main module">
                    !
                  </span>
                )}
              </span>
            </button>
          ))}

          <a className="navTile navTileDonation" href={SUPPORT_URL} target="_blank" rel="noreferrer noopener">
            <span className="navEmoji" aria-hidden="true">
              💵
            </span>
            <span className="navTileSupportLabel">
              Support me{" "}
              <Tooltip
                content={{
                  title: "Support this project",
                  lines: [
                    "I'm a beginner and I build ObeliskFarm as a hobby project.",
                    "If you find it useful, a small donation helps me keep improving it.",
                    "Thank you for the support!",
                  ],
                }}
              />
            </span>
          </a>
        </div>
      </div>

      {active === "gemev" ? <GemEv /> : active === "event" ? <EventSim /> : active === "arch" ? <ArchSim /> : <Stargazing />}
    </div>
  );
}

