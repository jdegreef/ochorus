import { describe, it, expect } from 'vitest';
import { readFileSync, readdirSync, statSync } from 'node:fs';
import { join, relative } from 'node:path';

/**
 * No bare "→" / "←" in reader-facing markup.
 *
 * Arrows are not bidi-mirrored characters (unlike ‹ ›), so a literal "→" on a
 * "Read more →" link points backwards in Arabic, where onward is leftward —
 * about fifty of them did, across shelf headers, cards and the notebook.
 * `<Arrow />` / `<Arrow back />` mirror under dir=rtl.
 *
 * Markup only: comments, <script> and <style> are stripped first, so prose
 * like "border → accent" or a keyboard hint in a comment is fine. The admin
 * console is English-only and excluded.
 */

const SRC = join(import.meta.dirname, '..');

function svelteFiles(dir: string): string[] {
	return readdirSync(dir).flatMap((name) => {
		const path = join(dir, name);
		if (statSync(path).isDirectory()) return svelteFiles(path);
		return name.endsWith('.svelte') ? [path] : [];
	});
}

function markupOf(source: string): string {
	return source
		.replace(/<script[\s\S]*?<\/script>/g, '')
		.replace(/<style[\s\S]*?<\/style>/g, '')
		.replace(/<!--[\s\S]*?-->/g, '');
}

describe('text arrows mirror in right-to-left locales', () => {
	it('uses <Arrow> rather than a literal arrow in reader-facing markup', () => {
		const offenders: string[] = [];
		for (const file of svelteFiles(SRC)) {
			const rel = relative(SRC, file);
			if (rel.startsWith('routes/admin') || rel.endsWith('Arrow.svelte')) continue;
			const markup = markupOf(readFileSync(file, 'utf8'));
			markup.split('\n').forEach((line) => {
				if (/[←→]/.test(line)) offenders.push(`${rel}: ${line.trim().slice(0, 80)}`);
			});
		}
		expect(offenders, 'Use <Arrow /> (onward) or <Arrow back /> instead:\n').toEqual([]);
	});
});
