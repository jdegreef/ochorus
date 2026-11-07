/**
 * The halo's rules as `cover-type.css` writes them — every rule whose selector
 * names the halo's scope — whitespace-collapsed, so a re-indent is not a change
 * and a new shadow is.
 *
 * `scripts/measure-cover-halo.mjs` digests this (sha256, first 16 hex) when it measures the halo's
 * floor into `backend/library/cover_halo.py`; `coverHalo.test.ts` digests it
 * again and fails if the stylesheet has moved on from what was measured. Pure, so
 * a bare-Node script can load it (`nodeLoadable.test.ts`).
 */
export const HALO_SCOPE = '.cover-plate.over-art:not(.has-layout, .ink-dark) .cover-type';

export function haloRules(css: string): string {
	const rules = [...css.replace(/\/\*[\s\S]*?\*\//g, '').matchAll(/([^{}]+)\{([^{}]*)\}/g)]
		.filter(([, selector, body]) => selector.includes(HALO_SCOPE) && /text-shadow|drop-shadow|box-shadow/.test(body))
		.map(([, selector, body]) => `${selector.trim()}{${body.trim()}}`.replace(/\s+/g, ' '));
	return rules.join('\n');
}
