export type Theme = "system" | "light" | "dark";

const KEY = "cm.theme";

export function loadTheme(): Theme {
  const v = localStorage.getItem(KEY);
  return v === "light" || v === "dark" ? v : "system";
}

/** Applies the theme to <html> and remembers it. System follows the OS. */
export function applyTheme(theme: Theme): void {
  localStorage.setItem(KEY, theme);
  const root = document.documentElement;
  if (theme === "system") delete root.dataset.theme;
  else root.dataset.theme = theme;
}

export const THEMES: { id: Theme; label: string; icon: string }[] = [
  { id: "system", label: "시스템", icon: "🖥️" },
  { id: "light", label: "라이트", icon: "☀️" },
  { id: "dark", label: "다크", icon: "🌙" },
];
