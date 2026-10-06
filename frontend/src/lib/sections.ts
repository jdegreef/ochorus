import type { EmblemName } from '$lib/emblems';
import type { IconName } from '$lib/components/Icon.svelte';
import { PRIMARY_NAV, type NavSection } from '$lib/contentNav';

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
 * - `emblem` — the multicolour emblem in the section's hue beside its page
 *   title, from the same art as the topic and plan shelves.
 * - `icon` — the line icon the top nav gives it (read from PRIMARY_NAV, so
 *   the two can't differ), worn beside a shelf heading in the section.
 */
export type Ornament = 'leaf' | 'lamp' | 'anchor' | 'vine' | 'dove' | 'laurel';

const DEVICES: Record<NavSection, { ornament: Ornament; emblem: EmblemName }> = {
	books: { ornament: 'lamp', emblem: 'candle-and-book' },
	topics: { ornament: 'anchor', emblem: 'compass-rose' },
	plans: { ornament: 'vine', emblem: 'pilgrim-road' },
	sermons: { ornament: 'dove', emblem: 'herald-trumpet' },
	biographies: { ornament: 'laurel', emblem: 'laurel-tome' }
};

const navIcon = (section: NavSection): IconName => PRIMARY_NAV.find((d) => d.section === section)!.icon;

export const SECTION_MARKS = Object.fromEntries(
	PRIMARY_NAV.map(({ section }) => [section, { ...DEVICES[section], icon: navIcon(section) }])
) as Record<NavSection, { ornament: Ornament; emblem: EmblemName; icon: IconName }>;
