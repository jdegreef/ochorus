/**
 * The page grain (app.css --grain / --grain-light-specks), pre-rendered.
 *
 *   node scripts/generate-grain.mjs
 *
 * The grain used to be an inline SVG data: URI running an feTurbulence filter.
 * A browser re-runs that filter whenever it rasterises the tile — at every
 * device-pixel ratio, zoom and repaint of a layer the body ground sits under —
 * which is paint time on a phone. These are the SAME three SVGs, rendered once
 * to tiles at 1x, 2x and 3x (app.css serves them through image-set(), so every
 * screen gets the tile drawn at its own resolution, as the SVG was). Change a
 * grain here, re-run, commit the PNGs.
 *
 * Each grain: fractal noise, coloured one ink, its alpha thresholded by a
 * discrete table so only the top of the noise survives as sparse specks.
 */
import { Resvg } from '@resvg/resvg-js';
import { mkdirSync, writeFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const OUT = join(dirname(fileURLToPath(import.meta.url)), '..', 'static', 'textures');
const TILE = 180;
const SCALES = [1, 2, 3];

/** name → [r, g, b] ink (0–1) and the speck alpha. */
const GRAINS = {
	// Lamplight (and every .night-band, the home hero): light specks.
	light: { ink: [0.96, 0.9, 0.8], alpha: 0.1 },
	// Paper: warm brown.
	paper: { ink: [0.42, 0.32, 0.18], alpha: 0.16 },
	// Sepia: a deeper brown, a little stronger.
	sepia: { ink: [0.4, 0.3, 0.14], alpha: 0.18 }
};

export function grainSvg({ ink: [r, g, b], alpha }) {
	return (
		`<svg xmlns='http://www.w3.org/2000/svg' width='${TILE}' height='${TILE}'>` +
		`<filter id='n'><feTurbulence type='fractalNoise' baseFrequency='.8' numOctaves='3' stitchTiles='stitch'/>` +
		`<feColorMatrix values='0 0 0 0 ${r} 0 0 0 0 ${g} 0 0 0 0 ${b} 1 0 0 0 0'/>` +
		`<feComponentTransfer><feFuncA type='discrete' tableValues='0 0 0 0 0 ${alpha} ${alpha}'/></feComponentTransfer>` +
		`</filter><rect width='100%' height='100%' filter='url(#n)'/></svg>`
	);
}

mkdirSync(OUT, { recursive: true });
for (const [name, grain] of Object.entries(GRAINS)) {
	for (const scale of SCALES) {
		const png = new Resvg(grainSvg(grain), { fitTo: { mode: 'zoom', value: scale } }).render().asPng();
		const file = `grain-${name}${scale === 1 ? '' : `@${scale}x`}.png`;
		writeFileSync(join(OUT, file), png);
		console.log(`${file}  ${png.length} bytes`);
	}
}
