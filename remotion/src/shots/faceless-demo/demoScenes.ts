// Shared demo storyboard (about this repo) used by the landscape + vertical shots
// to prove the data-driven engine. narration fields double as caption text.
import type { Scene } from '../../lib/storyboard';

export const DEMO_SCENES: Scene[] = [
  { type: 'title', dur: 120, eyebrow: 'open-source · youtube pipeline', title: 'claude-youtube-editor', subtitle: 'You record. Claude Code does the rest.',
    narration: 'claude-youtube-editor turns your footage into a finished video.' },
  { type: 'statement', dur: 150, eyebrow: 'the idea', text: 'Every on-screen moment is built as code and composited over your cut.',
    narration: 'Every on-screen moment is built as code — no screen recorder, no timeline to drag.' },
  { type: 'features', dur: 210, eyebrow: 'what it does',
    items: [
      { label: 'Visuals as code', value: 'Remotion · no editor' },
      { label: 'Clean voice + SFX', value: 'isolate · sound-design' },
      { label: 'Package + upload', value: 'titles · thumbs · draft' },
    ],
    narration: 'It builds the visuals, cleans your voice, and packages the video for YouTube.' },
  { type: 'steps', dur: 180, eyebrow: 'the pipeline',
    steps: ['cut', 'visuals', 'voice', 'sfx', 'package', 'ship'],
    narration: 'The pipeline runs in six steps: cut, visuals, voice, sound effects, package, ship.' },
  { type: 'bullets', dur: 150, eyebrow: 'new in module 1', title: 'Faceless from a source',
    points: ['A public GitHub repo', 'An article or webpage URL', 'Or just pasted text'],
    narration: 'And now it can build a faceless video from a repo, an article, or pasted text.' },
  { type: 'cta', dur: 90, title: 'See it in Remotion Studio', sub: 'cd remotion && npm run studio',
    narration: 'See it for yourself in Remotion Studio.' },
];
