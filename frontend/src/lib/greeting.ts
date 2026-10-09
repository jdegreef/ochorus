/**
 * The dashboard's greeting turns with the reader's day: morning from 4am,
 * afternoon from noon, evening from 5pm — and through the night, evening
 * still (a "good morning" at 1am reads as a mistake, not a welcome).
 *
 * Evening starts later where the language's evening greeting means NIGHT:
 * Spanish "Buenas noches" and Portuguese "Boa noite" belong from about 8pm;
 * before that it is still "Buenas tardes" / "Boa tarde".
 */
export type DayPart = 'morning' | 'afternoon' | 'evening';

const EVENING_FROM: Record<string, number> = { es: 20, pt: 20 };

export function dayPart(hour: number, lang = 'en'): DayPart {
	if (hour >= 4 && hour < 12) return 'morning';
	if (hour >= 12 && hour < (EVENING_FROM[lang] ?? 17)) return 'afternoon';
	return 'evening';
}

/** A title or an initial, not a given name: "Rev.", "Dr", "J." */
const NOT_A_NAME = /^(?:.|rev|revd|dr|mr|mrs|ms|miss|fr|sr|br|pastor|prof|sir)\.?$/i;

/**
 * The name a greeting uses: the reader's first name ("Good evening, James" —
 * warmer than the full name, and it fits a phone). A display name that opens
 * with a title or an initial ("Rev. John Smith", "J. R. Miller") is used whole,
 * as the reader wrote it, rather than greeting "Rev." or "J.".
 *
 * With no display name, the first word of the email's local part, if it reads
 * as a name: `james.degreef+1@…` greets "James"; `jd1987@…` or `x@…` greets
 * no one, and the hero says a plain "Good afternoon". Never the address, and
 * never a handle with dots, digits or a `+tag` in it (a reader once saw
 * "Good afternoon, james.degreef+1").
 */
export function greetingName(displayName: string, email: string | undefined): string {
	const full = displayName.trim().replace(/\s+/g, ' ');
	if (full) {
		const first = full.split(' ')[0];
		return NOT_A_NAME.test(first) ? full : first;
	}
	const word = email?.split('@')[0].split('+')[0].split(/[._-]/)[0] ?? '';
	return /^\p{L}{2,}$/u.test(word) ? word[0].toLocaleUpperCase() + word.slice(1) : '';
}
