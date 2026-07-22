// Data-driven faceless-video engine. One set of scene renderers driven by a
// storyboard (JSON), adapting to landscape or vertical, with an optional caption
// track. This is the reuse keystone for source-to-video: a generator emits a thin
// shot file that embeds a Scene[] and renders <StoryboardVideo/>.
//
// Look is theme-driven: a `templateId` selects colors + fonts + radius from
// templates.ts (default = the brand theme). Frame-based only; every interpolate
// is monotonic + clamped. Reuses useRise / CLAMP for brand motion.
import React from 'react';
import { AbsoluteFill, interpolate, useCurrentFrame, Series, Audio, staticFile } from 'remotion';
import { SHADOW, EASINGS } from '../brand';
import { getTemplate, DEFAULT_THEME, type Theme } from '../templates';
import { useRise, CLAMP } from './kit';

// Brand motion easing (not themed) — reused by every scene's enter animation.
const EASE = EASINGS.easeOut;

// ---- theme context ---------------------------------------------------------
const ThemeContext = React.createContext<Theme>(DEFAULT_THEME);
const useTheme = (): Theme => React.useContext(ThemeContext);

// ---- Scene data model ------------------------------------------------------
// `audio` is a staticFile-relative path (under media/) to a narration clip for
// this scene; `narration` is the caption/voiceover text.
export type Scene =
  | { type: 'title'; dur: number; eyebrow?: string; title: string; subtitle?: string; glow?: string; narration?: string; audio?: string }
  | { type: 'statement'; dur: number; eyebrow?: string; text: string; glow?: string; narration?: string; audio?: string }
  | { type: 'features'; dur: number; eyebrow?: string; items: { label: string; value?: string }[]; glow?: string; narration?: string; audio?: string }
  | { type: 'steps'; dur: number; eyebrow?: string; steps: string[]; glow?: string; narration?: string; audio?: string }
  | { type: 'code'; dur: number; eyebrow?: string; filename?: string; lines: string[]; glow?: string; narration?: string; audio?: string }
  | { type: 'bullets'; dur: number; eyebrow?: string; title?: string; points: string[]; glow?: string; narration?: string; audio?: string }
  | { type: 'cta'; dur: number; title: string; sub?: string; glow?: string; narration?: string; audio?: string };

type Fmt = { vertical: boolean; captions: boolean };

// A tiny responsive helper: pick a value for landscape vs vertical.
const pick = <A, B>(v: boolean, land: A, vert: B): A | B => (v ? vert : land);

// Clamp overlong extracted text so it never wraps past its scene.
const clip = (s: string, n: number): string => (s.length > n ? s.slice(0, n - 1).trimEnd() + '…' : s);

// Strip emoji/pictographs (and the whitespace they leave) so captions never
// show 🚀🤖 — the caption text mirrors the voice-over, which also drops emoji.
// Extended_Pictographic covers the emoji themselves; the extra ranges catch
// regional-indicator flags, variation selectors and ZWJ sequences.
const stripEmoji = (s: string): string =>
  s
    .replace(/[\p{Extended_Pictographic}\u{1F1E6}-\u{1F1FF}\u{FE00}-\u{FE0F}\u{200D}]/gu, '')
    .replace(/\s{2,}/g, ' ')
    .replace(/\s+([;,.!?])/g, '$1')
    .trim();

// Themed background (replaces the brand-locked BrandBg so palettes apply).
const ThemedBg: React.FC<{ glow: string; theme: Theme }> = ({ glow, theme }) => (
  <>
    <AbsoluteFill style={{ backgroundColor: theme.paper }} />
    <AbsoluteFill style={{ background: `radial-gradient(1300px 700px at 50% -12%, ${glow}22, transparent 60%)` }} />
    <AbsoluteFill style={{ backgroundImage: `radial-gradient(${theme.line} 1.5px, transparent 1.5px)`, backgroundSize: '46px 46px', opacity: 0.45 }} />
  </>
);

// ---- shared chrome ---------------------------------------------------------
const Eyebrow: React.FC<{ text?: string; color: string; vertical: boolean }> = ({ text, color, vertical }) => {
  const rise = useRise();
  const theme = useTheme();
  if (!text) return null;
  return (
    <div style={{ ...rise(4, 14), fontFamily: theme.fontMono, fontSize: pick(vertical, 24, 28), letterSpacing: 3, color, marginBottom: pick(vertical, 30, 40), textAlign: 'center' }}>
      {text.toUpperCase()}
    </div>
  );
};

const Frame: React.FC<{ glow: string; f: Fmt; children: React.ReactNode }> = ({ glow, f, children }) => {
  const theme = useTheme();
  return (
    <AbsoluteFill style={{ fontFamily: theme.fontBody }}>
      <ThemedBg glow={glow} theme={theme} />
      <AbsoluteFill style={{
        alignItems: 'center', justifyContent: 'center',
        paddingLeft: pick(f.vertical, 70, 160), paddingRight: pick(f.vertical, 70, 160),
        // reserve a safe area at the bottom so content never collides with captions
        paddingBottom: f.captions ? pick(f.vertical, 300, 180) : 0,
      }}>
        {children}
      </AbsoluteFill>
    </AbsoluteFill>
  );
};

// ---- scene renderers -------------------------------------------------------
const TitleScene: React.FC<{ s: Extract<Scene, { type: 'title' }>; f: Fmt }> = ({ s, f }) => {
  const rise = useRise();
  const theme = useTheme();
  const glow = s.glow ?? theme.accent;
  return (
    <Frame glow={glow} f={f}>
      <Eyebrow text={s.eyebrow} color={glow} vertical={f.vertical} />
      <div style={{ ...rise(10, 20), fontFamily: theme.fontDisplay, fontWeight: 700, fontSize: pick(f.vertical, 84, 104), letterSpacing: -1, color: theme.ink, lineHeight: 1.02, textAlign: 'center' }}>
        {s.title}
      </div>
      {s.subtitle && (
        <div style={{ ...rise(22, 16), fontSize: pick(f.vertical, 38, 44), color: theme.muted, marginTop: 28, textAlign: 'center' }}>{s.subtitle}</div>
      )}
    </Frame>
  );
};

const StatementScene: React.FC<{ s: Extract<Scene, { type: 'statement' }>; f: Fmt }> = ({ s, f }) => {
  const rise = useRise();
  const theme = useTheme();
  const glow = s.glow ?? theme.accent2;
  return (
    <Frame glow={glow} f={f}>
      <Eyebrow text={s.eyebrow} color={glow} vertical={f.vertical} />
      <div style={{ ...rise(10, 22), fontFamily: theme.fontDisplay, fontWeight: 600, fontSize: pick(f.vertical, 56, 64), lineHeight: 1.2, color: theme.ink, textAlign: 'center' }}>
        {clip(s.text, 180)}
      </div>
    </Frame>
  );
};

const FeaturesScene: React.FC<{ s: Extract<Scene, { type: 'features' }>; f: Fmt }> = ({ s, f }) => {
  const frame = useCurrentFrame();
  const theme = useTheme();
  const glow = s.glow ?? theme.accent;
  const palette = [theme.accent, theme.signal, theme.accent2, theme.warn, theme.danger];
  return (
    <Frame glow={glow} f={f}>
      <Eyebrow text={s.eyebrow} color={glow} vertical={f.vertical} />
      <div style={{ display: 'flex', flexDirection: pick(f.vertical, 'column', 'row'), gap: pick(f.vertical, 20, 26), width: '100%', justifyContent: 'center', alignItems: 'stretch' }}>
        {s.items.slice(0, pick(f.vertical, 4, 3)).map((it, i) => {
          const start = 18 + i * 14;
          const op = interpolate(frame, [start, start + 16], [0, 1], { ...CLAMP, easing: EASE });
          const y = interpolate(frame, [start, start + 16], [30, 0], { ...CLAMP, easing: EASE });
          const c = palette[i % palette.length];
          return (
            <div key={it.label} style={{
              opacity: op, transform: `translateY(${y}px)`,
              flex: pick(f.vertical, '0 0 auto', '1 1 0'), maxWidth: pick(f.vertical, '100%', 460),
              background: theme.cream, border: `1px solid ${theme.line}`, borderRadius: theme.radius.card, boxShadow: SHADOW.card,
              padding: pick(f.vertical, '26px 30px', '38px 34px'),
              display: 'flex', flexDirection: pick(f.vertical, 'row', 'column'), alignItems: pick(f.vertical, 'center', 'flex-start'), gap: 18,
            }}>
              <div style={{ width: 60, height: 60, flex: '0 0 auto', borderRadius: 16, background: `${c}1e`, display: 'flex', alignItems: 'center', justifyContent: 'center', fontFamily: theme.fontMono, fontWeight: 700, fontSize: 26, color: c }}>
                {String(i + 1).padStart(2, '0')}
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                <div style={{ fontFamily: theme.fontDisplay, fontWeight: 700, fontSize: pick(f.vertical, 36, 38), color: theme.ink }}>{clip(it.label, 30)}</div>
                {it.value && <div style={{ fontFamily: theme.fontMono, fontSize: pick(f.vertical, 22, 23), color: theme.muted }}>{it.value}</div>}
              </div>
            </div>
          );
        })}
      </div>
    </Frame>
  );
};

const StepsScene: React.FC<{ s: Extract<Scene, { type: 'steps' }>; f: Fmt }> = ({ s, f }) => {
  const frame = useCurrentFrame();
  const theme = useTheme();
  const glow = s.glow ?? theme.accent2;
  const steps = s.steps.slice(0, 6);
  return (
    <Frame glow={glow} f={f}>
      <Eyebrow text={s.eyebrow} color={glow} vertical={f.vertical} />
      <div style={{ display: 'flex', flexDirection: pick(f.vertical, 'column', 'row'), alignItems: 'center', justifyContent: 'center', gap: pick(f.vertical, 14, 12), flexWrap: 'wrap' }}>
        {steps.map((st, i) => {
          const start = 14 + i * 10;
          const op = interpolate(frame, [start, start + 12], [0, 1], { ...CLAMP, easing: EASE });
          const y = interpolate(frame, [start, start + 12], [22, 0], { ...CLAMP, easing: EASE });
          return (
            <React.Fragment key={st}>
              <div style={{
                opacity: op, transform: `translateY(${y}px)`,
                minWidth: pick(f.vertical, 300, 200), background: theme.cream, border: `1px solid ${theme.line}`,
                borderRadius: theme.radius.card, boxShadow: SHADOW.card, padding: pick(f.vertical, '20px 26px', '26px 24px'),
                display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 8,
              }}>
                <div style={{ fontFamily: theme.fontMono, fontSize: 20, color: theme.accent }}>{String(i + 1).padStart(2, '0')}</div>
                <div style={{ fontFamily: theme.fontDisplay, fontWeight: 700, fontSize: pick(f.vertical, 32, 32), color: theme.ink, textAlign: 'center' }}>{st}</div>
              </div>
              {i < steps.length - 1 && (
                <div style={{ opacity: op, fontFamily: theme.fontMono, fontSize: 28, color: theme.muted, transform: pick(f.vertical, 'rotate(90deg)', 'none') }}>→</div>
              )}
            </React.Fragment>
          );
        })}
      </div>
    </Frame>
  );
};

const CodeScene: React.FC<{ s: Extract<Scene, { type: 'code' }>; f: Fmt }> = ({ s, f }) => {
  const frame = useCurrentFrame();
  const rise = useRise();
  const theme = useTheme();
  const glow = s.glow ?? theme.accent;
  const lines = s.lines.slice(0, pick(f.vertical, 12, 14));
  return (
    <Frame glow={glow} f={f}>
      <Eyebrow text={s.eyebrow} color={glow} vertical={f.vertical} />
      <div style={{ ...rise(10, 18), width: pick(f.vertical, '100%', 1200), maxWidth: '100%', background: theme.d900, borderRadius: theme.radius.window, boxShadow: SHADOW.soft, overflow: 'hidden', border: `1px solid ${theme.d600}` }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '16px 20px', borderBottom: `1px solid ${theme.d600}` }}>
          <span style={{ width: 12, height: 12, borderRadius: '50%', background: '#ff5f56' }} />
          <span style={{ width: 12, height: 12, borderRadius: '50%', background: '#ffbd2e' }} />
          <span style={{ width: 12, height: 12, borderRadius: '50%', background: '#27c93f' }} />
          {s.filename && <span style={{ marginLeft: 14, fontFamily: theme.fontMono, fontSize: 20, color: theme.d400 }}>{s.filename}</span>}
        </div>
        <div style={{ padding: pick(f.vertical, '22px 24px', '28px 34px'), display: 'flex', flexDirection: 'column', gap: 6 }}>
          {lines.map((ln, i) => {
            const start = 16 + i * 4;
            const op = interpolate(frame, [start, start + 10], [0, 1], { ...CLAMP, easing: EASE });
            const isComment = ln.trim().startsWith('#') || ln.trim().startsWith('//');
            return (
              <div key={i} style={{ opacity: op, fontFamily: theme.fontMono, fontSize: pick(f.vertical, 24, 26), lineHeight: 1.5, color: isComment ? theme.d400 : theme.d300, whiteSpace: 'pre' }}>
                {ln || ' '}
              </div>
            );
          })}
        </div>
      </div>
    </Frame>
  );
};

const BulletsScene: React.FC<{ s: Extract<Scene, { type: 'bullets' }>; f: Fmt }> = ({ s, f }) => {
  const frame = useCurrentFrame();
  const rise = useRise();
  const theme = useTheme();
  const glow = s.glow ?? theme.accent;
  return (
    <Frame glow={glow} f={f}>
      <Eyebrow text={s.eyebrow} color={glow} vertical={f.vertical} />
      {s.title && <div style={{ ...rise(8, 16), fontFamily: theme.fontDisplay, fontWeight: 700, fontSize: pick(f.vertical, 52, 60), color: theme.ink, marginBottom: 34, textAlign: 'center' }}>{s.title}</div>}
      <div style={{ display: 'flex', flexDirection: 'column', gap: 18, width: pick(f.vertical, '100%', 1100) }}>
        {s.points.slice(0, 5).map((p, i) => {
          const start = 18 + i * 12;
          const op = interpolate(frame, [start, start + 14], [0, 1], { ...CLAMP, easing: EASE });
          const x = interpolate(frame, [start, start + 14], [-24, 0], { ...CLAMP, easing: EASE });
          return (
            <div key={i} style={{ opacity: op, transform: `translateX(${x}px)`, display: 'flex', alignItems: 'flex-start', gap: 18, background: theme.cream, border: `1px solid ${theme.line}`, borderRadius: theme.radius.card, boxShadow: SHADOW.card, padding: pick(f.vertical, '22px 26px', '24px 32px') }}>
              <div style={{ width: 14, height: 14, borderRadius: '50%', background: theme.gradient, flex: '0 0 auto', marginTop: pick(f.vertical, 10, 12) }} />
              <div style={{ fontFamily: theme.fontBody, fontWeight: 500, fontSize: pick(f.vertical, 32, 36), color: theme.ink, lineHeight: 1.35 }}>{clip(p, pick(f.vertical, 42, 66))}</div>
            </div>
          );
        })}
      </div>
    </Frame>
  );
};

const CtaScene: React.FC<{ s: Extract<Scene, { type: 'cta' }>; f: Fmt }> = ({ s, f }) => {
  const frame = useCurrentFrame();
  const rise = useRise();
  const theme = useTheme();
  const glow = s.glow ?? theme.signal;
  const barX = interpolate(frame, [10, 32], [0, 1], { ...CLAMP, easing: EASE });
  return (
    <Frame glow={glow} f={f}>
      <div style={{ ...rise(2, 20), fontFamily: theme.fontDisplay, fontWeight: 700, fontSize: pick(f.vertical, 68, 84), letterSpacing: -1, color: theme.ink, textAlign: 'center' }}>{s.title}</div>
      <div style={{ width: pick(f.vertical, 260, 360), height: 8, borderRadius: 999, background: theme.gradient, marginTop: 26, transform: `scaleX(${barX})` }} />
      {s.sub && <div style={{ ...rise(20, 16), fontFamily: theme.fontMono, fontSize: pick(f.vertical, 28, 34), color: theme.muted, marginTop: 34, textAlign: 'center' }}>{s.sub}</div>}
    </Frame>
  );
};

const RenderScene: React.FC<{ s: Scene; f: Fmt }> = ({ s, f }) => {
  switch (s.type) {
    case 'title': return <TitleScene s={s} f={f} />;
    case 'statement': return <StatementScene s={s} f={f} />;
    case 'features': return <FeaturesScene s={s} f={f} />;
    case 'steps': return <StepsScene s={s} f={f} />;
    case 'code': return <CodeScene s={s} f={f} />;
    case 'bullets': return <BulletsScene s={s} f={f} />;
    case 'cta': return <CtaScene s={s} f={f} />;
    default: return null;
  }
};

// ---- caption band ----------------------------------------------------------
const Caption: React.FC<{ text: string; dur: number; vertical: boolean }> = ({ text, dur, vertical }) => {
  const frame = useCurrentFrame();
  const theme = useTheme();
  const op = interpolate(frame, [4, 14, dur - 8, dur - 2], [0, 1, 1, 0], CLAMP);
  const clean = stripEmoji(text);
  if (!clean) return null;
  return (
    <div style={{
      position: 'absolute', left: 0, right: 0, bottom: pick(vertical, 150, 70),
      display: 'flex', justifyContent: 'center', padding: '0 60px', opacity: op,
    }}>
      <div style={{
        maxWidth: pick(vertical, '92%', 1400), textAlign: 'center',
        background: 'rgba(13,17,23,0.86)', color: '#f4f4f7', borderRadius: 14,
        padding: pick(vertical, '18px 26px', '16px 30px'),
        fontFamily: theme.fontBody, fontWeight: 600, fontSize: pick(vertical, 40, 34), lineHeight: 1.3,
      }}>
        {clean}
      </div>
    </div>
  );
};

// ---- the video -------------------------------------------------------------
export const StoryboardVideo: React.FC<{ scenes: Scene[]; width: number; height: number; captions?: boolean; templateId?: string }> = ({ scenes, width, height, captions = false, templateId }) => {
  const vertical = height > width;
  const f: Fmt = { vertical, captions };
  const theme = getTemplate(templateId).theme;
  return (
    <ThemeContext.Provider value={theme}>
      <Series>
        {scenes.map((s, i) => (
          <Series.Sequence key={i} durationInFrames={Math.max(1, Math.round(s.dur))}>
            <RenderScene s={s} f={f} />
            {captions && s.narration ? <Caption text={s.narration} dur={Math.max(1, Math.round(s.dur))} vertical={vertical} /> : null}
            {s.audio ? <Audio src={staticFile(s.audio)} /> : null}
          </Series.Sequence>
        ))}
      </Series>
    </ThemeContext.Provider>
  );
};

// Sum scene durations (frames) — used by generators to set durationInSeconds.
export const totalFrames = (scenes: Scene[]): number => scenes.reduce((a, s) => a + Math.max(1, Math.round(s.dur)), 0);
