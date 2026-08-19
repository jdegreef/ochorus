/**
 * Right-to-left guards.
 *
 * Arabic is a routed locale, so every reader-facing surface renders under
 * `dir="rtl"`. Two things have to hold, and neither is visible in a code review
 * of an unrelated change — which is why they're pinned here.
 *
 * 1. The direction is baked into the PRERENDERED html. The root layout keeps
 *    `document.documentElement.dir` in sync on client navigation, but this is a
 *    static site: without the placeholder in app.html an Arabic page ships with
 *    no direction and paints left-to-right until hydration. A crawler sees only
 *    that.
 *
 * 2. Reader-facing markup uses LOGICAL spacing utilities (ms/me/ps/pe,
 *    text-start/end, border-s/e, start-/end-) rather than physical ones. In LTR
 *    they are identical, so a physical class is invisible until someone opens
 *    the site in Arabic and finds a badge on the wrong side of a heading. The
 *    admin is exempt: it is deliberately English-only and always renders LTR.
 *
 * 3. Scoped <style> blocks use LOGICAL CSS. The utility check above only sees
 *    class names, so for a long time every physical declaration written in real
 *    CSS shipped unchecked — which is how both slide-in drawers came to open
 *    from the wrong edge in Arabic, and how the current-chapter marker and both
 *    reading-page accent rails ended up on the wrong side.
 *
 * This is a source-text check, like readerDirection.test.ts beside it — the
 * mistake it catches is one of authoring, and it costs nothing to run.
 */
import { describe, expect, it } from 'vitest';
import { readFileSync, readdirSync, statSync } from 'node:fs';
import { join } from 'node:path';

const SRC = join(process.cwd(), 'src');

function svelteFiles(dir: string, out: string[] = []): string[] {
	for (const name of readdirSync(dir)) {
		const path = join(dir, name);
		if (statSync(path).isDirectory()) {
			if (name === 'paraglide' || name === 'node_modules') continue;
			svelteFiles(path, out);
		} else if (name.endsWith('.svelte')) {
			out.push(path);
		}
	}
	return out;
}

/** Admin is English-only and always LTR — see the note in admin/+page.svelte. */
const ADMIN_ONLY = [
	join('routes', 'admin'),
	join('components', 'AddLanguageForm.svelte'),
	join('components', 'LanguageSettingsCard.svelte')
];

const isAdmin = (path: string) => ADMIN_ONLY.some((frag) => path.includes(frag));

/**
 * The same mistake, one layer down: a scoped `<style>` block. The class scan
 * above never looked inside `<style>`, so physical CSS slipped past it — a
 * pull-quote rule drawn down the left of Arabic prose, an outline rail pinned
 * to the wrong margin, `text-align: left` on a sermon's outline.
 *
 * Positioning is deliberately included (`left:`/`right:` as properties), since
 * a fixed panel anchored `right: 0` sits at the READING end in English and the
 * wrong end in Arabic. Some properties genuinely have no logical form —
 * `box-shadow` offsets, `translateX`, `transform-origin: left` — and those are
 * flipped under an explicit `[dir='rtl']` rule instead; a file may opt a line
 * out with a trailing `/* rtl-ok: why *\/` comment when the physical value is
 * the correct one (a symmetric `left: 0; right: 0` pair, a mirror-image arrow).
 */
const PHYSICAL_CSS: [RegExp, string][] = [
	[/\bborder-(left|right)(-[a-z]+)?\s*:/g, 'border-inline-start/end'],
	[/\bpadding-(left|right)\s*:/g, 'padding-inline-start/end'],
	[/\bmargin-(left|right)\s*:/g, 'margin-inline-start/end'],
	[/\btext-align\s*:\s*(left|right)\b/g, 'text-align: start/end'],
	[/^\s*(left|right)\s*:/gm, 'inset-inline-start/end']
];

/** The `<style>` blocks of a component, concatenated. */
function styleBlocks(src: string): string {
	return (src.match(/<style[^>]*>[\s\S]*?<\/style>/g) ?? []).join('\n');
}

/** Lines a file has deliberately excused, by line content. */
const RTL_OK = /\/\*\s*rtl-ok:/;

/**
 * Physical inline-axis utilities and their logical replacements. Only the
 * inline axis: `mt-`/`mb-`/`top-`/`bottom-` are direction-independent, and
 * pixel-positioned popovers (measured from a selection rect) are physical by
 * nature and correctly so.
 */
const PHYSICAL: [RegExp, string][] = [
	[/\bml-[\w.[\]/-]+/g, 'ms-*'],
	[/\bmr-[\w.[\]/-]+/g, 'me-*'],
	[/\bpl-[\w.[\]/-]+/g, 'ps-*'],
	[/\bpr-[\w.[\]/-]+/g, 'pe-*'],
	[/\btext-left\b/g, 'text-start'],
	[/\btext-right\b/g, 'text-end'],
	[/\bborder-l(-[\w.[\]/-]+)?\b/g, 'border-s*'],
	[/\bborder-r(-[\w.[\]/-]+)?\b/g, 'border-e*']
];

/**
 * Physical CSS declarations and their logical replacements, for scoped <style>
 * blocks. Only the inline axis, and only where a single edge is addressed:
 * `left: 0; right: 0` pins BOTH edges and is direction-independent, as is
 * `left: 50%` paired with a centring translate.
 */
const PHYSICAL_CSS: [RegExp, string][] = [
	[/border-left(-color|-width|-style)?\s*:/g, 'border-inline-start*'],
	[/border-right(-color|-width|-style)?\s*:/g, 'border-inline-end*'],
	[/margin-left\s*:/g, 'margin-inline-start'],
	[/margin-right\s*:/g, 'margin-inline-end'],
	[/padding-left\s*:/g, 'padding-inline-start'],
	[/padding-right\s*:/g, 'padding-inline-end'],
	[/text-align\s*:\s*(left|right)\b/g, 'text-align: start|end']
];

/**
 * Deliberate physical CSS, with the reason. Each entry is a file fragment; the
 * scan skips it entirely, so keep them narrow.
 *
 * - LifeTimeline positions every mark with an inline `style="left: {pct}%"`
 *   computed from years, so its CSS and its markup have to agree on an axis.
 *   Mirroring it for RTL is a real change to the component, not a property
 *   swap, and doing half of it would be worse than neither.
 * - The chapter reader's .pageturn arrows are physical ON PURPOSE: the markup
 *   already swaps which chapter each PHYSICAL side turns to (`contentRtl`), and
 *   the arrow glyphs point the way they sit. Making the CSS logical too would
 *   mirror it twice and put both arrows back where they started.
 */
const PHYSICAL_CSS_EXEMPT = [
	join('components', 'LifeTimeline.svelte'),
	join('[order]', '+page.svelte')
];

describe('right-to-left support', () => {
	it('app.html carries the direction placeholder', () => {
		const html = readFileSync(join(SRC, 'app.html'), 'utf-8');
		expect(html).toMatch(/<html[^>]*\sdir="%paraglide\.dir%"/);
	});

	it('the server hook substitutes the direction from the locale', () => {
		const hook = readFileSync(join(SRC, 'hooks.server.ts'), 'utf-8');
		expect(hook).toContain('%paraglide.dir%');
		expect(hook).toContain('getTextDirection(locale)');
	});

	it('reader-facing scoped styles use logical, not physical, properties', () => {
		const offenders: string[] = [];
		for (const file of svelteFiles(SRC)) {
			if (isAdmin(file)) continue;
			const css = styleBlocks(readFileSync(file, 'utf-8'));
			for (const line of css.split('\n')) {
				if (RTL_OK.test(line)) continue;
				for (const [pattern, replacement] of PHYSICAL_CSS) {
					for (const hit of line.match(pattern) ?? []) {
						offenders.push(`${file.replace(SRC, 'src')}: ${hit.trim()} → use ${replacement}`);
					}
				}
			}
		}
		expect(offenders, offenders.join('\n')).toEqual([]);
	});

	it('reader-facing markup uses logical, not physical, inline spacing', () => {
		const offenders: string[] = [];
		for (const file of svelteFiles(SRC)) {
			if (isAdmin(file)) continue;
			const src = readFileSync(file, 'utf-8');
			for (const [pattern, replacement] of PHYSICAL) {
				for (const hit of src.match(pattern) ?? []) {
					offenders.push(`${file.replace(SRC, 'src')}: ${hit} → use ${replacement}`);
				}
			}
		}
		expect(offenders, offenders.join('\n')).toEqual([]);
	});

	it('scoped <style> blocks use logical, not physical, inline properties', () => {
		const offenders: string[] = [];
		for (const file of svelteFiles(SRC)) {
			if (isAdmin(file)) continue;
			if (PHYSICAL_CSS_EXEMPT.some((frag) => file.includes(frag))) continue;
			const style = /<style>([\s\S]*?)<\/style>/.exec(readFileSync(file, 'utf-8'))?.[1];
			if (!style) continue;
			for (const [pattern, replacement] of PHYSICAL_CSS) {
				for (const hit of style.match(pattern) ?? []) {
					offenders.push(`${file.replace(SRC, 'src')}: ${hit} → use ${replacement}`);
				}
			}
		}
		expect(offenders, offenders.join('\n')).toEqual([]);
	});
});
