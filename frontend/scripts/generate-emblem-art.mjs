/**
 * Export the topic emblems the COVER GENERATOR needs, into the backend.
 *
 *     cd frontend && npm run emblem:art
 *
 * WHY THIS CROSSES THE TREE
 * `covers.py` draws the generated book covers — 105 of the library's 153
 * editions wear one — and a plate with nothing on it but a title reads as
 * wallpaper on a shelf: twelve coloured slabs in a grid. The fix is the emblem
 * the book's topic already has. But the emblems are TypeScript (`emblems.ts`,
 * 51 drawings with a shared palette), the API's Docker image has rootDir
 * `backend/`, and `covers.py` cannot read anything under `frontend/`.
 *
 * So the art is exported here, at author time, the same way `emblemHues.ts` is
 * derived here rather than at runtime — and for the same reason the brand
 * lockup is committed on both sides (`brandAssets.test.ts`). `emblems.ts` stays
 * the single source: this writes, nobody hand-edits, and `emblemArt.test.ts`
 * re-derives every file and fails if the committed copies have drifted.
 *
 * ONLY THE TOPIC EMBLEMS. A book wears its topic's emblem, so the sermon and
 * plan drawings have no business in the API image — 17 files, not 51.
 */
import { mkdirSync, readdirSync, rmSync, writeFileSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

import { EMBLEM_ART } from '../src/lib/emblems.ts';
import { topicEmblems } from '../src/lib/emblemNames.ts';

const OUT = resolve(dirname(fileURLToPath(import.meta.url)), '../../backend/library/data/emblems');

// The map itself is `topicEmblems()` in `emblemNames.ts`, NOT derived here:
// `emblemArt.test.ts` checks the committed files against that same function, and
// a gate that re-derives what it checks is a second opinion, not a drift test.
mkdirSync(OUT, { recursive: true });
const topics = topicEmblems();
const wanted = new Set(Object.values(topics));

// Prune first: an emblem that stops being a topic's is dead weight in the image,
// and a stale file would keep passing the drift check nobody thought to widen.
for (const name of readdirSync(OUT)) {
	if (name.endsWith('.svg') && !wanted.has(name.replace('.svg', ''))) {
		rmSync(resolve(OUT, name));
	}
}

for (const name of [...wanted].sort()) {
	// A standalone document, not a fragment: `covers.py` re-scales it by its
	// viewBox, exactly as it does the lockup, so the art carries its own frame.
	writeFileSync(
		resolve(OUT, `${name}.svg`),
		`<!--GENERATED from frontend/src/lib/emblems.ts by npm run emblem:art; do not hand-edit.-->` +
			`<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 48 48">${EMBLEM_ART[name]}</svg>\n`
	);
}

writeFileSync(
	resolve(OUT, 'topics.json'),
	JSON.stringify(
		{
			_comment:
				'GENERATED from frontend/src/lib/emblemNames.ts by npm run emblem:art. ' +
				'Topic slug -> emblem name, so covers.py can draw the emblem a book’s topic wears.',
			topics
		},
		null,
		'\t'
	) + '\n'
);

console.log(
	`wrote ${wanted.size} emblems and ${Object.keys(topics).length} topic assignments to ${OUT}`
);
