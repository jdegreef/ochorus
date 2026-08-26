import { readFileSync } from 'node:fs';
import { join } from 'node:path';

/**
 * Reading `cover-type.css` the way its gates need to read it.
 *
 * Four test files scan this stylesheet — for the faces a recipe names, the band
 * geometry it shares with `covers.py`, the scrim's stops, and the arrangement
 * each era composes in — and each had grown its own copy of the same two moves:
 * slurp the file, then pull the body of every block matching a selector. The
 * copies had already drifted (one stripped comments before scanning, three did
 * not) and the cascade rule they all depend on was restated in each.
 *
 * NOT IN `src/lib`. `nodeLoadable.test.ts` polices that directory for
 * bare-Node loadability because the build scripts import from it; a test-only
 * scanner has no business being subject to that. `vitest.config.ts` collects
 * `src/**\/*.test.ts` alone, so nothing here is collected as a suite.
 */
export const COVER_CSS = readFileSync(
	join(process.cwd(), 'src/lib/components/cover-type.css'),
	'utf-8'
);

/**
 * The same stylesheet with its comments removed.
 *
 * This file is more than half prose by volume, and prose here quotes selectors
 * and declarations constantly — `--font-display:` appears in a paragraph, and
 * `.cover-type.style-press .title` in another. A scan of the raw text reads
 * those as code: it has reported a paragraph as a declaration's value, and a
 * comment as a rule a style writes.
 */
export const COVER_CSS_CODE = COVER_CSS.replace(/\/\*[\s\S]*?\*\//g, '');

/**
 * The body of every block matching `selector`, in source order.
 *
 * EVERY block, not the first. A style writes the same selector more than once —
 * once inside the container gate for the face and weight it asks of it, once
 * outside for the leading its composition wants — and a scan that stopped at
 * the first match read whichever happened to come first. That is not a
 * hypothetical: it is how the weight gate came to report that `.style-press`
 * asked for no weight at all, and how the tracking gate passed on a block that
 * does not decide anything.
 *
 * SCANS THE COMMENT-STRIPPED TEXT BY DEFAULT, and that is not tidiness either.
 * `[^{]*\{` run over the raw file walks forward from any PROSE that quotes a
 * selector to the next real brace, and returns that unrelated block's body as
 * though it belonged to the selector named in the comment. `.style-press
 * .title` is quoted in a paragraph about cascade order, so scanning raw text
 * returned `.script-arabic .title`'s body as a third `press` block — and since
 * that phantom sets `font-weight: 400`, the weight gate read 400 no matter what
 * the real recipe asked for. Verified: with the raw default, setting the press
 * recipe to a 700 IM Fell has not got left every gate green.
 */
export function blocksFor(selector: string, css = COVER_CSS_CODE): RegExpMatchArray[] {
	return [
		...css.matchAll(new RegExp(`${selector.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}[^{]*\\{([^}]*)\\}`, 'g'))
	];
}

/**
 * The declaration that WINS for `selector` — the last one in source order.
 *
 * Every selector these gates care about is the same specificity as the ones it
 * competes with (three classes, by construction), so nothing but source order
 * decides. Returning the last match is that rule, written once, instead of in
 * each gate that depends on it.
 */
export function lastDecl(selector: string, decl: RegExp, css = COVER_CSS_CODE): string | null {
	const found = blocksFor(selector, css)
		.flatMap((m) => [...m[1].matchAll(new RegExp(decl, 'g'))])
		.map((m) => m[1]);
	return found.length ? found[found.length - 1] : null;
}
