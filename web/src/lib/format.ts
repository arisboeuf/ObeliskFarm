export function formatInt(n: number): string {
  if (!Number.isFinite(n)) return String(n);
  return Math.trunc(n).toLocaleString("en-US");
}

export function formatTime(seconds: number): string {
  if (!Number.isFinite(seconds)) return String(seconds);
  if (seconds < 60) return `${seconds.toFixed(1)}s`;
  const minutes = Math.floor(seconds / 60);
  const secs = seconds % 60;
  if (minutes < 60) return `${minutes}m ${Math.round(secs)}s`;
  const hours = Math.floor(minutes / 60);
  const mins = minutes % 60;
  return `${hours}h ${mins}m ${Math.round(secs)}s`;
}

