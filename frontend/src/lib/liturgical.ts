/**
 * The season of the Church year a date falls in — the Western calendar
 * (Gregorian Easter), as most of the library's own authors kept it. Shown as a
 * quiet line under the home hero's date: the dashboard is visited daily, and
 * the year it is set in is the Church's as much as the civil one.
 *
 * Pure date arithmetic on the reader's local calendar day; no data, no clock
 * beyond the Date passed in, so the boundaries are tested rather than trusted.
 */
import { localDayNumber } from './dailyArticles';

export type Season = 'advent' | 'christmas' | 'epiphany' | 'lent' | 'holyWeek' | 'easter' | 'pentecost' | 'ordinary';

/** The liturgical colour each season is vested in — the hero's dot wears it. */
export type SeasonColour = 'violet' | 'white' | 'red' | 'green';

export const SEASON_COLOUR: Record<Season, SeasonColour> = {
	advent: 'violet',
	christmas: 'white',
	epiphany: 'white',
	lent: 'violet',
	holyWeek: 'red',
	easter: 'white',
	pentecost: 'red',
	ordinary: 'green'
};

/** A calendar day as a whole number, so a season boundary is a comparison. */
const dayNumber = (y: number, m: number, d: number) => Date.UTC(y, m, d) / 86_400_000;

/** Easter Sunday of `year` (Gregorian; the anonymous "Meeus/Jones/Butcher"
 *  computus), as a day number. */
export function easterDay(year: number): number {
	const a = year % 19;
	const b = Math.floor(year / 100);
	const c = year % 100;
	const d = Math.floor(b / 4);
	const e = b % 4;
	const f = Math.floor((b + 8) / 25);
	const g = Math.floor((b - f + 1) / 3);
	const h = (19 * a + b - d - g + 15) % 30;
	const i = Math.floor(c / 4);
	const k = c % 4;
	const l = (32 + 2 * e + 2 * i - h - k) % 7;
	const m = Math.floor((a + 11 * h + 22 * l) / 451);
	const month = Math.floor((h + l - 7 * m + 114) / 31) - 1;
	const day = ((h + l - 7 * m + 114) % 31) + 1;
	return dayNumber(year, month, day);
}

/** The first Sunday of Advent: four Sundays before Christmas, i.e. the Sunday
 *  falling between November 27 and December 3. */
export function adventStart(year: number): number {
	const christmasEve = dayNumber(year, 11, 24);
	const weekday = new Date(christmasEve * 86_400_000).getUTCDay();
	return christmasEve - weekday - 21;
}

export function liturgicalSeason(date: Date): Season {
	const y = date.getFullYear();
	const today = localDayNumber(date);
	const easter = easterDay(y);

	if (today >= adventStart(y) && today <= dayNumber(y, 11, 24)) return 'advent';
	if (today >= dayNumber(y, 11, 25) || today <= dayNumber(y, 0, 5)) return 'christmas';
	if (today === dayNumber(y, 0, 6)) return 'epiphany';
	if (today >= easter - 46 && today < easter - 7) return 'lent';
	if (today >= easter - 7 && today < easter) return 'holyWeek';
	if (today >= easter && today < easter + 49) return 'easter';
	if (today === easter + 49) return 'pentecost';
	return 'ordinary';
}
