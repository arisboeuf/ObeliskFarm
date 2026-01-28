import { useEffect, useMemo, useState } from "react";

export function Collapsible(props: {
  id: string;
  title: React.ReactNode;
  defaultExpanded?: boolean;
  headerRight?: React.ReactNode;
  children: React.ReactNode;
}) {
  const { id, title, defaultExpanded, headerRight, children } = props;

  const storageKey = useMemo(() => `obeliskfarm:web:ui:collapse:${id}`, [id]);
  const [expanded, setExpanded] = useState<boolean>(() => {
    try {
      const raw = localStorage.getItem(storageKey);
      if (raw === "0") return false;
      if (raw === "1") return true;
    } catch {
      // ignore
    }
    return defaultExpanded ?? true;
  });

  useEffect(() => {
    try {
      localStorage.setItem(storageKey, expanded ? "1" : "0");
    } catch {
      // ignore
    }
  }, [expanded, storageKey]);

  return (
    <div className="collapseWrap">
      <div className="collapseHeader">
        <button className="collapseToggle" type="button" onClick={() => setExpanded((x) => !x)} aria-expanded={expanded}>
          {expanded ? "▼" : "▶"}
        </button>
        <div className="collapseTitle">{title}</div>
        <div style={{ marginLeft: "auto" }}>{headerRight}</div>
      </div>
      {expanded ? <div className="collapseBody">{children}</div> : null}
    </div>
  );
}

