// Data-driven faceless-video engine. One set of scene renderers driven by a
// storyboard (JSON), adapting to landscape or vertical, with an optional caption
// track. This is the reuse keystone for source-to-video: a generator emits a thin
// shot file that embeds a Scene[] and renders <StoryboardVideo/>.
//
// Look is theme-driven: a `templateId` selects colors + fonts + radius from
// templates.ts (default = the brand theme). Frame-based only; every interpolate
// is monotonic + clamped. Reuses useRise / CLAMP for brand motion.
import React from 'react';
import { AbsoluteFill, interpolate, useCurrentFrame, useVideoConfig, Series, Audio, staticFile } from 'remotion';
import { Star, MousePointer2 } from 'lucide-react';
import { SHADOW, EASINGS } from '../brand';
import { getTemplate, DEFAULT_THEME, type Theme } from '../templates';
import { useRise, CLAMP } from './kit';
import { WebBrowserFrame, chromeH } from './browser';

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
  | { type: 'repo_scroll'; dur: number; eyebrow?: string; glow?: string; narration?: string; audio?: string; repo: RepoView }
  | { type: 'cta'; dur: number; title: string; sub?: string; glow?: string; narration?: string; audio?: string };

// The GitHub page shown in the repo-scroll scene (filled by the generator from source.json).
export type RepoView = {
  owner: string; name: string; url: string;
  stars?: number; description?: string; topics?: string[];
  readme?: string[]; files?: string[];
};

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

// ---- repo scroll-&-explain ------------------------------------------------
const formatStars = (n?: number): string =>
  n == null ? '' : n >= 1000 ? `${(n / 1000).toFixed(n >= 10000 ? 0 : 1)}k` : String(n);

// One fixed-height README row (heading / bullet / paragraph) — fixed height so
// the scroll distance is computed exactly, with no layout measurement.
const ReadmeLine: React.FC<{ text: string; h: number; theme: Theme }> = ({ text, h, theme }) => {
  const base = { height: h, display: 'flex', alignItems: 'center', boxSizing: 'border-box' as const };
  if (text.startsWith('## '))
    return <div style={{ ...base, fontFamily: theme.fontDisplay, fontWeight: 700, fontSize: 30, color: theme.d300, borderBottom: `1px solid ${theme.d600}` }}>{clip(text.slice(3), 58)}</div>;
  if (text.startsWith('- '))
    return <div style={{ ...base, gap: 14, fontSize: 25, color: theme.d300 }}><span style={{ width: 8, height: 8, borderRadius: '50%', background: theme.accent, flex: '0 0 auto' }} />{clip(text.slice(2), 78)}</div>;
  return <div style={{ ...base, fontSize: 25, color: theme.d400 }}>{clip(text, 88)}</div>;
};

const RepoScrollScene: React.FC<{ s: Extract<Scene, { type: 'repo_scroll' }>; f: Fmt }> = ({ s, f }) => {
  const frame = useCurrentFrame();
  const theme = useTheme();
  const { width, height } = useVideoConfig();
  const repo = s.repo;
  const glow = s.glow ?? theme.accent;
  if (!repo || !repo.name) return <Frame glow={glow} f={f}><div /></Frame>;

  const uiScale = pick(f.vertical, 1.6, 1);
  const marginX = pick(f.vertical, 40, 120);
  const top = pick(f.vertical, 150, 96);
  const bottomSafe = f.captions ? pick(f.vertical, 300, 190) : pick(f.vertical, 70, 70);
  const box = { x: marginX, y: top, w: width - marginX * 2, h: height - top - bottomSafe };
  const viewportH = box.h - chromeH(uiScale);

  const files = (repo.files || []).slice(0, 12);
  const readme = (repo.readme || []).slice(0, 26);
  const HEADER = 236, PANELHDR = 62, FILEROW = 56, LINE = 48, PAD = 90;
  const filesH = files.length ? 24 + PANELHDR + files.length * FILEROW : 0;
  const readmeH = 24 + PANELHDR + 24 + readme.length * LINE;
  const contentH = HEADER + filesH + readmeH + PAD;
  const maxScroll = Math.max(0, contentH - viewportH);
  const scrollY = interpolate(frame, [14, Math.max(30, s.dur - 22)], [0, maxScroll], { ...CLAMP, easing: EASINGS.easeInOut });
  const progress = maxScroll > 0 ? scrollY / maxScroll : 0;

  // interactive chrome: a scrollbar thumb + a drifting cursor over the page
  const trackTop = box.y + chromeH(uiScale);
  const trackH = viewportH;
  const thumbH = Math.max(48, trackH * Math.min(1, viewportH / contentH));
  const thumbY = trackTop + progress * (trackH - thumbH);
  const barOp = interpolate(frame, [10, 22], [0, 1], CLAMP);
  const curX = box.x + box.w * 0.4 + Math.sin(frame / 22) * 14;
  const curY = trackTop + viewportH * 0.28 + progress * viewportH * 0.4;
  const curOp = interpolate(frame, [16, 28], [0, 0.92], CLAMP);

  const panel = { margin: '24px 44px 0', border: `1px solid ${theme.d600}`, borderRadius: 12, overflow: 'hidden' as const };
  const panelHdr = { height: PANELHDR, display: 'flex', alignItems: 'center', padding: '0 24px', background: theme.d800, fontFamily: theme.fontMono, fontSize: 24, fontWeight: 600, color: theme.d300 };

  const page = (
    <div style={{ minHeight: contentH, background: theme.d900, color: theme.d300 }}>
      <div style={{ height: HEADER, padding: '34px 44px', boxSizing: 'border-box', borderBottom: `1px solid ${theme.d600}` }}>
        <div style={{ fontFamily: theme.fontDisplay, fontSize: 46 }}>
          <span style={{ color: theme.d400 }}>{repo.owner} / </span>
          <span style={{ color: theme.accent, fontWeight: 700 }}>{repo.name}</span>
        </div>
        {repo.description && <div style={{ fontSize: 27, color: theme.d400, marginTop: 16, maxWidth: '92%' }}>{clip(repo.description, 108)}</div>}
        <div style={{ display: 'flex', alignItems: 'center', gap: 20, marginTop: 22, flexWrap: 'wrap' }}>
          {repo.stars != null && (
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, color: theme.d300, fontFamily: theme.fontMono, fontSize: 24 }}>
              <Star size={22} color={theme.warn} fill={theme.warn} /> {formatStars(repo.stars)}
            </div>
          )}
          {(repo.topics || []).slice(0, 4).map((t) => (
            <span key={t} style={{ fontFamily: theme.fontMono, fontSize: 19, color: theme.accent, background: `${theme.accent}1f`, border: `1px solid ${theme.accent}55`, borderRadius: 999, padding: '5px 14px' }}>{t}</span>
          ))}
        </div>
      </div>

      {files.length > 0 && (
        <div style={panel}>
          <div style={panelHdr}>Files</div>
          {files.map((fn) => (
            <div key={fn} style={{ height: FILEROW, display: 'flex', alignItems: 'center', gap: 16, padding: '0 24px', borderTop: `1px solid ${theme.d600}` }}>
              <span style={{ width: 22, height: 22, borderRadius: 5, flex: '0 0 auto', background: fn.includes('.') ? theme.accent : theme.warn, opacity: 0.85 }} />
              <span style={{ fontFamily: theme.fontMono, fontSize: 24, color: theme.d300 }}>{clip(fn, 46)}</span>
            </div>
          ))}
        </div>
      )}

      <div style={panel}>
        <div style={panelHdr}>README.md</div>
        <div style={{ padding: '12px 30px' }}>
          {readme.map((ln, i) => <ReadmeLine key={i} text={ln} h={LINE} theme={theme} />)}
        </div>
      </div>
    </div>
  );

  return (
    <AbsoluteFill style={{ fontFamily: theme.fontBody }}>
      <ThemedBg glow={glow} theme={theme} />
      {s.eyebrow && (
        <div style={{ position: 'absolute', top: pick(f.vertical, 74, 40), left: 0, right: 0, textAlign: 'center', fontFamily: theme.fontMono, fontSize: pick(f.vertical, 24, 26), letterSpacing: 3, color: glow }}>
          {s.eyebrow.toUpperCase()}
        </div>
      )}
      <WebBrowserFrame url={repo.url} tabTitle={`${repo.owner}/${repo.name}`} box={box} uiScale={uiScale} pageBg={theme.d900} scrollY={scrollY}>
        {page}
      </WebBrowserFrame>
      {/* scrollbar thumb */}
      {maxScroll > 0 && (
        <div style={{ position: 'absolute', left: box.x + box.w - 16, top: thumbY, width: 7, height: thumbH, borderRadius: 999, background: theme.d400, opacity: barOp * 0.6 }} />
      )}
      {/* drifting cursor — reads as someone browsing the repo */}
      <div style={{ position: 'absolute', left: curX, top: curY, opacity: curOp, filter: 'drop-shadow(0 2px 6px rgba(0,0,0,0.5))' }}>
        <MousePointer2 size={40} color="#ffffff" fill="#ffffff" strokeWidth={1.5} />
      </div>
    </AbsoluteFill>
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
    case 'repo_scroll': return <RepoScrollScene s={s} f={f} />;
    case 'cta': return <CtaScene s={s} f={f} />;
    default: return null;
  }
};

// ---- caption band (chunked, YouTube-style) --------------------------------
// Split narration into short phrases (<=6 words, breaking on clause punctuation)
// so captions read one crisp line at a time instead of a wall of text.
const chunkText = (t: string): string[] => {
  const words = t.split(/\s+/).filter(Boolean);
  const chunks: string[] = [];
  let cur: string[] = [];
  for (const w of words) {
    cur.push(w);
    const clause = /[.,!?;:]$/.test(w);
    if (cur.length >= 6 || (clause && cur.length >= 3)) {
      chunks.push(cur.join(' '));
      cur = [];
    }
  }
  if (cur.length) chunks.push(cur.join(' '));
  return chunks;
};

const Caption: React.FC<{ text: string; dur: number; vertical: boolean }> = ({ text, dur, vertical }) => {
  const frame = useCurrentFrame();
  const theme = useTheme();
  const clean = stripEmoji(text);
  if (!clean) return null;
  const chunks = chunkText(clean);
  const totalWords = chunks.reduce((a, c) => a + c.split(' ').length, 0) || 1;
  const startF = 2;
  const endF = Math.max(startF + 6, dur - 2);
  const span = endF - startF;
  // give each chunk a window proportional to its word count (tracks speech pace)
  let acc = 0;
  const wins = chunks.map((c) => {
    const s = startF + (span * acc) / totalWords;
    acc += c.split(' ').length;
    return [s, startF + (span * acc) / totalWords] as const;
  });
  let idx = wins.findIndex(([s, e]) => frame >= s && frame < e);
  if (idx < 0) idx = frame < startF ? 0 : chunks.length - 1;
  const [s] = wins[idx];
  const op = interpolate(frame, [s, s + 4], [0, 1], CLAMP);
  const pop = interpolate(frame, [s, s + 6], [0.94, 1], { ...CLAMP, easing: EASINGS.easeOut });
  return (
    <div style={{
      position: 'absolute', left: 0, right: 0, bottom: pick(vertical, 170, 84),
      display: 'flex', justifyContent: 'center', padding: '0 60px',
    }}>
      <div style={{
        maxWidth: pick(vertical, '94%', 1500), textAlign: 'center',
        background: 'rgba(9,12,18,0.9)', color: '#ffffff', borderRadius: 16,
        padding: pick(vertical, '16px 30px', '14px 34px'),
        boxShadow: '0 8px 30px rgba(0,0,0,0.35)',
        opacity: op, transform: `scale(${pop})`,
        fontFamily: theme.fontBody, fontWeight: 700, fontSize: pick(vertical, 48, 40),
        lineHeight: 1.25, letterSpacing: 0.2, whiteSpace: 'nowrap',
      }}>
        {chunks[idx]}
      </div>
    </div>
  );
};

// Cross-dissolve: fade each scene in/out over a persistent background so cuts
// become smooth dissolves (no hard jumps, no black flashes).
const SceneFade: React.FC<{ dur: number; children: React.ReactNode }> = ({ dur, children }) => {
  const frame = useCurrentFrame();
  const t = Math.min(9, Math.floor(dur / 3));
  const op = interpolate(frame, [0, t, dur - t, dur], [0, 1, 1, 0], CLAMP);
  return <AbsoluteFill style={{ opacity: op }}>{children}</AbsoluteFill>;
};

// ---- the video -------------------------------------------------------------
export const StoryboardVideo: React.FC<{ scenes: Scene[]; width: number; height: number; captions?: boolean; templateId?: string }> = ({ scenes, width, height, captions = false, templateId }) => {
  const vertical = height > width;
  const f: Fmt = { vertical, captions };
  const theme = getTemplate(templateId).theme;
  return (
    <ThemeContext.Provider value={theme}>
      {/* persistent background so scene cross-fades never flash to black */}
      <AbsoluteFill><ThemedBg glow={theme.accent} theme={theme} /></AbsoluteFill>
      <Series>
        {scenes.map((s, i) => {
          const D = Math.max(1, Math.round(s.dur));
          return (
            <Series.Sequence key={i} durationInFrames={D}>
              <SceneFade dur={D}><RenderScene s={s} f={f} /></SceneFade>
              {captions && s.narration ? <Caption text={s.narration} dur={D} vertical={vertical} /> : null}
              {s.audio ? <Audio src={staticFile(s.audio)} /> : null}
            </Series.Sequence>
          );
        })}
      </Series>
    </ThemeContext.Provider>
  );
};

// Sum scene durations (frames) — used by generators to set durationInSeconds.
export const totalFrames = (scenes: Scene[]): number => scenes.reduce((a, s) => a + Math.max(1, Math.round(s.dur)), 0);
