// Designed YouTube thumbnail (1280x720), rendered in Remotion — no image API.
// Theme-driven (colors + fonts from templates.ts) so thumbnails match the video.
// The generator emits a thin shot that renders <ThumbnailCard/> with baked props,
// then renders it as a still. Gemini supplies the short overlay text.
import React from 'react';
import { AbsoluteFill } from 'remotion';
import { Star } from 'lucide-react';
import { getTemplate } from '../templates';

export type ThumbProps = {
  overlay: string; name: string; owner?: string; stars?: number;
  templateId?: string; variant?: number;
};

const fmtStars = (n?: number): string =>
  n == null ? '' : n >= 1000 ? `${(n / 1000).toFixed(n >= 10000 ? 0 : 1)}k` : String(n);

export const ThumbnailCard: React.FC<ThumbProps> = ({ overlay, name, owner, stars, templateId, variant = 0 }) => {
  const t = getTemplate(templateId).theme;
  const hl = variant % 2 === 0 ? t.accent : t.signal; // highlight color varies per variant
  const text = (overlay || name).trim().toUpperCase();
  const words = text.split(/\s+/).filter(Boolean);
  const size = text.length > 20 ? 96 : text.length > 13 ? 124 : 150;
  const head = words.slice(0, -1).join(' ');
  const tail = words.slice(-1)[0] || '';

  // decorative graph nodes (top-right)
  const nodes = [
    { x: 940, y: 120, r: 16 }, { x: 1080, y: 90, r: 11 }, { x: 1150, y: 200, r: 20 },
    { x: 1010, y: 240, r: 13 }, { x: 1120, y: 320, r: 10 },
  ];

  return (
    <AbsoluteFill style={{ background: t.d900, fontFamily: t.fontDisplay, overflow: 'hidden' }}>
      <AbsoluteFill style={{ background: `radial-gradient(900px 620px at 80% 12%, ${hl}38, transparent 62%)` }} />
      <AbsoluteFill style={{ backgroundImage: `radial-gradient(${t.d600} 2px, transparent 2px)`, backgroundSize: '42px 42px', opacity: 0.22 }} />
      {/* graph motif */}
      <svg width={1280} height={720} style={{ position: 'absolute', inset: 0 }}>
        {nodes.map((n, i) => nodes.slice(i + 1).map((m, j) => (
          <line key={`${i}-${j}`} x1={n.x} y1={n.y} x2={m.x} y2={m.y} stroke={t.d600} strokeWidth={2} opacity={0.5} />
        )))}
        {nodes.map((n, i) => (
          <circle key={i} cx={n.x} cy={n.y} r={n.r} fill={i % 2 ? hl : t.d400} opacity={0.9} />
        ))}
      </svg>

      <AbsoluteFill style={{ padding: '64px 76px', justifyContent: 'space-between' }}>
        {/* top row: repo + stars */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
          <div style={{ width: 46, height: 46, borderRadius: 13, background: t.gradient }} />
          <div style={{ fontFamily: t.fontMono, fontSize: 32, color: t.d300 }}>
            {owner ? `${owner}/` : ''}<span style={{ color: '#fff' }}>{name}</span>
          </div>
          {stars != null && (
            <div style={{ marginLeft: 'auto', display: 'flex', alignItems: 'center', gap: 10, fontFamily: t.fontMono, fontSize: 32, color: '#fff', background: `${t.warn}22`, border: `1px solid ${t.warn}66`, borderRadius: 999, padding: '8px 22px' }}>
              <Star size={30} color={t.warn} fill={t.warn} /> {fmtStars(stars)}
            </div>
          )}
        </div>
        {/* headline */}
        <div style={{ fontWeight: 700, fontSize: size, lineHeight: 0.98, letterSpacing: -2, color: '#fff', maxWidth: '90%' }}>
          {head} <span style={{ color: hl }}>{tail}</span>
        </div>
        {/* accent bar */}
        <div style={{ width: 240, height: 12, borderRadius: 999, background: t.gradient }} />
      </AbsoluteFill>
    </AbsoluteFill>
  );
};
