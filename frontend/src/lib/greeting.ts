/**
 * The dashboard's greeting turns with the reader's day: morning from 4am,
 * afternoon from noon, evening from 5pm — and through the night, evening
 * still (a "good morning" at 1am reads as a mistake, not a welcome).
 */
export type DayPart = 'morning' | 'afternoon' | 'evening';

export function dayPart(hour: number): DayPart {
	if (hour >= 4 && hour < 12) return 'morning';
	if (hour >= 12 && hour < 17) return 'afternoon';
	return 'evening';
}

/**
 * The name a greeting uses: the first word of the reader's display name
 * ("Welcome back, James", not the full name — warmer, and it fits a phone),
 * else the local part of their email. Never the full address.
 */
export function greetingName(displayName: string, email: string | undefined): string {
	const first = displayName.trim().split(/\s+/)[0];
	return first || (email?.split('@')[0] ?? '');
}
