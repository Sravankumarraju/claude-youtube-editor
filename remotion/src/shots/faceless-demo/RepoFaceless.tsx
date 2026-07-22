// Faceless demo video — a source-to-video explainer of THIS repo, built entirely
// from the existing kit (BrandBg / useRise / brand tokens). No footage, no keys,
// no GPU: renders via the Remotion renderer. Five scenes sequenced with <Series>.
// Frame-based only; every interpolate is monotonic + clamped.
import React from 'react';
import { AbsoluteFill, interpolate, useCurrentFrame, Series } from 'remotion';
import { Braces, Mic, Play } from 'lucide-react';
import { COLORS, EASINGS, RADIUS, SHADOW, GRADIENT } from '../../brand';
import { FONT_DISPLAY, FONT_BODY, FONT_MONO } from '../../fonts';
import { BrandBg, useRise, CLAMP } from '../../lib/kit';

export const compositionConfig = { id: 'RepoFaceless', durationInSeconds: 25, fps: 30, width: 1920, height: 1080 };

// ---- Scene 1 — title -------------------------------------------------------
const SceneTitle: React.FC = () => {
  const rise = useRise();
  return (
    <AbsoluteFill style={{ fontFamily: FONT_BODY }}>
      <BrandBg glow={COLORS.accent} />
      <AbsoluteFill style={{ alignItems: 'center', justifyContent: 'center' }}>
        <div style={{ ...rise(4, 14), fontFamily: FONT_MONO, fontSize: 28, letterSpacing: 6, color: COLORS.accent, marginBottom: 28 }}>
          OPEN-SOURCE&nbsp;·&nbsp;YOUTUBE&nbsp;PIPELINE
        </div>
        <div style={{ ...rise(10, 20), fontFamily: FONT_DISPLAY, fontWeight: 700, fontSize: 96, letterSpacing: -1, color: COLORS.ink, lineHeight: 1 }}>
          claude<span style={{ color: COLORS.accent }}>-youtube-</span>editor
        </div>
        <div style={{ ...rise(22, 16), fontSize: 44, color: COLORS.muted, marginTop: 30 }}>
          You record. Claude Code does the rest.
        </div>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};

// ---- Scene 2 — the idea ----------------------------------------------------
const SceneIdea: React.FC = () => {
  const rise = useRise();
  return (
    <AbsoluteFill style={{ fontFamily: FONT_BODY }}>
      <BrandBg glow={COLORS.accent2} />
      <AbsoluteFill style={{ alignItems: 'center', justifyContent: 'center', padding: '0 240px' }}>
        <div style={{ ...rise(4, 14), fontFamily: FONT_MONO, fontSize: 24, letterSpacing: 3, color: COLORS.accent2, marginBottom: 36 }}>THE&nbsp;IDEA</div>
        <div style={{ ...rise(10, 22), fontFamily: FONT_DISPLAY, fontWeight: 600, fontSize: 64, lineHeight: 1.2, color: COLORS.ink, textAlign: 'center' }}>
          Every on-screen moment is <span style={{ color: COLORS.accent }}>built as code</span> and composited over your cut. No screen recorder. No timeline to drag.
        </div>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};

// ---- Scene 3 — what it does (feature cards) --------------------------------
const FEATURES = [
  { Icon: Braces, label: 'Visuals as code', value: 'Remotion · no editor', color: COLORS.accent },
  { Icon: Mic, label: 'Clean voice + SFX', value: 'isolate · sound-design', color: COLORS.signal },
  { Icon: Play, label: 'Package + upload', value: 'titles · thumbs · draft', color: COLORS.accent2 },
];
const SceneFeatures: React.FC = () => {
  const frame = useCurrentFrame();
  const rise = useRise();
  return (
    <AbsoluteFill style={{ fontFamily: FONT_BODY }}>
      <BrandBg glow={COLORS.accent} />
      <AbsoluteFill style={{ alignItems: 'center', justifyContent: 'center' }}>
        <div style={{ ...rise(4, 14), fontFamily: FONT_MONO, fontSize: 24, letterSpacing: 3, color: COLORS.accent, marginBottom: 44 }}>WHAT&nbsp;IT&nbsp;DOES</div>
        <div style={{ display: 'flex', gap: 26 }}>
          {FEATURES.map((f, i) => {
            const s = 18 + i * 16;
            const op = interpolate(frame, [s, s + 16], [0, 1], { ...CLAMP, easing: EASINGS.easeOut });
            const y = interpolate(frame, [s, s + 16], [34, 0], { ...CLAMP, easing: EASINGS.easeOut });
            const Icon = f.Icon;
            return (
              <div key={f.label} style={{
                opacity: op, transform: `translateY(${y}px)`, width: 400,
                background: COLORS.paper, border: `1px solid ${COLORS.line}`,
                borderRadius: RADIUS.card, boxShadow: SHADOW.card,
                padding: '40px 34px', display: 'flex', flexDirection: 'column', gap: 22,
              }}>
                <div style={{ width: 84, height: 84, borderRadius: 20, background: `${f.color}18`, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                  <Icon size={42} color={f.color} strokeWidth={2.1} />
                </div>
                <div style={{ fontFamily: FONT_DISPLAY, fontWeight: 700, fontSize: 40, color: COLORS.ink }}>{f.label}</div>
                <div style={{ fontFamily: FONT_MONO, fontSize: 24, color: COLORS.muted }}>{f.value}</div>
              </div>
            );
          })}
        </div>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};

// ---- Scene 4 — the pipeline ------------------------------------------------
const STEPS = [
  { k: '01', t: 'cut' }, { k: '02', t: 'visuals' }, { k: '03', t: 'voice' },
  { k: '04', t: 'sfx' }, { k: '05', t: 'package' }, { k: '06', t: 'ship' },
];
const ScenePipeline: React.FC = () => {
  const frame = useCurrentFrame();
  const rise = useRise();
  return (
    <AbsoluteFill style={{ fontFamily: FONT_BODY }}>
      <BrandBg glow={COLORS.accent2} />
      <AbsoluteFill style={{ alignItems: 'center', justifyContent: 'center' }}>
        <div style={{ ...rise(4, 14), fontFamily: FONT_MONO, fontSize: 24, letterSpacing: 3, color: COLORS.accent2, marginBottom: 44 }}>THE&nbsp;PIPELINE</div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          {STEPS.map((st, i) => {
            const s = 14 + i * 11;
            const op = interpolate(frame, [s, s + 12], [0, 1], { ...CLAMP, easing: EASINGS.easeOut });
            const y = interpolate(frame, [s, s + 12], [24, 0], { ...CLAMP, easing: EASINGS.easeOut });
            return (
              <React.Fragment key={st.k}>
                <div style={{
                  opacity: op, transform: `translateY(${y}px)`, width: 224, height: 150,
                  background: COLORS.paper, border: `1px solid ${COLORS.line}`,
                  borderRadius: RADIUS.card, boxShadow: SHADOW.card,
                  display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', gap: 10,
                }}>
                  <div style={{ fontFamily: FONT_MONO, fontSize: 22, color: COLORS.accent }}>{st.k}</div>
                  <div style={{ fontFamily: FONT_DISPLAY, fontWeight: 700, fontSize: 36, color: COLORS.ink }}>{st.t}</div>
                </div>
                {i < STEPS.length - 1 && (
                  <div style={{ opacity: op, fontFamily: FONT_MONO, fontSize: 30, color: COLORS.muted }}>→</div>
                )}
              </React.Fragment>
            );
          })}
        </div>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};

// ---- Scene 5 — call to action ----------------------------------------------
const SceneEnd: React.FC = () => {
  const frame = useCurrentFrame();
  const rise = useRise();
  const barX = interpolate(frame, [10, 32], [0, 1], { ...CLAMP, easing: EASINGS.easeOut });
  return (
    <AbsoluteFill style={{ fontFamily: FONT_BODY }}>
      <BrandBg glow={COLORS.signal} />
      <AbsoluteFill style={{ alignItems: 'center', justifyContent: 'center' }}>
        <div style={{ ...rise(2, 20), fontFamily: FONT_DISPLAY, fontWeight: 700, fontSize: 88, letterSpacing: -1, color: COLORS.ink }}>
          See it in <span style={{ color: COLORS.accent }}>Remotion Studio</span>
        </div>
        <div style={{ width: 360, height: 8, borderRadius: 999, background: GRADIENT, marginTop: 26, transform: `scaleX(${barX})` }} />
        <div style={{ ...rise(20, 16), fontFamily: FONT_MONO, fontSize: 34, color: COLORS.muted, marginTop: 34 }}>
          cd remotion &amp;&amp; npm run studio
        </div>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};

// ---- Sequence them all -----------------------------------------------------
const RepoFaceless: React.FC = () => (
  <Series>
    <Series.Sequence durationInFrames={120}><SceneTitle /></Series.Sequence>
    <Series.Sequence durationInFrames={150}><SceneIdea /></Series.Sequence>
    <Series.Sequence durationInFrames={210}><SceneFeatures /></Series.Sequence>
    <Series.Sequence durationInFrames={180}><ScenePipeline /></Series.Sequence>
    <Series.Sequence durationInFrames={90}><SceneEnd /></Series.Sequence>
  </Series>
);
export default RepoFaceless;
