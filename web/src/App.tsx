import { useEffect, useMemo, useRef, useState } from "react";
import { assetUrl } from "./lib/assets";
import { Tooltip } from "./components/Tooltip";
import { isEasterIconMonth } from "./lib/event/icons";
import { loadJson, saveJson } from "./lib/storage";
import { EventSim } from "./modules/event/EventSim";
import { ArchSim } from "./modules/arch/ArchSim";
import { GemEv } from "./modules/gemev/GemEv";
import { Stargazing } from "./modules/stargazing/Stargazing";
import { Fishing } from "./modules/fishing/Fishing";
import { Drone } from "./modules/drone/Drone";
import { Lootbug } from "./modules/lootbug/Lootbug";
import { Items } from "./modules/items/Items";
import { Bombs } from "./modules/bombs/Bombs";
import { OvernightGains } from "./modules/overnight/OvernightGains";
import { Veins } from "./modules/veins/Veins";
import { Transmuter } from "./modules/transmuter/Transmuter";
import "./modules/overnight/overnight.css";
type ModuleId =
  | "event"
  | "arch"
  | "gemev"
  | "bombs"
  | "stargazing"
  | "fishing"
  | "drone"
  | "lootbug"
  | "veins"
  | "items"
  | "transmuter"
  | "overnight"
  | "about";
const SUPPORT_URL = "https://buymeacoffee.com/arisboeuf";
const EVENT_EASTER_ICON = "https://static.wikitide.net/shminerwiki/c/cd/Event_Button_Easter.png";
/** Obelisk level for “tested up to” in About and README. Update README when this changes. */
const OB_LEVEL = 60;
const HEADER_MINIMIZED_KEY = "obeliskfarm:web:header_minimized";
const SHOW_BACKUP_KEY = "obeliskfarm:web:about_show_backup";
const BACKUP_INTERVAL_MIN_KEY = "obeliskfarm:web:backup_interval_min";
const BACKUP_PREFIX = "obeliskfarm:web:";
const DEFAULT_BACKUP_INTERVAL_MIN = 10;
const MIN_BACKUP_INTERVAL_MIN = 0.5;
const MAX_BACKUP_INTERVAL_MIN = 120;

function Sprite(props: { path: string; alt: string; className?: string }) {
  const src = props.path.startsWith("http://") || props.path.startsWith("https://") ? props.path : assetUrl(props.path);
  return <img className={props.className ?? "icon"} src={src} alt={props.alt} />;
}

function MoonStarsIcon() {
  return (
    <span className="icon navOvernightIconWrap" aria-hidden="true">
      <svg className="navOvernightIcon" viewBox="0 0 24 24" fill="currentColor">
        <path d="M12 3a6 6 0 0 0 6 6c0 2.2-1.2 4.1-3 5.2A6 6 0 0 1 6 12a6 6 0 0 1 6-9Z" />
        <circle cx="18" cy="6" r="1" fill="currentColor" />
        <circle cx="20" cy="14" r="0.8" fill="currentColor" />
        <circle cx="5" cy="18" r="0.7" fill="currentColor" />
      </svg>
    </span>
  );
}

export function App() {
  const [active, setActive] = useState<ModuleId>("gemev");
  const [navExpanded, setNavExpanded] = useState(false);
  const [headerMinimized, setHeaderMinimized] = useState(() => loadJson<boolean>(HEADER_MINIMIZED_KEY) ?? false);
  const [showBackup, setShowBackup] = useState(() => loadJson<boolean>(SHOW_BACKUP_KEY) ?? false);
  const [backupIntervalMin, setBackupIntervalMin] = useState(() => {
    const v = loadJson<number>(BACKUP_INTERVAL_MIN_KEY);
    if (typeof v === "number" && v >= MIN_BACKUP_INTERVAL_MIN && v <= MAX_BACKUP_INTERVAL_MIN) return v;
    return DEFAULT_BACKUP_INTERVAL_MIN;
  });
  const [restoreMessage, setRestoreMessage] = useState<"idle" | "ok" | "error">("idle");
  const fileInputRef = useRef<HTMLInputElement>(null);
  useEffect(() => {
    saveJson(HEADER_MINIMIZED_KEY, headerMinimized);
  }, [headerMinimized]);
  useEffect(() => {
    saveJson(SHOW_BACKUP_KEY, showBackup);
  }, [showBackup]);
  useEffect(() => {
    saveJson(BACKUP_INTERVAL_MIN_KEY, backupIntervalMin);
  }, [backupIntervalMin]);

  const handleRestoreBackup = (e: React.ChangeEvent<HTMLInputElement>) => {
    setRestoreMessage("idle");
    const file = e.target.files?.[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = () => {
      try {
        const raw = reader.result as string;
        const data = JSON.parse(raw) as Record<string, string>;
        let count = 0;
        for (const [key, value] of Object.entries(data)) {
          if (key.startsWith(BACKUP_PREFIX) && typeof value === "string") {
            localStorage.setItem(key, value);
            count++;
          }
        }
        setRestoreMessage(count > 0 ? "ok" : "error");
      } catch {
        setRestoreMessage("error");
      }
    };
    reader.onerror = () => setRestoreMessage("error");
    reader.readAsText(file, "utf8");
    e.target.value = "";
  };

  // Dev only: backup localStorage to web/backups/ at configured interval
  useEffect(() => {
    if (!import.meta.env.DEV) return;
    const ms = Math.max(MIN_BACKUP_INTERVAL_MIN * 60 * 1000, Math.min(MAX_BACKUP_INTERVAL_MIN * 60 * 1000, backupIntervalMin * 60 * 1000));
    const backup = () => {
      const snapshot: Record<string, string> = {};
      for (let i = 0; i < localStorage.length; i++) {
        const key = localStorage.key(i);
        if (key?.startsWith("obeliskfarm:web:")) snapshot[key] = localStorage.getItem(key) ?? "";
      }
      fetch("/api/backup", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(snapshot),
      }).catch(() => {});
    };
    const id = setInterval(backup, ms);
    return () => clearInterval(id);
  }, [backupIntervalMin]);

  const modules = useMemo(
    () =>
      [
        { id: "event" as const, label: "Event Simulator", icon: "sprites/event/event_button.png" },
        { id: "arch" as const, label: "Archaeology Simulator", icon: "sprites/archaeology/archaeology.png" },
        { id: "gemev" as const, label: "Gem EV Calculator", icon: "sprites/common/gem.png" },
        { id: "bombs" as const, label: "Bombs", icon: "sprites/event/gembomb.png" },
        { id: "stargazing" as const, label: "Stargazing", icon: "sprites/stargazing/stargazing.svg" },
        { id: "fishing" as const, label: "Fishing", icon: "https://static.wikitide.net/shminerwiki/f/fb/Fishing_Button.png" },
        { id: "drone" as const, label: "Drone", icon: "https://static.wikitide.net/shminerwiki/d/d1/Drones_Button.png" },
        { id: "lootbug" as const, label: "Lootbug", icon: "https://static.wikitide.net/shminerwiki/8/86/Lootbug_Default.png" },
        { id: "veins" as const, label: "Veins", icon: "https://static.wikitide.net/shminerwiki/0/04/Stone_Vein.png" },
        { id: "items" as const, label: "Items / Chests", icon: "https://static.wikitide.net/shminerwiki/a/a8/Item_Chest.png" },
        {
          id: "transmuter" as const,
          label: "Ore / Bars",
          icon: "https://static.wikitide.net/shminerwiki/c/c4/Tin_Ore.png",
        },
        { id: "overnight" as const, label: "Overnight Gains", icon: "" },
      ] as const,
    [],
  );

  return (
    <div className={`appShell ${active === "overnight" ? "overnightActive" : ""}`}>
      <div className={`topNav ${navExpanded ? "navExpanded" : ""} ${headerMinimized ? "headerMinimized" : ""}`}>
        <div className="topNavBrand">
          <Sprite path="sprites/common/gem.png" alt="ObeliskFarm" className="icon" />
          <div className="topNavBrandText">
            <div className="topNavTitle">ObeliskFarm (Web)</div>
            {!headerMinimized ? <div className="topNavSubtitle">Choose a module.</div> : null}
          </div>
          <button
            type="button"
            className={`navTile navTileAbout ${active === "about" ? "navTileActive" : ""}`}
            onClick={() => setActive("about")}
          >
            <span className="navEmoji" aria-hidden="true">
              ℹ️
            </span>
            <span className="navTileLabel">About this tool</span>
          </button>
          {!headerMinimized ? (
            <span className="topNavUpdateHint" aria-hidden="true">
              F5 daily to activate latest updates!
            </span>
          ) : null}
        </div>
        <div className="topNavButtons">
          {modules.map((m) => (
            <button
              key={m.id}
              type="button"
              className={`navTile ${active === m.id ? "navTileActive" : ""} ${m.id === "overnight" ? "navTileOvernight" : ""}`}
              onClick={() => setActive(m.id)}
            >
              {m.id === "overnight" ? <MoonStarsIcon /> : <Sprite path={m.id === "event" && isEasterIconMonth() ? EVENT_EASTER_ICON : m.icon} alt={m.label} className="icon" />}
              <span className="navTileLabel">
                <span>{m.label}</span>
                {m.id === "veins" && (
                  <span className="navBetaBadge">
                    <Tooltip
                      content={{ title: "Beta", lines: ["This module is in beta. Numbers and behaviour may change."] }}
                      label="Beta"
                    />
                  </span>
                )}
              </span>
            </button>
          ))}
        </div>
        <button
          type="button"
          className="topNavMinimize"
          onClick={() => setHeaderMinimized((v) => !v)}
          aria-pressed={headerMinimized}
          aria-expanded={!headerMinimized}
          aria-label={headerMinimized ? "Expand menu" : "Collapse menu"}
          title={headerMinimized ? "Expand menu (show module tiles)" : "Collapse menu (more space for content)"}
        >
          {headerMinimized ? "Maximize Menu" : "Minimize Menu"}
        </button>
        <button
          type="button"
          className="topNavToggle"
          onClick={() => setNavExpanded((v) => !v)}
          aria-expanded={navExpanded}
          aria-label={navExpanded ? "Close menu" : "Open menu"}
        >
          {navExpanded ? "✕" : "☰"}
        </button>
      </div>

      {active === "about" ? (
        <div className="aboutSection">
          <h2 className="aboutTitle">About this tool</h2>
          <p className="aboutText">
            I'm a hobby developer and gamer. I created this tool for my personal use, opposing spreadsheet/Excel workflows.
          </p>
          <p className="aboutText">
            I realized how helpful it could be to the community so here it is publicly available for everybody. I have used a lot of AI to make this possible; however, I tested {' & '}{' '}
            <strong>confirmed numerical outcomes as far as my game progress would allow</strong>
          </p>
          <div className="aboutObWrap" aria-hidden="true">
            <span className="aboutObArrow">↓</span>
            <span className={`mono aboutObRainbow`} style={{ fontSize: "1.5em", fontWeight: 800 }}>
              ob {OB_LEVEL}
            </span>
          </div>
          <p className="aboutText">
            If you like my work and want to support me, you can do so here:
          </p>
          <a className="aboutCta" href={SUPPORT_URL} target="_blank" rel="noreferrer noopener">
            Support me on Buy Me a Coffee
          </a>

          <div className="aboutBackupToggle">
            <input
              type="checkbox"
              id="about-show-backup"
              checked={showBackup}
              onChange={(e) => setShowBackup(e.target.checked)}
              className="aboutBackupCheckbox"
            />
            <label htmlFor="about-show-backup" className="aboutBackupToggleLabel">
              Backup & restore
            </label>
          </div>
          {showBackup && (
            <div className="aboutBackup">
              <div className="aboutBackupIntervalRow">
                <label htmlFor="about-backup-interval" className="aboutBackupIntervalLabel">
                  Auto-save backup every
                </label>
                <input
                  id="about-backup-interval"
                  type="number"
                  inputMode="decimal"
                  min={MIN_BACKUP_INTERVAL_MIN}
                  max={MAX_BACKUP_INTERVAL_MIN}
                  step={0.5}
                  value={backupIntervalMin}
                  onChange={(e) => {
                    const raw = e.target.value.replace(",", ".");
                    const n = Number.parseFloat(raw);
                    if (!Number.isFinite(n)) return;
                    const clamped = Math.max(MIN_BACKUP_INTERVAL_MIN, Math.min(MAX_BACKUP_INTERVAL_MIN, n));
                    setBackupIntervalMin(clamped);
                  }}
                  className="aboutBackupIntervalInput mono"
                />
                <span className="aboutBackupIntervalSuffix">minutes</span>
              </div>
              <p className="aboutText aboutBackupIntervalHint">
                When running locally (e.g. <code>npm run dev</code>), a backup file is saved at this interval.
              </p>
              <p className="aboutText aboutBackupFolder">
                Backup folder: <code className="mono">web/backups/</code> (relative to project root).
              </p>
              <h3 className="aboutSubtitle">Restore backup</h3>
              <p className="aboutText">
                Choose a backup file (e.g. from <code>web/backups/</code>). After restore, reload the page to apply.
              </p>
              <input
                ref={fileInputRef}
                type="file"
                accept=".json,application/json"
                aria-label="Choose backup file"
                className="aboutFileInput"
                onChange={handleRestoreBackup}
              />
              <button
                type="button"
                className="aboutCta aboutCtaSecondary"
                onClick={() => fileInputRef.current?.click()}
              >
                Choose backup file
              </button>
              {restoreMessage === "ok" && (
                <p className="aboutText aboutRestoreOk">
                  Restored. <button type="button" className="aboutReloadBtn" onClick={() => window.location.reload()}>Reload page</button> to apply.
                </p>
              )}
              {restoreMessage === "error" && (
                <p className="aboutText aboutRestoreError">Could not restore (invalid file or no obeliskfarm keys).</p>
              )}
            </div>
          )}
        </div>
      ) : active === "gemev" ? (
        <GemEv />
      ) : active === "bombs" ? (
        <Bombs />
      ) : active === "event" ? (
        <EventSim />
      ) : active === "arch" ? (
        <ArchSim />
      ) : active === "drone" ? (
        <Drone />
      ) : active === "lootbug" ? (
        <Lootbug />
      ) : active === "veins" ? (
        <Veins />
      ) : active === "items" ? (
        <Items />
      ) : active === "transmuter" ? (
        <Transmuter />
      ) : active === "fishing" ? (
        <Fishing />
      ) : active === "overnight" ? (
        <OvernightGains />
      ) : (
        <Stargazing />
      )}
    </div>
  );
}

