import { beforeEach, describe, expect, it, vi } from 'vitest';
import { readFileSync, readdirSync } from 'node:fs';
import { join, relative } from 'node:path';

/**
 * A reader-initiated language switch must survive the next profile pull.
 *
 * `auth.#pullProfile()` runs on every load with a session and reconciles the
 * locale against the account: when `ochorus:lang` is absent it ADOPTS the saved
 * profile locale (cross-device restore), and `Profile.locale` defaults to "en".
 * So a switcher that navigates without recording the choice sends a signed-in
 * reader to /es, then the profile pull bounces them straight back to English —
 * which is exactly what the footer language strip did (it called `lang.set()`
 * instead of `lang.choose()`).
 *
 * `set()` alone is legitimate in one place only: the profile-adoption branch
 * itself, which is not a reader choice and must not be recorded as one.
 */

const { setLocale } = vi.hoisted(() => ({ setLocale: vi.fn() }));

// The real setLocale navigates (Paraglide's `url` strategy), which jsdom cannot
// do — and the property under test is what gets RECORDED, not the navigation.
vi.mock('$lib/paraglide/runtime', () => ({
	getLocale: () => 'en',
	setLocale,
	locales: ['en', 'es', 'sw', 'lg', 'pt', 'ar']
}));

const { lang } = await import('./lang.svelte');

const CHOSEN_KEY = 'ochorus:lang';

describe('recording a reader-initiated switch', () => {
	beforeEach(() => {
		localStorage.clear();
		setLocale.mockClear();
	});

	it('choose() records the device choice, so a profile pull cannot bounce it back', () => {
		lang.choose('es');

		expect(localStorage.getItem(CHOSEN_KEY)).toBe('es');
		expect(setLocale).toHaveBeenCalledWith('es');
	});

	it('set() switches without recording — profile adoption, not a reader choice', () => {
		lang.set('es');

		expect(localStorage.getItem(CHOSEN_KEY)).toBeNull();
		expect(setLocale).toHaveBeenCalledWith('es');
	});
});

/*
 * The behavioural tests above pin what the two methods do; they cannot catch a
 * switcher calling the wrong one. These do, at the source level — the same
 * approach messageCatalogues.test.ts takes to a property no unit test sees.
 */

const SRC = join(process.cwd(), 'src');

/** Every `.svelte` / `.ts` file under src/, minus generated + test files. */
const sourceFiles = (dir = SRC, out: string[] = []): string[] => {
	for (const entry of readdirSync(dir, { withFileTypes: true })) {
		const full = join(dir, entry.name);
		if (entry.isDirectory()) {
			if (entry.name !== 'paraglide') sourceFiles(full, out);
		} else if (/\.(svelte|ts)$/.test(entry.name) && !entry.name.endsWith('.test.ts')) {
			out.push(full);
		}
	}
	return out;
};

/** Where a bare `lang.set()` is the correct call: adopting the saved profile. */
const SET_ALLOWED = new Set(['lib/auth.svelte.ts']);

/**
 * Every surface a reader can switch language from.
 *
 * Two, deliberately. A third — a header dropdown — was removed because it had
 * to list every UI locale to justify its slot, which made the chrome contradict
 * itself: hi showed in the header while the footer strip, sitemap and hreflang
 * all omit it. The footer strip advertises; Settings is the full list.
 */
const SWITCHERS = [
	'src/routes/+layout.svelte', // footer language strip
	'src/routes/settings/+page.svelte' // Settings -> Language
];

describe('every reader-facing switcher goes through choose()', () => {
	it.each(SWITCHERS)('%s calls lang.choose()', (file) => {
		const src = readFileSync(join(process.cwd(), file), 'utf-8');

		expect(src, `${file} should switch locale via lang.choose()`).toMatch(/lang\.choose\(/);
		expect(
			src,
			`${file} calls lang.set() — that skips the ${CHOSEN_KEY} guard, so a signed-in ` +
				'reader gets bounced back to their profile locale on the next load'
		).not.toMatch(/lang\.set\(/);
	});

	// The check above reads a file's CONTENTS. That is not the same as the
	// component being on screen: LanguagePicker.svelte sat in this list, passed
	// every assertion, and was imported by nothing at all — so the header had no
	// language control at all for a while.
	//
	// Both switchers are routes today, and a route is mounted by definition, so
	// this loop has no subjects. A plain `for` rather than `it.each`, which
	// throws on an empty list — and it stays because the bug it caught costs
	// nothing to guard against and reappears the moment a component is added
	// back to SWITCHERS.
	for (const file of SWITCHERS.filter((f) => f.includes('/components/'))) {
		it(`${file} is actually mounted somewhere`, () => {
			const name = file.split('/').pop()!.replace('.svelte', '');
			const importers = sourceFiles()
				.filter((f) => !f.endsWith(`${name}.svelte`))
				.filter((f) => new RegExp(`import\\s+${name}\\s+from`).test(readFileSync(f, 'utf-8')));

			expect(
				importers,
				`${file} is a reader-facing switcher that nothing imports — it cannot be ` +
					'used. Mount it, or drop it from SWITCHERS.'
			).not.toEqual([]);
		});
	}

	it('no other module calls lang.set() except the profile-adoption branch', () => {
		const offenders = sourceFiles()
			.filter((f) => /lang\.set\(/.test(readFileSync(f, 'utf-8')))
			.map((f) => relative(SRC, f).replaceAll('\\', '/'))
			.filter((f) => !SET_ALLOWED.has(f));

		expect(offenders).toEqual([]);
	});
});

describe('the language switch survives blocked storage', () => {
	/**
	 * `chosen()` and `choose()` touched `localStorage` bare. Where storage access
	 * THROWS — Safari/Chrome with "block all cookies", some embedded webviews —
	 * `setItem` threw before `set()` ran, so the footer's language strip was
	 * simply dead: no navigation, no error the reader could see. Every other
	 * store in the app degrades instead (persisted.ts); this one took the caller
	 * down with it, in exactly the privacy-conscious configurations where the
	 * rest of the app is careful.
	 */
	const blocked = () => {
		const boom = () => {
			throw new DOMException('The operation is insecure.', 'SecurityError');
		};
		vi.stubGlobal('localStorage', { getItem: boom, setItem: boom, removeItem: boom });
	};

	beforeEach(() => {
		setLocale.mockClear();
	});

	it('still performs the switch when the preference cannot be written', () => {
		blocked();
		expect(() => lang.choose('es')).not.toThrow();
		expect(setLocale).toHaveBeenCalledWith('es');
		vi.unstubAllGlobals();
	});

	it('reports no remembered choice rather than throwing', () => {
		blocked();
		expect(() => lang.chosen()).not.toThrow();
		expect(lang.chosen()).toBeNull();
		vi.unstubAllGlobals();
	});
});
