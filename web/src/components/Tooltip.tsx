import { useEffect, useMemo, useRef, useState } from "react";

type TooltipContent =
  | {
      title: string;
      lines: string[];
    }
  | {
      title: string;
      sections: Array<{ heading: string; lines: string[] }>;
    };

function clamp(n: number, min: number, max: number): number {
  return Math.max(min, Math.min(max, n));
}

export function Tooltip(props: { content: TooltipContent; label?: string }) {
  const { content, label = "?" } = props;
  const anchorRef = useRef<HTMLButtonElement | null>(null);
  const tipRef = useRef<HTMLDivElement | null>(null);
  const [open, setOpen] = useState(false);
  const [pos, setPos] = useState<{ left: number; top: number } | null>(null);

  const rendered = useMemo(() => {
    if ("lines" in content) {
      return (
        <>
          <div className="tooltipTitle">{content.title}</div>
          {content.lines.map((l, i) => (
            <div className="tooltipLine" key={i}>
              {l}
            </div>
          ))}
        </>
      );
    }
    return (
      <>
        <div className="tooltipTitle">{content.title}</div>
        {content.sections.map((s, si) => (
          <div className="tooltipSection" key={si}>
            <div className="tooltipHeading">{s.heading}</div>
            {s.lines.map((l, li) => (
              <div className="tooltipLine" key={li}>
                {l}
              </div>
            ))}
          </div>
        ))}
      </>
    );
  }, [content]);

  function computePosition() {
    const a = anchorRef.current;
    const t = tipRef.current;
    if (!a || !t) return;

    const ar = a.getBoundingClientRect();
    const tr = t.getBoundingClientRect();
    const margin = 10;

    // Prefer right of the icon, otherwise below.
    const preferredLeft = ar.right + 10;
    const preferredTop = ar.top - 6;

    const vw = window.innerWidth;
    const vh = window.innerHeight;

    let left = preferredLeft;
    let top = preferredTop;

    if (left + tr.width + margin > vw) {
      left = ar.left - tr.width - 10;
    }
    if (left < margin) {
      left = margin;
    }

    top = clamp(top, margin, vh - tr.height - margin);

    setPos({ left: Math.round(left), top: Math.round(top) });
  }

  useEffect(() => {
    if (!open) return;
    // Wait for tooltip to render before measuring.
    const id = window.requestAnimationFrame(() => computePosition());
    const onScroll = () => computePosition();
    const onResize = () => computePosition();
    window.addEventListener("scroll", onScroll, true);
    window.addEventListener("resize", onResize);
    return () => {
      window.cancelAnimationFrame(id);
      window.removeEventListener("scroll", onScroll, true);
      window.removeEventListener("resize", onResize);
    };
  }, [open]);

  return (
    <span className="tooltipWrap">
      <button
        ref={anchorRef}
        type="button"
        className="qmark"
        aria-label="Help"
        onMouseEnter={() => setOpen(true)}
        onMouseLeave={() => setOpen(false)}
        onFocus={() => setOpen(true)}
        onBlur={() => setOpen(false)}
      >
        {label}
      </button>
      {open ? (
        <div
          ref={tipRef}
          className="tooltipPop"
          style={pos ? { left: pos.left, top: pos.top } : undefined}
          role="tooltip"
        >
          {rendered}
        </div>
      ) : null}
    </span>
  );
}

