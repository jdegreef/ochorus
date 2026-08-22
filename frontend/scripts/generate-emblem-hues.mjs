/**
 * Regenerate `src/lib/emblemHues.ts` — the emblem accents, precomputed.
 *
 *     cd frontend && npm run emblem:hues
 *
 * WHY THE MAP EXISTS
 * `emblemHue()` derives an accent by scanning an emblem's SVG source, so
 * calling it drags `EMBLEM_ART` — 51 drawings, 38 KB raw / 10.6 KB gzip — into
 * whatever bundle wants a colour. Rollup cannot tree-shake object properties,
 * so a page that needs ONE hue and no art still ships all fifty-one drawings.
 * Measured: importing it from the sermon plate put that chunk on the critical
 * path of both the home page and every sermon page, +10.6 KB gzip each, for
 * one colour and one drawing.
 *
 * So the derivation runs here, at author time, and the app imports 51 short
 * strings instead. `emblemHues.test.ts` re-derives every entry and fails if the
 * committed map has drifted, which is what makes it safe to trust.
 */
import { writeFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, resolve } from 'node:path';

import { EMBLEM_ART, emblemHue } from '../src/lib/emblems.ts';

const OUT = resolve(dirname(fileURLToPath(import.meta.url)), '../src/lib/emblemHues.ts');
const names = Object.keys(EMBLEM_ART).sort();

writeFileSync(
	OUT,
	`/**
 * The dominant ink of every emblem, precomputed.
 *
 * GENERATED — do not edit by hand. Run \`npm run emblem:hues\` after changing
 * emblem art; \`emblemHues.test.ts\` fails if this file and \`emblemHue()\`
 * disagree.
 *
 * This exists so a surface can wear an emblem's colour without importing the
 * emblem's DRAWING. \`emblemHue()\` reads the art to derive the hue, and the art
 * is 51 SVG strings that Rollup cannot tree-shake apart — the sermon plate
 * importing it cost the home page and every sermon page 10.6 KB gzip on the
 * critical path, for one colour.
 *
 * hex-ok-file: these are the colours OF the drawings, the way a book cover has
 * colours — data, not chrome that should restyle with the theme.
 */
import type { EmblemName } from './emblems';

export const EMBLEM_HUES: Record<EmblemName, string> = {
${names.map((n) => `\t'${n}': '${emblemHue(n)}'`).join(',\n')}
};
`,
	'utf8'
);
console.log(`Wrote ${names.length} emblem hues to ${OUT}`);
