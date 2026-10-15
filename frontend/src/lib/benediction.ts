/**
 * The footer's closing word: a blessing from Scripture that turns with the
 * Church year — Romans 15:13 in Advent, Jude 24–25 through Lent and Holy Week,
 * Hebrews 13:20–21 in Eastertide, 2 Corinthians 13:14 at Pentecost, and the
 * Aaronic blessing (Numbers 6:24–26) the rest of the year.
 *
 * Every text is VERBATIM from the locale's own Bible (the one
 * backend/library/language_seed.py names), fetched by
 * scripts/fetch-benedictions.mjs into benediction.generated.ts — never typed or
 * translated here. A locale without an entry shows no blessing rather than
 * another language's. The licensed texts among them (hi, lg, am) are credited
 * by the footer's Bible-credit line, which renders on exactly those locales.
 *
 * The season is read from the date where the page renders: at build for the
 * prerendered HTML, then the reader's own day on hydration — so a page built
 * in the last days of Lent still closes on Easter's blessing on Easter Day.
 */
import { BLESSINGS } from './benediction.generated';
import { liturgicalSeason, type Season } from './liturgical';

export type BlessingKey = 'aaronic' | 'hope' | 'keep' | 'shepherd' | 'grace';

export type Blessing = {
	/** The book as that Bible names it ("Numbers", "Hesabu", "민수기"). */
	book: string;
	/** Chapter and verses in that Bible's own numbering ("6:24–26"). */
	passage: string;
	text: string;
};

export const SEASON_BLESSING: Readonly<Record<Season, BlessingKey>> = {
	advent: 'hope',
	christmas: 'aaronic',
	epiphany: 'aaronic',
	lent: 'keep',
	holyWeek: 'keep',
	easter: 'shepherd',
	pentecost: 'grace',
	ordinary: 'aaronic'
};

const byLocale = BLESSINGS as Readonly<Record<string, Record<BlessingKey, Blessing> & { bible: string }>>;

/** The blessing `locale`'s Bible gives for `date`'s season, or null. */
export function blessingFor(locale: string, date: Date = new Date()): Blessing | null {
	return byLocale[locale]?.[SEASON_BLESSING[liturgicalSeason(date)]] ?? null;
}

/** The Take Root code each locale's blessings were fetched from. */
export function blessingBible(locale: string): string | null {
	return byLocale[locale]?.bible ?? null;
}
