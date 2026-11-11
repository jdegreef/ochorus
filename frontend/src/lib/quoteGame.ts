/**
 * "Whose words?" — the reader's side of the daily quotation game: their
 * results on this device, the streak, and the line they share.
 *
 * The puzzle itself is the server's (`library.quote_game`: the same for every
 * reader on a date). What is kept here is only what this reader did — one
 * guess per local date — under QUOTE_GAME_KEY, device-local like the reading
 * pace and wiped on sign-out like the rest of the reader's data.
 */
import { readJSON, writeJSON } from './persisted';
import { QUOTE_GAME_KEY } from './reading-schema';
import { currentStreak, shiftDay } from './streak';

/** One day's play: which puzzle, whom they chose, and whether it was right. */
export interface GameResult {
	n: number;
	guess: string;
	right: boolean;
}

/** Results by local `YYYY-MM-DD`. */
export type GameLog = Record<string, GameResult>;

/** Days kept: enough for any streak worth showing, without growing for ever. */
const KEEP_DAYS = 400;
const ISO_DAY = /^\d{4}-\d{2}-\d{2}$/;

const isResult = (v: unknown): v is GameResult =>
	!!v &&
	typeof v === 'object' &&
	typeof (v as GameResult).n === 'number' &&
	typeof (v as GameResult).guess === 'string' &&
	typeof (v as GameResult).right === 'boolean';

/** The stored log, with anything malformed dropped (a corrupt cache never throws). */
export function loadLog(): GameLog {
	const raw = readJSON<Record<string, unknown>>(QUOTE_GAME_KEY, {});
	const log: GameLog = {};
	if (!raw || typeof raw !== 'object') return log;
	for (const [day, r] of Object.entries(raw)) if (ISO_DAY.test(day) && isResult(r)) log[day] = r;
	return log;
}

/** Record `day`'s guess — the first one only: the game is one guess a day. */
export function recordResult(log: GameLog, day: string, result: GameResult): GameLog {
	if (log[day]) return log;
	const cutoff = shiftDay(day, -KEEP_DAYS);
	const next: GameLog = { [day]: result };
	for (const [d, r] of Object.entries(log)) if (d > cutoff) next[d] = r;
	writeJSON(QUOTE_GAME_KEY, next);
	return next;
}

/** Days running answered RIGHT, ending today (or yesterday, before today's
 *  guess) — a wrong answer or a missed day starts it again. */
export function gameStreak(log: GameLog, today: string): number {
	if (log[today] && !log[today].right) return 0;
	return currentStreak(
		Object.entries(log)
			.filter(([, r]) => r.right)
			.map(([d]) => d),
		today
	);
}

/** The last `days` days, oldest first: right, wrong, or not played. */
export function recentDays(
	log: GameLog,
	today: string,
	days = 7
): { day: string; state: 'right' | 'wrong' | 'none' }[] {
	return Array.from({ length: days }, (_, i) => {
		const day = shiftDay(today, i - days + 1);
		const r = log[day];
		return { day, state: r ? (r.right ? 'right' : 'wrong') : 'none' };
	});
}

/** The shared line: "Ochorus · Whose words? No. 42 ✓ · 6-day streak". The
 *  words come in localized; the ✓ / ✗ are the part that reads at a glance in
 *  a chat, whatever the language. */
export function resultLine(opts: { title: string; number: string; right: boolean; streak: string }): string {
	return ['Ochorus', `${opts.title} ${opts.number} ${opts.right ? '✓' : '✗'}`, opts.streak]
		.filter(Boolean)
		.join(' · ');
}
