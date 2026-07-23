// Render one or more compositions as PNG stills into a target directory.
// Bundles once for all ids (fast). Used by tools/gen_package.py for thumbnails.
//   node scripts/render-still.mjs <outDir> <CompId> [CompId ...]
import { bundle } from '@remotion/bundler';
import { selectComposition, renderStill } from '@remotion/renderer';
import { fileURLToPath } from 'url';
import path from 'path';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const [, , outDir, ...ids] = process.argv;
if (!outDir || ids.length === 0) {
  console.error('usage: render-still.mjs <outDir> <CompId> [CompId ...]');
  process.exit(1);
}

const serveUrl = await bundle({
  entryPoint: path.join(root, 'src', 'index.ts'),
  publicDir: path.join(root, '..', 'media'),
});

for (const id of ids) {
  const composition = await selectComposition({ serveUrl, id });
  const out = path.join(outDir, `${id}.png`);
  await renderStill({ serveUrl, composition, output: out, frame: 0, scale: 1, imageFormat: 'png', overwrite: true });
  console.log('still ->', out);
}
