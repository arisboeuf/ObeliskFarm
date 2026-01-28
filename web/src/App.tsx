import { useMemo, useState } from "react";
import { assetUrl } from "./lib/assets";
import { EventSim } from "./modules/event/EventSim";
import { ArchSim } from "./modules/arch/ArchSim";

type ModuleId = "event" | "arch";

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
              <span>{m.label}</span>
            </button>
          ))}
        </div>
      </div>

      {active === "event" ? <EventSim /> : <ArchSim />}
    </div>
  );
}

