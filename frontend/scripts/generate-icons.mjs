/**
 * Generate the app icons and the favicon from the real Ochorus logo.
 *
 * Output: frontend/static/icons/*.png — committed to the repo and served as
 * static assets. This script is NOT part of the build or CI; run it by hand
 * when the logo changes:
 *
 *     cd frontend
 *     npm i -D @resvg/resvg-js        # build-only, not an app dep
 *     node scripts/generate-icons.mjs
 *
 * WHY THIS EXISTS
 * The icons were a placeholder blue "O" until the real logo landed (#873), and
 * the replacements were rasterized by hand. Every decision below — the plate
 * colour, how much of the square the glyph fills, the maskable inset, and which
 * glyph the favicon uses — then lived only in a pull-request description. This
 * file is that knowledge, in a form that can be re-run.
 *
 * IT READS THE BACKEND COPY ON PURPOSE
 * `backend/library/data/brand/` is the canonical artwork (the api's Docker image
 * has rootDir `backend/`, so covers.py cannot reach into frontend/). The
 * frontend mirrors two of those files for Vite's `?raw` imports, but a
 * dev-time script has the whole monorepo and should read the original rather
 * than add a third copy — `ochorus-o.svg` is not mirrored at all.
 */
import { Resvg } from '@resvg/resvg-js';
import { readFileSync, writeFileSync, mkdirSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, resolve, join } from 'node:path';

const HERE = dirname(fileURLToPath(import.meta.url));
const BRAND = resolve(HERE, '../../backend/library/data/brand');
const OUT_DIR = resolve(HERE, '../static/icons');

/** The plate the glyph sits on. Unchanged from the placeholder it replaced, so
 *  this was a glyph swap rather than a rebrand. */
const PLATE = '#3b5bdb';

const ICONS = [
	// The book-and-quill mark, at sizes where its hairlines survive.
	{ out: 'icon-192.png', size: 192, glyph: 'ochorus-mark.svg', fill: 0.62 },
	{ out: 'icon-512.png', size: 512, glyph: 'ochorus-mark.svg', fill: 0.62 },
	// Maskable: Android crops to a circle ~80% of the square and may round the
	// corners hard, so the glyph is pulled well inside the safe zone.
	{ out: 'icon-maskable-512.png', size: 512, glyph: 'ochorus-mark.svg', fill: 0.46 },
	// The tab icon is the wordmark's capital O, NOT the mark. At 16px the mark's
	// hairlines collapse into an unreadable smudge (checked against the real
	// thing); the O is from the same logo and stays crisp.
	{ out: 'favicon-32.png', size: 32, glyph: 'ochorus-o.svg', fill: 0.66 }
];

/** The glyph's paths, and its viewBox size. */
function readGlyph(name) {
	const src = readFileSync(join(BRAND, name), 'utf-8');
	const box = /viewBox="0 0 ([\d.]+) ([\d.]+)"/.exec(src);
	if (!box) throw new Error(`${name}: expected a viewBox normalised to "0 0 w h"`);
	const inner = /<svg[^>]*>([\s\S]*)<\/svg>/.exec(src);
	if (!inner) throw new Error(`${name}: no <svg> body`);
	// The artwork carries `fill="currentColor"` on its ROOT <svg>, which this
	// throws away — so the extracted paths inherit nothing and rasterize BLACK
	// on the blue plate. The caller paints the wrapping <g> white instead.
	// (`currentColor` is replaced too, for any file that sets it further down.)
	return { body: inner[1].replaceAll('currentColor', '#ffffff'), w: +box[1], h: +box[2] };
}

function render({ out, size, glyph, fill }) {
	const { body, w, h } = readGlyph(glyph);
	// Fit the glyph's longest side to `fill` of the square, then centre it.
	const k = (size * fill) / Math.max(w, h);
	const x = (size - w * k) / 2;
	const y = (size - h * k) / 2;
	const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="${size}" height="${size}" viewBox="0 0 ${size} ${size}">
  <rect width="${size}" height="${size}" fill="${PLATE}"/>
  <g fill="#ffffff" transform="translate(${x.toFixed(2)} ${y.toFixed(2)}) scale(${k.toFixed(5)})">${body}</g>
</svg>`;
	const png = new Resvg(svg, { fitTo: { mode: 'width', value: size } }).render().asPng();
	writeFileSync(join(OUT_DIR, out), png);
	return png.length;
}

mkdirSync(OUT_DIR, { recursive: true });
for (const icon of ICONS) {
	const bytes = render(icon);
	console.log(`  ✓ ${icon.out.padEnd(24)} ${String(icon.size).padStart(3)}px  ${bytes} bytes`);
}
console.log(`Wrote ${ICONS.length} icons to ${OUT_DIR}`);
