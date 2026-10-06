import type { IconName } from '$lib/components/Icon.svelte';
import type { NavSection } from '$lib/contentNav';

/**
 * Each library section's marks, in one place. The section's COLOUR is app.css's
 * (`data-section` → `--section-hue`); these are its pictures:
 *
 * - `ornament` — the printer's ornament under its page title (`<Fleuron>`),
 *   in gold like every ornament (STYLE_GUIDE §1): a lamp for Books ("Thy word
 *   is a lamp", Ps 119:105), an anchor for Topics (hope, Heb 6:19), a vine for
 *   Plans (abiding, day by day, John 15), a descending dove for Sermons (the
 *   Spirit on the preached word), a laurel for Biographies (the crown of
 *   those who ran the race).
 * - `icon` — the line icon the top nav gives it (sections.test.ts holds the
 *   two to PRIMARY_NAV), worn beside a shelf heading in the section.
 *
 * Its multicolour emblem, beside its page title, is $lib/sectionEmblems.
 */
export type Ornament = 'leaf' | 'lamp' | 'anchor' | 'vine' | 'dove' | 'laurel';

export const SECTION_MARKS: Record<NavSection, { ornament: Ornament; icon: IconName }> = {
	books: { ornament: 'lamp', icon: 'book' },
	topics: { ornament: 'anchor', icon: 'tag' },
	plans: { ornament: 'vine', icon: 'calendar' },
	sermons: { ornament: 'dove', icon: 'mic' },
	biographies: { ornament: 'laurel', icon: 'users' }
};
