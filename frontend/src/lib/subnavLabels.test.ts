// @vitest-environment node
import { describe, expect, it } from 'vitest';
import { readFileSync, readdirSync, statSync } from 'node:fs';
import { join, relative } from 'node:path';

/**
 * Reader-facing pages build their tab strips and jump navs from `{ id, label }`
 * lists. A label typed as a string literal skips the catalogues, so it stays
 * English in every locale — the author page's "Questions" tab did exactly that
 * in Arabic (QA report, 2026-10). Labels go through `t()`. Admin is exempt
 * (English-only by design).
 */
const ROUTES = join(import.meta.dirname, '..', 'routes');

function pages(dir: string, out: string[] = []): string[] {
	for (const name of readdirSync(dir)) {
		const path = join(dir, name);
		if (statSync(path).isDirectory()) {
			if (name !== 'admin') pages(path, out);
		} else if (name === '+page.svelte') out.push(path);
	}
	return out;
}

describe('reader-facing nav labels are localized', () => {
	it.each(pages(ROUTES).map((f) => [relative(ROUTES, f), f]))('%s has no literal `label:`', (_, file) => {
		expect(readFileSync(file, 'utf8').match(/\blabel:\s*['"`][^'"`]+['"`]/g) ?? []).toEqual([]);
	});
});
