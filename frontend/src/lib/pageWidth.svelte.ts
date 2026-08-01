import { browser } from '$app/environment';

/**
 * Shared page-column width for the main browse surfaces (Home, Books, Topics,
 * Plans, Sermons, Biographies, Search).
 *
 * Ported from Take Root's `contentWidth` store so the two siblings behave the
 * same way: one stored preference, stepped narrower/wider from the quick
 * settings popover, and every page follows it.
 *
 * This replaces the previous `--page-scale` approach, which multiplied each
 * page's own `max-w-*` by 0.85/1/1.18. That kept the pages at six *different*
 * base widths (Books 6xl, Topics 5xl, Biographies 4xl, Plans/Sermons 3xl…), so
 * "wide" meant something different on every page. An absolute width, shared by
 * all of them, is what makes the control feel global.
 *
 * Deliberately separate from `readerPrefs.measure`: that governs the prose
 * measure inside a chapter (a typographic concern, capped near 52rem for
 * readability), whereas this governs the page shell around it.
 */
export const WIDTH_STEPS = [48, 62, 76, 90, 104]; // rem
const DEFAULT_IDX = 2; // 76rem ≈ 1216px — close to today's Books/Topics feel
const LS_KEY = 'ochorus:page-width';

class PageWidth {
	idx = $state(DEFAULT_IDX);

	/** Adopt any stored preference. Called once from the root layout on mount. */
	init() {
		if (!browser) return;
		// Only adopt a *stored* value — `Number(null)` is 0, so reading the key
		// unconditionally would pin a first-time visitor to the narrowest step
		// instead of DEFAULT_IDX.
		const raw = localStorage.getItem(LS_KEY);
		if (raw === null) return;
		const i = Number(raw);
		if (Number.isInteger(i) && i >= 0 && i < WIDTH_STEPS.length) this.idx = i;
	}

	/** Current width in rem — feed into `style="--pw:{…}rem"`. */
	get rem() {
		return WIDTH_STEPS[this.idx];
	}
	get atMin() {
		return this.idx === 0;
	}
	get atMax() {
		return this.idx === WIDTH_STEPS.length - 1;
	}

	/** Step the width by ±1 and persist. */
	step(delta: number) {
		this.idx = Math.min(WIDTH_STEPS.length - 1, Math.max(0, this.idx + delta));
		if (browser) localStorage.setItem(LS_KEY, String(this.idx));
	}
}

export const pageWidth = new PageWidth();
