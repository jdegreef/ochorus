import { readJSON } from './persisted';
import {
	PROGRESS_KEY,
	MARKS_KEY,
	BOOKMARKS_KEY,
	FAVORITES_KEY,
	JOURNAL_KEY,
	parseWorkSlugKey,
	parseWorkKey,
	type ProgressMap,
	type MarksStore,
	type BookmarksStore,
	type WorkKind
} from './reading-schema';
import { cleanStore, visibleEntries } from './journal';
import { listBooks, listSermons, listAuthors, listPlans } from './library-public';

/**
 * "Export my data" — turns the reader's device-local reading record (positions,
 * highlights + notes, bookmarks, favorites) into two portable files:
 *
 *  - a lossless JSON bundle (everything, re-importable), and
 *  - a human-readable Markdown digest.
 *
 * Highlight *text* isn't stored on the device (marks hold character offsets, and
 * the passage is sliced from the chapter at render time — see rangeMarks.ts), so
 * the digest reports each work's notes, bookmarked passages, favorites and
 * reading places, plus a highlight count; the full highlighted passages remain
 * viewable in the Notebook. Titles are resolved from the public catalogs
 * (best-effort — a slug that can't be resolved falls back to itself).
 */

export interface ExportNote {
	chapter_order: number;
	chapter_title: string;
	color: string;
	note: string;
}
export interface ExportBookmark {
	chapter_title: string;
	snippet: string;
}
export interface ExportWork {
	kind: WorkKind;
	slug: string;
	title: string;
	author: string;
	position: { chapter_order: number; chapter_title: string } | null;
	highlight_count: number;
	notes: ExportNote[];
	bookmarks: ExportBookmark[];
}
export interface ExportFavorite {
	kind: string;
	slug: string;
	title: string;
	saved_at: string;
}
/** A Notebook entry — the reader's own note or prayer. */
export interface ExportJournalEntry {
	kind: 'note' | 'prayer';
	title: string;
	body: string;
	ref: string;
	written_at: string;
	answered_at: string | null;
	answer: string;
	/** Who a prayer is for, and its dated updates. */
	person: string;
	updates: { at: string; text: string }[];
	/** The passage it was written from ("Humility · Chapter 2"), and its words. */
	source: { title: string; quote: string } | null;
}
export interface ExportBundle {
	app: 'Ochorus';
	exported_at: string;
	works: ExportWork[];
	favorites: ExportFavorite[];
	journal: ExportJournalEntry[];
}

type TitleMaps = {
	book: Map<string, { title: string; author: string }>;
	sermon: Map<string, { title: string; author: string }>;
	bio: Map<string, { title: string; author: string }>;
	plan: Map<string, { title: string; author: string }>;
};

/** Turn a slug into a passable label when the catalog lookup misses. */
function unslug(slug: string): string {
	return slug.replace(/-/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());
}

async function loadTitles(language: string): Promise<TitleMaps> {
	const [books, sermons, authors, plans] = await Promise.all([
		listBooks(language).catch(() => []),
		listSermons(language).catch(() => []),
		listAuthors(language).catch(() => []),
		listPlans(language).catch(() => [])
	]);
	const maps: TitleMaps = { book: new Map(), sermon: new Map(), bio: new Map(), plan: new Map() };
	for (const b of books) maps.book.set(b.slug, { title: b.title, author: b.author?.name ?? '' });
	for (const s of sermons) maps.sermon.set(s.slug, { title: s.title, author: s.author?.name ?? '' });
	// A "bio" work is keyed by the author's slug; its title is the author's name.
	for (const a of authors) maps.bio.set(a.slug, { title: a.name, author: a.name });
	for (const p of plans) maps.plan.set(p.slug, { title: p.title, author: '' });
	return maps;
}

/**
 * The favorites store and the title catalog name the same thing differently:
 * a favorited author is kind `author` (see FavoriteKind), while its titles are
 * keyed `bio` here, after the work kind. So `lookup(maps, 'author', …)` found
 * no map at all and every favorited author fell through to `unslug(slug)` —
 * "J C Ryle" for J. C. Ryle, with the real name sitting unused in `maps.bio`.
 */
const TITLE_MAP_KIND: Record<string, keyof TitleMaps> = { author: 'bio' };

function lookup(maps: TitleMaps, kind: string, slug: string): { title: string; author: string } {
	const m = maps[TITLE_MAP_KIND[kind] ?? (kind as keyof TitleMaps)];
	return m?.get(slug) ?? { title: unslug(slug), author: '' };
}

/** Fetch catalogs and assemble the full export bundle from localStorage. */
export async function collectExport(
	language: string,
	nowISO: string
): Promise<ExportBundle> {
	const maps = await loadTitles(language);
	const progress = readJSON<ProgressMap>(PROGRESS_KEY, {});
	const marksStore = readJSON<MarksStore>(MARKS_KEY, {});
	const bookmarksStore = readJSON<BookmarksStore>(BOOKMARKS_KEY, {});
	const favorites = readJSON<Record<string, number>>(FAVORITES_KEY, {});

	// Group everything under a per-work key so highlights, notes, bookmarks and
	// the reading position for one work land together.
	const works = new Map<string, ExportWork>();
	const workFor = (kind: WorkKind, slug: string): ExportWork => {
		const key = `${kind}:${slug}`;
		let w = works.get(key);
		if (!w) {
			const meta = lookup(maps, kind, slug);
			w = {
				kind,
				slug,
				title: meta.title,
				author: meta.author,
				position: null,
				highlight_count: 0,
				notes: [],
				bookmarks: []
			};
			works.set(key, w);
		}
		return w;
	};

	// Reading positions.
	for (const [key, rec] of Object.entries(progress)) {
		const { kind, slug } = parseWorkSlugKey(key);
		workFor(kind, slug).position = { chapter_order: rec.order, chapter_title: '' };
	}

	// Highlights + notes.
	for (const [key, entry] of Object.entries(marksStore)) {
		const parsed = parseWorkKey(key);
		if (!parsed) continue;
		const w = workFor(parsed.kind, parsed.slug);
		for (const m of entry.m ?? []) {
			w.highlight_count += 1;
			if (m.note) {
				w.notes.push({
					chapter_order: parsed.order,
					chapter_title: '',
					color: m.color ?? 'gold',
					note: m.note
				});
			}
		}
	}

	// Bookmarks (books only) — these carry their own snippet + chapter title.
	for (const [slug, list] of Object.entries(bookmarksStore)) {
		const w = workFor('book', slug);
		for (const b of list ?? []) w.bookmarks.push({ chapter_title: b.title, snippet: b.snippet });
	}

	// Favorites.
	const favList: ExportFavorite[] = Object.entries(favorites)
		.map(([key, at]) => {
			const i = key.indexOf(':');
			const kind = key.slice(0, i);
			const slug = key.slice(i + 1);
			return { kind, slug, title: lookup(maps, kind, slug).title, saved_at: new Date(at).toISOString() };
		})
		.sort((a, b) => a.kind.localeCompare(b.kind) || a.title.localeCompare(b.title));

	const workList = [...works.values()].sort(
		(a, b) => a.kind.localeCompare(b.kind) || a.title.localeCompare(b.title)
	);

	// The Notebook's own writing, newest first; tombstones are not the reader's words.
	const journal: ExportJournalEntry[] = visibleEntries(
		cleanStore(readJSON<unknown>(JOURNAL_KEY, {}))
	).map((e) => ({
		kind: e.kind,
		title: e.title,
		body: e.body,
		ref: e.ref,
		written_at: new Date(e.createdAt).toISOString(),
		answered_at: e.answeredAt ? new Date(e.answeredAt).toISOString() : null,
		answer: e.answer,
		person: e.person,
		updates: e.updates.map((u) => ({ at: new Date(u.at).toISOString(), text: u.text })),
		source: e.source ? { title: e.source.title, quote: e.source.quote } : null
	}));

	return { app: 'Ochorus', exported_at: nowISO, works: workList, favorites: favList, journal };
}

/** Render the bundle as a readable Markdown document. */
export function toMarkdown(b: ExportBundle): string {
	const lines: string[] = [];
	lines.push('# My Ochorus reading', '', `_Exported ${b.exported_at.slice(0, 10)}._`, '');

	if (b.journal.length) {
		lines.push('## My Notebook', '');
		for (const j of b.journal) {
			const label = j.kind === 'note' ? 'Note' : j.answered_at ? 'Answered prayer' : 'Prayer';
			lines.push(`### ${j.title || label} — ${j.written_at.slice(0, 10)}`);
			const forWhom = j.person ? ` for ${j.person}` : '';
			lines.push(`_${label}${forWhom}${j.ref ? ` · ${j.ref}` : ''}_`, '');
			if (j.source) lines.push(`> ${j.source.quote}`, `> — ${j.source.title}`, '');
			if (j.body) lines.push(j.body, '');
			for (const u of j.updates) lines.push(`- ${u.at.slice(0, 10)}: ${u.text}`);
			if (j.updates.length) lines.push('');
			if (j.answered_at) {
				lines.push(`**Answered ${j.answered_at.slice(0, 10)}.**${j.answer ? ` ${j.answer}` : ''}`, '');
			}
		}
	}

	if (b.favorites.length) {
		lines.push('## Favorites', '');
		for (const f of b.favorites) lines.push(`- **${f.title}** _(${f.kind})_`);
		lines.push('');
	}

	const withStuff = b.works.filter(
		(w) => w.notes.length || w.bookmarks.length || w.highlight_count || w.position
	);
	if (withStuff.length) {
		lines.push('## Works', '');
		for (const w of withStuff) {
			lines.push(`### ${w.title}${w.author ? ` — ${w.author}` : ''}`);
			if (w.position) lines.push(`- Reading place: chapter ${w.position.chapter_order}`);
			if (w.highlight_count) lines.push(`- ${w.highlight_count} highlight${w.highlight_count === 1 ? '' : 's'}`);
			if (w.notes.length) {
				lines.push('', '**Notes**');
				for (const n of w.notes) lines.push(`- (ch. ${n.chapter_order}) ${n.note}`);
			}
			if (w.bookmarks.length) {
				lines.push('', '**Bookmarks**');
				for (const bm of w.bookmarks) lines.push(`- ${bm.chapter_title}: “${bm.snippet}”`);
			}
			lines.push('');
		}
		lines.push(
			'_Your highlighted passages are viewable in full in the Notebook on Ochorus._',
			''
		);
	}

	if (lines.length <= 4) lines.push('_No reading data on this device yet._', '');
	return lines.join('\n');
}

/** Trigger a client-side file download. */
export function downloadFile(filename: string, mime: string, content: string) {
	const blob = new Blob([content], { type: mime });
	const url = URL.createObjectURL(blob);
	const a = document.createElement('a');
	a.href = url;
	a.download = filename;
	document.body.appendChild(a);
	a.click();
	a.remove();
	URL.revokeObjectURL(url);
}
