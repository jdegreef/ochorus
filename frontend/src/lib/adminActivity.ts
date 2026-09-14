/**
 * Pure shaping for the admin Activity log — everything the page derives from a
 * row that has no reason to live inside a `.svelte` file: which family an action
 * belongs to, what its target points at, how its detail reads, how the flat
 * newest-first list breaks into days, and the few figures the header shows.
 *
 * Kept here (and covered by `adminActivity.test.ts`) so the component is markup
 * over already-shaped data, and so a new action or target kind is a change with
 * a test rather than a surprise in the view. Language *names* are the one thing
 * deliberately left out: the code→autonym map is `localeName`, and resolving it
 * here would drag a `.svelte.ts` rune module into a plain unit.
 */
import { initials as nameInitials, unslug } from './strings';
import type { AdminActionRow } from './library-admin';

/**
 * The five families an action belongs to. Colour is spent on the two that reach
 * readers (a language going live, a document published); the rest are told apart
 * by their glyph, which is the same judgement the old two-tone `tone()` made.
 */
export type Category = 'language' | 'content' | 'review' | 'translation' | 'author' | 'access';

/** Which glyph a row wears. The view owns the actual path data. */
export type IconName =
	| 'globe'
	| 'edit'
	| 'sliders'
	| 'translate'
	| 'author'
	| 'document'
	| 'approve'
	| 'undo';

export interface ActionMeta {
	category: Category;
	icon: IconName;
	/** Reader-facing — drawn in the accent tint rather than muted. */
	loud: boolean;
}

const META: Record<string, ActionMeta> = {
	'language.create': { category: 'language', icon: 'globe', loud: false },
	'language.settings': { category: 'language', icon: 'edit', loud: false },
	'language.thresholds': { category: 'language', icon: 'sliders', loud: false },
	'language.go_live': { category: 'language', icon: 'globe', loud: true },
	'translation.job': { category: 'translation', icon: 'translate', loud: false },
	'content.edit_job': { category: 'content', icon: 'edit', loud: false },
	'author.create': { category: 'author', icon: 'author', loud: false },
	'content.publish': { category: 'content', icon: 'document', loud: true },
	'content.unpublish': { category: 'content', icon: 'document', loud: true },
	'review.decide': { category: 'review', icon: 'approve', loud: false },
	'review.undo': { category: 'review', icon: 'undo', loud: false },
	'role.grant': { category: 'access', icon: 'sliders', loud: true },
	'role.revoke': { category: 'access', icon: 'sliders', loud: true }
};

/** The categories, in the order the filter offers them. */
export const CATEGORIES: readonly Category[] = [
	'language',
	'content',
	'review',
	'translation',
	'author',
	'access'
];

/**
 * An action's family, glyph and weight. Unknown actions still render: a new
 * endpoint self-files by the part before the dot and shows up neutral rather
 * than throwing — the same generosity `summariseDetail` extends to new fields.
 */
export function actionMeta(action: string): ActionMeta {
	const known = META[action];
	if (known) return known;
	const prefix = action.split('.')[0] as Category;
	const category = CATEGORIES.includes(prefix) ? prefix : 'content';
	return { category, icon: 'document', loud: false };
}

export interface ParsedTarget {
	/** The display bucket — 'document' is what a `book:` target is called here. */
	kind: 'language' | 'author' | 'document' | 'other';
	/** The slug/code, for resolving a display name in the view. */
	slug: string;
	/** A book target's language edition, if present. */
	lang?: string;
	/** Where the row links, or null when nothing sensible does. */
	href: string | null;
}

/**
 * A target string (`language:sw`, `book:humility:es`, `sermon:grace:en`,
 * `author:andrew-murray`) split into its kind, slug and a link. The convention
 * is `kind:slug[:lang]`, free text by design on the backend, so anything
 * off-shape becomes a plain, unlinked label rather than a broken link.
 */
export function parseTarget(target: string): ParsedTarget {
	const [kind, slug, lang] = (target ?? '').split(':');
	if (kind === 'language' && slug)
		return { kind: 'language', slug, href: `/admin/languages/${slug}` };
	if (kind === 'author' && slug) return { kind: 'author', slug, href: `/authors/${slug}` };
	if (kind === 'book' && slug)
		return { kind: 'document', slug, lang: lang || undefined, href: `/admin/books/${slug}` };
	if (kind === 'sermon' && slug)
		return { kind: 'document', slug, lang: lang || undefined, href: `/admin/sermons/${slug}` };
	return { kind: 'other', slug: target ?? '', href: null };
}

/** `james.degreef@gmail.com` → `James Degreef`; blank actor → `a local dev request`. */
export function actorName(email: string): string {
	if (!email) return 'a local dev request';
	return unslug((email.split('@')[0] || '').replace(/[._]/g, '-')) || email;
}

/** The avatar monogram: `JD` for `james.degreef@…`, `·` for the tokenless request. */
export function initials(email: string): string {
	if (!email) return '·';
	return nameInitials(actorName(email));
}

export type DetailPart =
	/** A review verdict — the word, foregrounded, not a `key: value`. */
	| { kind: 'outcome'; text: string }
	/** A change, rendered `label from → to`. */
	| { kind: 'diff'; label: string; from: string; to: string }
	/** A reviewer's free-text reason, shown as a quote. */
	| { kind: 'quote'; text: string }
	/** A URL-valued field (e.g. a filed translation issue), shown as a link chip. */
	| { kind: 'link'; text: string; href: string }
	/** Anything else, `label: value`. */
	| { kind: 'text'; text: string };

/**
 * A compact label for a URL: a GitHub issue/PR shows as `#1852`, anything else
 * as its hostname. Keeps the append-only log readable — a raw issue URL per row
 * is noise, and `#1852` is what an admin actually recognises.
 */
export function linkLabel(url: string): string {
	const m = url.match(/\/(?:issues|pull)\/(\d+)\b/);
	if (m) return `#${m[1]}`;
	try {
		return new URL(url).hostname.replace(/^www\./, '');
	} catch {
		return url;
	}
}

function formatValue(label: string, v: unknown): string {
	if (typeof v === 'boolean') return v ? 'yes' : 'no';
	if (Array.isArray(v)) return v.join(', ');
	if (v && typeof v === 'object') return String(Object.keys(v).length);
	const s = String(v);
	// A bare readiness/coverage number is a percentage; say so.
	return /readiness|coverage/.test(label) && /^\d+$/.test(s) ? `${s}%` : s;
}

/**
 * The detail object as reading parts rather than a JSON blob. Three shapes get
 * lifted out of the generic `key: value` run: a review `outcome` leads as the
 * verdict; a `*_from` / `*_to` pair collapses into one `before → after`; a
 * `reason` becomes a quote. Everything else stays a labelled value, so a field
 * a future endpoint invents still reads without an edit here.
 */
export function summariseDetail(detail: Record<string, unknown>): DetailPart[] {
	const entries = Object.entries(detail ?? {}).filter(
		([, v]) => v !== '' && v !== null && v !== undefined
	);
	// The non-empty fields, for pairing — a *_to that is null/empty was already
	// dropped from `entries`, so the pair below collapses only when both sides
	// carry a value and never renders "→ null".
	const kept = new Map(entries);
	const consumed = new Set<string>();
	const parts: DetailPart[] = [];

	// The verdict leads, if there is one.
	const outcome = entries.find(([k]) => k === 'outcome');
	if (outcome) {
		parts.push({ kind: 'outcome', text: String(outcome[1]) });
		consumed.add('outcome');
	}
	// A *_from / *_to pair reads as one before → after.
	for (const [k, v] of entries) {
		if (consumed.has(k) || !k.endsWith('_from')) continue;
		const base = k.slice(0, -'_from'.length);
		const toKey = `${base}_to`;
		if (kept.has(toKey)) {
			const label = base.replace(/_/g, ' ');
			parts.push({ kind: 'diff', label, from: formatValue(label, v), to: formatValue(label, kept.get(toKey)) });
			consumed.add(k);
			consumed.add(toKey);
		}
	}
	// Everything else: a reason as a quote, the rest as labelled values.
	for (const [k, v] of entries) {
		if (consumed.has(k)) continue;
		if (k === 'reason') {
			parts.push({ kind: 'quote', text: String(v) });
			continue;
		}
		if (typeof v === 'string' && /^https?:\/\//.test(v)) {
			parts.push({ kind: 'link', text: linkLabel(v), href: v });
			continue;
		}
		const label = k.replace(/_/g, ' ');
		parts.push({ kind: 'text', text: `${label}: ${formatValue(label, v)}` });
	}
	return parts;
}

/** The precise stamp, kept for the row's hover title and second line. */
export function absoluteTime(iso: string): string {
	return new Date(iso).toLocaleString('en', {
		month: 'short',
		day: 'numeric',
		hour: '2-digit',
		minute: '2-digit'
	});
}

/** `Today`, `Yesterday`, else `Sunday, September 6` — a calendar-day heading. */
export function dayLabel(iso: string, now: Date = new Date()): string {
	const d = new Date(iso);
	const startOf = (x: Date) => new Date(x.getFullYear(), x.getMonth(), x.getDate()).getTime();
	const diffDays = Math.round((startOf(now) - startOf(d)) / 86_400_000);
	if (diffDays <= 0) return 'Today';
	if (diffDays === 1) return 'Yesterday';
	return d.toLocaleDateString('en', { weekday: 'long', month: 'long', day: 'numeric' });
}

export interface DayGroup {
	label: string;
	rows: AdminActionRow[];
}

/**
 * The flat, newest-first list broken into calendar days. Runs the rows in order
 * — they arrive sorted — so a day's block is contiguous and the order within it
 * is preserved; no sorting, no bucketing by key.
 */
export function groupByDay(rows: AdminActionRow[], now: Date = new Date()): DayGroup[] {
	const groups: DayGroup[] = [];
	for (const row of rows) {
		const label = dayLabel(row.at, now);
		const last = groups[groups.length - 1];
		if (last && last.label === label) last.rows.push(row);
		else groups.push({ label, rows: [row] });
	}
	return groups;
}

/** How many rows fall in each category (for the filter chips' counts). */
export function categoryCounts(rows: AdminActionRow[]): Record<Category, number> {
	const counts = Object.fromEntries(CATEGORIES.map((c) => [c, 0])) as Record<Category, number>;
	for (const r of rows) counts[actionMeta(r.action).category] += 1;
	return counts;
}

/** The most active actor in the window, and how many of the rows are theirs. */
export function busiestActor(rows: AdminActionRow[]): { actor: string; count: number } {
	const tally = new Map<string, number>();
	for (const r of rows) tally.set(r.actor, (tally.get(r.actor) ?? 0) + 1);
	let actor = '';
	let count = 0;
	for (const [a, n] of tally) {
		if (n > count) {
			count = n;
			actor = a;
		}
	}
	return { actor, count };
}

/** Today's tally: all actions, and the reader-facing (loud) share of them. */
export function todayStats(
	rows: AdminActionRow[],
	now: Date = new Date()
): { count: number; readerFacing: number } {
	let count = 0;
	let readerFacing = 0;
	for (const r of rows) {
		if (dayLabel(r.at, now) !== 'Today') continue;
		count += 1;
		if (actionMeta(r.action).loud) readerFacing += 1;
	}
	return { count, readerFacing };
}

/**
 * The filtered rows as CSV — the visible/filtered set, so an export matches what
 * the admin is looking at. Detail is kept as JSON in one column rather than
 * spread, so the columns are stable whatever an action recorded.
 */
export function toCsv(rows: AdminActionRow[]): string {
	// Wrap and double quotes; also neutralise a leading =,+,-,@ so a value can't
	// be read as a formula when the export is opened in a spreadsheet.
	const esc = (v: string) => {
		const safe = /^[=+\-@\t\r]/.test(v) ? `'${v}` : v;
		return `"${safe.replace(/"/g, '""')}"`;
	};
	const header = ['at', 'action', 'label', 'actor', 'target', 'detail'];
	const body = rows.map((r) =>
		[r.at, r.action, r.label, r.actor, r.target, JSON.stringify(r.detail ?? {})]
			.map((c) => esc(String(c)))
			.join(',')
	);
	return [header.join(','), ...body].join('\n');
}
