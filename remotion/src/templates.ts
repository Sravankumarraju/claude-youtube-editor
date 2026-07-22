// Typed loader for templates.json. Resolves each template into a full `Theme`
// (colors + gradient + radius + loaded font families) the storyboard engine
// consumes. The JSON is the shared source of truth (Python reads it too).
import data from './templates.json';
import { displayFont, bodyFont, monoFont } from './lib/fontcatalog';

export type Theme = {
  accent: string; accent2: string; signal: string; warn: string; danger: string;
  ink: string; muted: string; paper: string; cream: string; line: string;
  d900: string; d800: string; d600: string; d400: string; d300: string;
  gradient: string;
  radius: { card: number; panel: number; window: number; pill: number };
  fontDisplay: string; fontBody: string; fontMono: string;
};

export type Template = {
  id: string;
  name: string;
  description: string;
  theme: Theme;
  layout: { pacing: number; order: string[]; captionsDefault: boolean };
};

type RawTemplate = (typeof data.templates)[number];

const resolve = (t: RawTemplate): Template => {
  const c = t.colors;
  const g = t.gradient;
  return {
    id: t.id,
    name: t.name,
    description: t.description,
    theme: {
      ...c,
      gradient: `linear-gradient(120deg, ${g[0]}, ${g[1]}, ${g[2]})`,
      radius: t.radius,
      fontDisplay: displayFont(t.fonts.display),
      fontBody: bodyFont(t.fonts.body),
      fontMono: monoFont(t.fonts.mono),
    },
    layout: t.layout,
  };
};

export const TEMPLATES: Template[] = data.templates.map(resolve);

export const DEFAULT_TEMPLATE: Template =
  TEMPLATES.find((t) => t.id === 'brand') ?? TEMPLATES[0];

export const getTemplate = (id?: string): Template =>
  (id ? TEMPLATES.find((t) => t.id === id) : undefined) ?? DEFAULT_TEMPLATE;

export const DEFAULT_THEME: Theme = DEFAULT_TEMPLATE.theme;
