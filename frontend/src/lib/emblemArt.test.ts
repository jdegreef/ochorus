import { readFileSync, readdirSync } from 'node:fs';
import { join } from 'node:path';
import { describe, expect, it } from 'vitest';

import { EMBLEM_ART } from './emblems';
import { TOPIC_META, topicEmblems } from './emblemNames';

/**
 * The topic emblems exist twice on purpose, and must never diverge.
 *
 * `covers.py` draws the generated book covers — 105 of the library's 153
 * editions wear one — and a plate with nothing on it but a title reads as
 * wallpaper on a shelf. It draws the emblem the book's topic already wears.
 * But the drawings are TypeScript and the API's Docker image has rootDir
 * `backend/`, so `covers.py` cannot read anything under `frontend/`.
 *
 * So `npm run emblem:art` exports them, and this fails if the committed copies
 * have drifted — the same arrangement as the brand lockup
 * (`brandAssets.test.ts`) and the precomputed hues (`emblemHues.test.ts`).
 * `emblems.ts` is the source; nothing hand-edits the backend copies.
 *
 * If this fails, run `cd frontend && npm run emblem:art` and commit the result.
 *
 * The mapping itself is `topicEmblems()` — the SAME function the exporter
 * calls, not a copy of its derivation. A gate that reimplements what it checks
 * agrees with the generator right up until the day one of them changes.
 */
const BACKEND_EMBLEMS = join(process.cwd(), '..', 'backend', 'library', 'data', 'emblems');

describe('the cover generator has the emblems it draws', () => {
	it('ships exactly the topic emblems — no more, no fewer', () => {
		const onDisk = readdirSync(BACKEND_EMBLEMS)
			.filter((f) => f.endsWith('.svg'))
			.map((f) => f.replace('.svg', ''))
			.sort();
		// Exactly: a stale extra is dead weight in the API image AND a file the
		// drift check below would keep passing because nothing names it.
		expect(onDisk).toEqual([...new Set(Object.values(topicEmblems()))].sort());
	});

	it.each(Object.entries(TOPIC_META))('%s: art matches emblems.ts', (_slug, meta) => {
		const committed = readFileSync(join(BACKEND_EMBLEMS, `${meta.emblem}.svg`), 'utf-8');
		// The export wraps the fragment in a viewBox'd document; compare the art.
		expect(committed).toContain(EMBLEM_ART[meta.emblem]);
		expect(committed).toContain('viewBox="0 0 48 48"');
	});

	it('records which emblem each topic wears', () => {
		const committed = JSON.parse(readFileSync(join(BACKEND_EMBLEMS, 'topics.json'), 'utf-8'));
		expect(committed.topics).toEqual(topicEmblems());
	});
});
