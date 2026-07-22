// Curated font catalog for video templates. Every family a template can name
// (templates.json -> fonts.display/body/mono) MUST be statically imported here
// so Remotion bundles it — arbitrary/dynamic family names would break the build.
// AI-generated templates must also pick keys from these lists.
import { loadFont as spaceGrotesk } from '@remotion/google-fonts/SpaceGrotesk';
import { loadFont as sora } from '@remotion/google-fonts/Sora';
import { loadFont as archivo } from '@remotion/google-fonts/Archivo';
import { loadFont as poppins } from '@remotion/google-fonts/Poppins';
import { loadFont as fraunces } from '@remotion/google-fonts/Fraunces';
import { loadFont as inter } from '@remotion/google-fonts/Inter';
import { loadFont as manrope } from '@remotion/google-fonts/Manrope';
import { loadFont as dmSans } from '@remotion/google-fonts/DMSans';
import { loadFont as jetBrainsMono } from '@remotion/google-fonts/JetBrainsMono';
import { loadFont as ibmPlexMono } from '@remotion/google-fonts/IBMPlexMono';
import { loadFont as firaCode } from '@remotion/google-fonts/FiraCode';

// Each family loaded once; `.fontFamily` is the CSS name to use in styles.
const DISPLAY: Record<string, string> = {
  SpaceGrotesk: spaceGrotesk('normal', { weights: ['500', '600', '700'], subsets: ['latin'] }).fontFamily,
  Sora: sora('normal', { weights: ['500', '600', '700'], subsets: ['latin'] }).fontFamily,
  Archivo: archivo('normal', { weights: ['500', '600', '700'], subsets: ['latin'] }).fontFamily,
  Poppins: poppins('normal', { weights: ['500', '600', '700'], subsets: ['latin'] }).fontFamily,
  Fraunces: fraunces('normal', { weights: ['500', '600', '700'], subsets: ['latin'] }).fontFamily,
};
const BODY: Record<string, string> = {
  Inter: inter('normal', { weights: ['400', '500', '600'], subsets: ['latin'] }).fontFamily,
  Manrope: manrope('normal', { weights: ['400', '500', '600'], subsets: ['latin'] }).fontFamily,
  DMSans: dmSans('normal', { weights: ['400', '500', '600'], subsets: ['latin'] }).fontFamily,
  Poppins: DISPLAY.Poppins,
};
const MONO: Record<string, string> = {
  JetBrainsMono: jetBrainsMono('normal', { weights: ['400', '500', '700'], subsets: ['latin'] }).fontFamily,
  IBMPlexMono: ibmPlexMono('normal', { weights: ['400', '500', '600'], subsets: ['latin'] }).fontFamily,
  FiraCode: firaCode('normal', { weights: ['400', '500', '700'], subsets: ['latin'] }).fontFamily,
};

// Resolve a template font key to a loaded CSS family, falling back to the brand
// default if a template names something not in the catalog.
export const displayFont = (key?: string): string => (key && DISPLAY[key]) || DISPLAY.SpaceGrotesk;
export const bodyFont = (key?: string): string => (key && BODY[key]) || BODY.Inter;
export const monoFont = (key?: string): string => (key && MONO[key]) || MONO.JetBrainsMono;

// Names the UI / AI generator may choose from.
export const FONT_CHOICES = {
  display: Object.keys(DISPLAY),
  body: Object.keys(BODY),
  mono: Object.keys(MONO),
};
