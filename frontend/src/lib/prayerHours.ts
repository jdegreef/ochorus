/**
 * The hours of prayer, as the home hero's sky keeps them: the reader's clock
 * named the way the Daily Office names the day — Vigils in the night, Lauds
 * at dawn, Terce, Sext and None through the working day, Vespers at sunset,
 * Compline before sleep. Approximate on purpose (the Office follows the sun,
 * not a clock); close enough to give the sky its colour and the hour a name.
 *
 * Pure: no clock beyond the Date passed in.
 */
export type PrayerHour = 'vigils' | 'lauds' | 'terce' | 'sext' | 'none' | 'vespers' | 'compline';

/** Each hour from the clock hour it begins at, in order through the day. */
const BEGINS: readonly [number, PrayerHour][] = [
	[0, 'vigils'],
	[5, 'lauds'],
	[8, 'terce'],
	[11, 'sext'],
	[14, 'none'],
	[17, 'vespers'],
	[20, 'compline']
];

export function prayerHour(hour: number): PrayerHour {
	let named: PrayerHour = 'vigils';
	for (const [from, name] of BEGINS) if (hour >= from) named = name;
	return named;
}

/** The sun is up from Lauds until Compline; the moon has the rest. */
const SUNRISE = 5;
const SUNSET = 20;

/**
 * Where the sun (by day) or the moon (by night) stands on its arc over the
 * band: `along` runs 0 → 1 from the rising horizon to the setting one, and
 * `height` 0 → 1 → 0 from the horizon up to its noon (or midnight) and down.
 */
export function skyBody(date: Date): { body: 'sun' | 'moon'; along: number; height: number } {
	const h = date.getHours() + date.getMinutes() / 60;
	const day = h >= SUNRISE && h < SUNSET;
	const span = day ? SUNSET - SUNRISE : 24 - SUNSET + SUNRISE;
	const along = ((h - (day ? SUNRISE : SUNSET) + 24) % 24) / span;
	return { body: day ? 'sun' : 'moon', along, height: Math.sin(along * Math.PI) };
}
