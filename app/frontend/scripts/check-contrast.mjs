#!/usr/bin/env node
/**
 * Build-time contrast check (docs/web-ui-design.md §1.3).
 *
 * Reads the token blocks out of src/styles/tokens.css and asserts the floors:
 *   4.5:1 body text · 3:1 large text, icons and UI boundaries.
 * A failing pair fails the build. Tune a colour, don't lower the floor.
 */
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";

const here = dirname(fileURLToPath(import.meta.url));
const css = readFileSync(join(here, "..", "src", "styles", "tokens.css"), "utf8");

function block(selector) {
  const i = css.indexOf(selector);
  if (i < 0) throw new Error(`selector not found: ${selector}`);
  const body = css.slice(css.indexOf("{", i) + 1, css.indexOf("}", i));
  const out = {};
  for (const m of body.matchAll(/--([a-z0-9-]+)\s*:\s*(#[0-9a-fA-F]{3,8})/g)) out[m[1]] = m[2];
  return out;
}

const THEMES = {
  light: block('[data-theme="light"]'),
  dark: block('[data-theme="dark"]'),
};

function hexToRgb(h) {
  h = h.replace("#", "");
  if (h.length === 3) h = h.split("").map((c) => c + c).join("");
  return [0, 2, 4].map((i) => parseInt(h.slice(i, i + 2), 16) / 255);
}

function luminance(hex) {
  const [r, g, b] = hexToRgb(hex).map((c) => (c <= 0.03928 ? c / 12.92 : Math.pow((c + 0.055) / 1.055, 2.4)));
  return 0.2126 * r + 0.7152 * g + 0.0722 * b;
}

function ratio(a, b) {
  const la = luminance(a), lb = luminance(b);
  const [hi, lo] = la > lb ? [la, lb] : [lb, la];
  return (hi + 0.05) / (lo + 0.05);
}

const TEXT = 4.5;   // body text
const NON_TEXT = 3; // large text, icons, UI boundaries and states

const PAIRS = [
  ["fg on bg", "fg", "bg", TEXT],
  ["fg on surface", "fg", "surface", TEXT],
  ["fg muted on surface", "fg-muted", "surface", TEXT],
  ["primary as text on bg", "primary", "bg", TEXT],
  ["primary fg on primary", "primary-fg", "primary", TEXT],
  ["success on surface", "success", "surface", TEXT],
  ["warning on surface", "warning", "surface", TEXT],
  ["danger on surface", "danger", "surface", TEXT],
  ["border on bg", "border", "bg", NON_TEXT],
  ["border on surface", "border", "surface", NON_TEXT],
  ["focus ring on bg", "focus", "bg", NON_TEXT],
];

let failed = 0;
for (const [themeName, tokens] of Object.entries(THEMES)) {
  console.log(`\n${themeName}`);
  for (const [label, fgKey, bgKey, floor] of PAIRS) {
    const fg = tokens[fgKey], bg = tokens[bgKey];
    if (!fg || !bg) {
      console.log(`  !! ${label}: missing token (${fgKey}=${fg} ${bgKey}=${bg})`);
      failed++;
      continue;
    }
    const r = ratio(fg, bg);
    const ok = r >= floor;
    if (!ok) failed++;
    console.log(`  ${ok ? "ok  " : "FAIL"} ${label.padEnd(26)} ${r.toFixed(2)}:1  (>= ${floor})`);
  }
}

console.log("");
if (failed) {
  console.error(`${failed} contrast pair(s) below the floor.`);
  process.exit(1);
}
console.log("all contrast pairs pass.");
