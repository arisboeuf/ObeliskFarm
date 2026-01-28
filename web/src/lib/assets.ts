export function assetUrl(relativePath: string): string {
  // Vite serves `public/` at BASE_URL.
  const base = import.meta.env.BASE_URL ?? "/";
  return `${base}${relativePath.replace(/^\/+/, "")}`;
}

