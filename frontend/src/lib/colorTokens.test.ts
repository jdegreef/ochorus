/**
 * Colour-token guard — STYLE_GUIDE §8, rule 1.
 *
 * "Use tokens for every color — no raw hex" is the oldest rule in the guide and
 * the only one of the four §8 colour/type/layout rules that had no CI check.
 * The cost of a raw hex is not that it looks wrong once: it is that it does not
 * move when the theme moves, so it silently becomes the one element that stays
 * cream on the lamplight page — which is exactly how `#3b5bdb` ended up
 * hardcoded in five files, four different ways (fixed in #720 by `coverArt.ts`).
 *
 * Three exemptions, all narrow and all stated by the guide itself:
 *
 *   1. `app.css` — where the tokens are DEFINED. Hex is the point there.
 *   2. `/admin/` — an internal, English-only, single-theme surface.
 *   3. A stated opt-out, at one of two granularities:
 *        - `hex-ok:` on the same line or the line above it, for a one-off;
 *        - `hex-ok-file:` anywhere in a file that is ENTIRELY about painting
 *          something other than a theme surface — generated cover artwork, a
 *          vendor's brand mark. Both are cases the guide itself carves out.
 *      Either way the comment has to say why, because "there is a reason" and
 *      "someone wrote a reason down" are different things.
 *
 * Same shape as rtl.test.ts and typeScaleGuard.test.ts beside it: a source-text
 * check for a mistake of authoring, costing nothing to run.
 */
import { describe, expect, it } from 'vitest';
import { readFileSync, readdirSync, statSync } from 'node:fs';
import { join } from 'node:path';

const SRC = join(process.cwd(), 'src');

function sourceFiles(dir: string, out: string[] = []): string[] {
	for (const name of readdirSync(dir)) {
		const path = join(dir, name);
		if (statSync(path).isDirectory()) {
			if (name === 'paraglide' || name === 'node_modules' || name === 'brand') continue;
			sourceFiles(path, out);
		} else if (
			name.endsWith('.svelte') ||
			name.endsWith('.css') ||
			(name.endsWith('.ts') && !name.endsWith('.test.ts'))
		) {
			out.push(path);
		}
	}
	return out;
}

/**
 * The part of a line that is code, not prose.
 *
 * Comments are stripped before scanning because `#` is not only a colour: this
 * repo's route files are full of "(queue jobs #685-#689, PR #964)" notes, and
 * `#685` is three valid hex digits' worth of coincidence. A guard that cried
 * wolf on a PR number would be switched off within the week — a worse outcome
 * than not having one.
 */
function codeOnly(line: string): string {
	const trimmed = line.trim();
	if (
		trimmed.startsWith('*') ||
		trimmed.startsWith('//') ||
		trimmed.startsWith('/*') ||
		trimmed.startsWith('<!--')
	) {
		return '';
	}
	const slashes = line.indexOf('//');
	return slashes === -1 ? line : line.slice(0, slashes);
}

/**
 * Is the offending line covered by an opt-out in the comment block directly
 * above it?
 *
 * Walks up through contiguous comment lines rather than checking only `i - 1`:
 * a reason worth writing is usually longer than one line, and a guard that
 * silently stops honouring an opt-out when its comment wraps would teach people
 * to write terser reasons instead of better ones.
 */
function exemptedByCommentAbove(lines: string[], i: number): boolean {
	for (let j = i - 1; j >= 0; j--) {
		const line = lines[j].trim();
		const isComment =
			line.startsWith('*') ||
			line.startsWith('/*') ||
			line.startsWith('//') ||
			line.startsWith('<!--') ||
			line.endsWith('*/') ||
			line.endsWith('-->');
		if (!isComment) return false;
		if (OPT_OUT.test(line)) return true;
	}
	return false;
}

/**
 * #rgb, #rgba, #rrggbb, #rrggbbaa — but not a `#anchor` or an id selector.
 *
 * The 4-digit form matters: `#0008` is how a translucent black gets written,
 * and it is exactly the shorthand `coverArt.ts` names as the old cover gradient.
 */
const HEX = /#[0-9a-fA-F]{3,4}\b|#[0-9a-fA-F]{6}(?:[0-9a-fA-F]{2})?\b/g;
const OPT_OUT = /hex-ok:/;
const OPT_OUT_FILE = /hex-ok-file:/;

describe('colour tokens', () => {
	it('no raw hex outside app.css, admin, and the stated exemptions', () => {
		const offenders: string[] = [];
		for (const file of sourceFiles(SRC)) {
			const rel = file.replace(SRC, 'src');
			if (rel.endsWith('app.css') || rel.includes('/admin/')) continue;
			const source = readFileSync(file, 'utf-8');
			if (OPT_OUT_FILE.test(source)) continue;
			const lines = source.split('\n');
			lines.forEach((line, i) => {
				const code = codeOnly(line);
				if (!HEX.test(code)) return;
				HEX.lastIndex = 0;
				if (OPT_OUT.test(line) || exemptedByCommentAbove(lines, i)) return;
				offenders.push(
					`${rel}:${i + 1}: ${line.trim().slice(0, 90)} → use a token, or /* hex-ok: why */`
				);
			});
		}
		expect(offenders, offenders.join('\n')).toEqual([]);
	});

	it('app.css still defines the tokens the rule points at', () => {
		const css = readFileSync(join(SRC, 'app.css'), 'utf-8');
		for (const token of ['--bg', '--surface', '--text', '--muted', '--accent', '--border']) {
			expect(css, `${token} is missing from app.css`).toContain(`${token}:`);
		}
	});
});
