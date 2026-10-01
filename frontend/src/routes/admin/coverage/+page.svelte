<script lang="ts">
	import { browser } from '$app/environment';
	import { replaceState } from '$app/navigation';
	import { dismissable } from '$lib/actions/dismissable';
	import { adminResource } from '$lib/adminResource.svelte';
	import AdminGate from '$lib/components/AdminGate.svelte';
	import ProgressBar from '$lib/components/ProgressBar.svelte';
	import { ApiError } from '$lib/api';
	import { auth } from '$lib/auth.svelte';
	import {
		getAdminCoverage,
		getAdminTranslationJobs,
		createAdminTranslationJob,
		markTranslationCurrent,
		type AdminCoverageRow,
		type AdminCoverageLanguage,
		type AdminTranslationJob,
		type TranslationJobType,
		type ReviewKind
	} from '$lib/library-admin';

	// Load the open translation queue right after coverage — via onLoad, so it
	// waits for auth to settle and re-runs on every (authenticated) refresh, the
	// way adminResource already sequences a page's dependent fetches. Firing it
	// from a bare $effect instead would race the Supabase session restore: the
	// pre-auth GET 403s and, with no auth dependency, never re-runs.
	const coverage = adminResource(getAdminCoverage, 'Something went wrong loading coverage.', () =>
		void loadJobs()
	);
	const cov = $derived(coverage.data);

	// Queueing translation work is super-admin-only: a language admin reads the
	// matrix (state + what's already queued) but never files jobs from it. UX only
	// — the POST is gated server-side too (see admin_views/jobs.py).
	const canQueue = $derived(auth.isAdmin);

	type Tab = 'books' | 'sermons' | 'plans' | 'bios' | 'articles';
	// The view lives in the querystring (tab, filters, order, grouping), so a
	// reload restores it and a link opens exactly this view for a colleague.
	// Seeded here, one-of-a-set values validated; written back by syncUrl().
	const init = browser ? new URLSearchParams(location.search) : new URLSearchParams();
	const pick = <T extends string>(key: string, allowed: readonly T[], fallback: T): T => {
		const v = init.get(key) as T | null;
		return v && allowed.includes(v) ? v : fallback;
	};
	const TAB_KEYS = ['books', 'sermons', 'plans', 'bios', 'articles'] as const;
	let tab = $state<Tab>(pick('tab', TAB_KEYS, 'books'));

	const TABS: { key: Tab; label: string }[] = [
		{ key: 'books', label: 'Books' },
		{ key: 'sermons', label: 'Sermons' },
		{ key: 'plans', label: 'Plans' },
		{ key: 'bios', label: 'Biographies' },
		{ key: 'articles', label: 'Articles' }
	];

	// Each tab is one job type (the queue's singular names).
	const JOB_TYPE: Record<Tab, TranslationJobType> = {
		books: 'book',
		sermons: 'sermon',
		plans: 'plan',
		bios: 'bio',
		articles: 'article'
	};

	// `?? []` guards the deploy window where the SPA carries a new tab before the
	// API's payload does: a missing `cov[tab]` must render empty, not throw.
	const rows = $derived<AdminCoverageRow[]>(cov?.[tab] ?? []);
	// Hidden languages (a per-viewer preference, like Compact) drop out of the
	// whole matrix — columns, totals, "+N", Priority, selection and CSV — so the
	// view is about the languages this person actually works on.
	const HIDDEN_KEY = 'ochorus:admin-coverage-hidden-langs';
	let hiddenLangs = $state<string[]>([]);
	try {
		const raw = browser ? localStorage.getItem(HIDDEN_KEY) : null;
		const parsed: unknown = raw ? JSON.parse(raw) : [];
		if (Array.isArray(parsed)) hiddenLangs = parsed.filter((c) => typeof c === 'string');
	} catch {
		// storage blocked or garbled — show every language
	}
	function setHidden(next: string[]) {
		hiddenLangs = next;
		// A hidden "Gaps in" language would keep filtering invisibly.
		if (gapLang && next.includes(gapLang)) gapLang = '';
		try {
			localStorage.setItem(HIDDEN_KEY, JSON.stringify(next));
		} catch {
			// storage blocked — the choice holds for this visit
		}
	}
	const allLangs = $derived(cov?.languages ?? []);
	const langs = $derived(allLangs.filter((l) => !hiddenLangs.includes(l.code)));
	// Only codes that are actually columns count as hidden (a remembered code
	// for a language that has since gone isn't worth mentioning).
	const hiddenCount = $derived(allLangs.length - langs.length);

	// Crosshair: the row highlights on hover already; this tints the hovered
	// (or keyboard-focused) cell's language column too, header to footer. One
	// delegated handler on the table reads the cell's data-lang.
	let hoverCol = $state<string | null>(null);
	function trackCol(e: Event) {
		const cell = (e.target as HTMLElement | null)?.closest<HTMLElement>('[data-lang]');
		hoverCol = cell?.dataset.lang ?? null;
	}
	let langMenuOpen = $state(false);
	const colTint = (code: string) => (hoverCol === code ? 'bg-surface-2' : '');
	// Books link to their admin detail page; sermons/plans/bios/articles (no admin
	// detail yet) link to their live pages — a biography row is an author.
	const ROW_HREF_BASE: Record<Tab, string> = {
		books: '/admin/books',
		sermons: '/sermons',
		plans: '/plans',
		bios: '/authors',
		articles: '/articles'
	};
	const rowHref = (slug: string) => `${ROW_HREF_BASE[tab]}/${slug}`;
	// An unreviewed cell opens that translation in the review queue, panel open.
	// A link rather than an approve button here: approving means reading the
	// text beside its English and settling its flagged verses, which lives there.
	// Articles aren't in the review queue, so their cells stay plain.
	const REVIEW_KIND: Partial<Record<Tab, ReviewKind>> = {
		books: 'book',
		sermons: 'sermon',
		bios: 'bio'
	};
	const reviewHref = (slug: string, lang: string) => {
		const kind = REVIEW_KIND[tab];
		return kind
			? `/admin/review?${new URLSearchParams({ kind, language: lang, slug })}`
			: null;
	};

	// --- Planner controls: narrow and order the matrix to what you're working on.
	// All of them act on the same derived row list, so totals, the "+N" column
	// counts and the column "queue all" all follow what's actually on screen.
	let q = $state(init.get('q') ?? '');
	const SORTS = ['default', 'priority', 'least', 'most'] as const;
	let sortMode = $state<(typeof SORTS)[number]>(pick('sort', SORTS, 'default'));
	let unreviewedOnly = $state(init.get('unreviewed') === '1');
	// Books only: narrow the matrix to one series, in volume order. With a series
	// chosen, a column's "queue all" files every missing volume of it in that
	// language — "translate the whole series into Swahili" is one press.
	let seriesFilter = $state(init.get('series') ?? '');
	const seriesOptions = $derived(cov?.series ?? []);
	// How many languages a work is present in — the completeness sort key.
	const completeness = (r: AdminCoverageRow) =>
		langs.reduce((n, l) => n + (r.cells[l.code] ? 1 : 0), 0);
	// A work with at least one AI translation still awaiting review — the backlog.
	const hasUnreviewed = (r: AdminCoverageRow) =>
		langs.some((l) => r.cells[l.code] === 'ai_unreviewed');
	// "Gaps in <language>": only the works missing there, so the matrix reads as
	// that language's to-do list. Queued ones stay listed (their ◷ shows it) — the
	// job list loads after coverage, so hiding them would make rows flicker away.
	let gapLang = $state(init.get('gaps') ?? '');
	// Translations made from English that has since changed.
	let staleOnly = $state(init.get('stale') === '1');
	const isStale = (r: AdminCoverageRow, code: string) => !!r.stale?.includes(code);
	// "Still current": a reviewer checked a stale translation against the new
	// English and it holds (the change was a typo fix, say). Books, sermons and
	// articles only — a stale bio clears through its own review/re-translation.
	const STALE_KIND: Partial<Record<Tab, 'book' | 'sermon' | 'article'>> = {
		books: 'book',
		sermons: 'sermon',
		articles: 'article'
	};
	let markingCurrent = $state<string | null>(null);
	async function markCurrent(r: AdminCoverageRow, l: AdminCoverageLanguage) {
		const kind = STALE_KIND[tab];
		if (!kind) return;
		if (
			!confirm(
				`Mark the ${l.name} “${r.title}” as still matching its English? Do this only after checking the English change doesn't affect the translation.`
			)
		)
			return;
		markingCurrent = `${r.slug}:${l.code}`;
		queueError = null;
		try {
			await markTranslationCurrent({ kind, slug: r.slug, language: l.code });
			// Rows are the resource's $state, so this clears the ↻ in place.
			r.stale = r.stale?.filter((c) => c !== l.code);
		} catch (e) {
			queueError = e instanceof ApiError ? e.message : "Couldn't mark it current — try again.";
		} finally {
			markingCurrent = null;
		}
	}
	const tabHasStale = $derived(rows.some((r) => r.stale?.length));

	// --- View: density and grouping. Compact is a per-viewer preference, so it
	// persists in this browser; grouping is a question you ask, so it doesn't.
	// Compact is the default — a matrix is for comparing rows, and the roomy
	// layout fits ~4 books on a screen — so only an explicit '0' opts out.
	const COMPACT_KEY = 'ochorus:admin-coverage-compact';
	let compact = $state(true);
	try {
		compact = !browser || localStorage.getItem(COMPACT_KEY) !== '0';
	} catch {
		// storage blocked — default density
	}
	function setCompact(on: boolean) {
		compact = on;
		try {
			localStorage.setItem(COMPACT_KEY, on ? '1' : '0');
		} catch {
			// storage blocked — the toggle still works for this visit
		}
	}

	// Group by author (books, sermons) or series (books). A tab without the
	// chosen axis simply shows ungrouped, so switching tabs never strands a view.
	const GROUPS = ['none', 'author', 'series'] as const;
	let groupBy = $state<(typeof GROUPS)[number]>(pick('group', GROUPS, 'none'));
	const groupAxis = $derived(
		groupBy === 'author' && (tab === 'books' || tab === 'sermons')
			? 'author'
			: groupBy === 'series' && tab === 'books'
				? 'series'
				: 'none'
	);
	const seriesTitle = $derived(new Map(seriesOptions.map((s) => [s.slug, s.title])));
	const NO_SERIES = '\u0000none'; // sorts nowhere in particular; placed last below
	// Groups keep the matrix's current order — each appears where its first work
	// would, so Priority ranks groups by their most pressing work. "Not in a
	// series" goes last: it's the remainder, not a group.
	const groups = $derived.by(() => {
		if (groupAxis === 'none') return [{ key: '', label: '', rows: visibleRows }];
		const byKey = new Map<string, { key: string; label: string; rows: AdminCoverageRow[] }>();
		for (const r of visibleRows) {
			const key = groupAxis === 'author' ? (r.author ?? '—') : (r.series ?? NO_SERIES);
			const label =
				groupAxis === 'author'
					? key
					: key === NO_SERIES
						? 'Not in a series'
						: (seriesTitle.get(key) ?? key);
			let g = byKey.get(key);
			if (!g) byKey.set(key, (g = { key, label, rows: [] }));
			g.rows.push(r);
		}
		const out = [...byKey.values()];
		const rest = out.findIndex((g) => g.key === NO_SERIES);
		if (rest >= 0) out.push(...out.splice(rest, 1));
		return out;
	});
	let collapsed = $state<Record<string, boolean>>({});

	// Mirror the view into the URL without a navigation; defaults are omitted so
	// the link stays as short as what was actually set.
	$effect(() => {
		const p = new URLSearchParams();
		if (tab !== 'books') p.set('tab', tab);
		if (q.trim()) p.set('q', q.trim());
		if (sortMode !== 'default') p.set('sort', sortMode);
		if (gapLang) p.set('gaps', gapLang);
		if (unreviewedOnly) p.set('unreviewed', '1');
		if (staleOnly) p.set('stale', '1');
		if (seriesFilter) p.set('series', seriesFilter);
		if (groupBy !== 'none') p.set('group', groupBy);
		const qs = p.toString();
		const next = `${location.pathname}${qs ? `?${qs}` : ''}`;
		if (next === `${location.pathname}${location.search}`) return;
		try {
			replaceState(next, {});
		} catch {
			// Router not ready yet (a link carrying an invalid value, rewritten on
			// mount) — the next change writes it.
		}
	});

	let copied = $state(false);
	async function copyLink() {
		try {
			await navigator.clipboard.writeText(location.href);
			copied = true;
			setTimeout(() => (copied = false), 1500);
		} catch {
			// clipboard blocked — the address bar holds the same link
		}
	}

	// The rows as drawn, top to bottom — a collapsed group's rows are hidden,
	// so a shift-click range never selects cells you can't see.
	const shownRows = $derived(groups.flatMap((g) => (g.key && collapsed[g.key] ? [] : g.rows)));

	// --- CSV of the current view: every filtered work (collapsed groups too),
	// one column per language, each cell the state the matrix shows.
	function csvCell(r: AdminCoverageRow, l: AdminCoverageLanguage): string {
		const v = r.cells[l.code];
		const job = v ? undefined : jobFor(r.slug, l.code);
		const base = v
			? ({ public_domain: 'PD', ai_reviewed: 'AI reviewed', ai_unreviewed: 'AI unreviewed' } as Record<string, string>)[v] ??
				'present'
			: job
				? job.state === 'in_progress'
					? 'translating'
					: 'queued'
				: r.blocked
					? 'blocked (copyright)'
					: '';
		return isStale(r, l.code) ? `${base} (out of date)` : base;
	}
	function downloadCsv() {
		const esc = (x: string | number) => {
			const t = String(x);
			return /[",\n]/.test(t) ? `"${t.replaceAll('"', '""')}"` : t;
		};
		const header = ['Work', 'Slug', 'Author', 'Readers', ...langs.map((l) => l.code)];
		const lines = [header, ...visibleRows.map((r) => [
			r.title,
			r.slug,
			r.author ?? '',
			r.readers ?? '',
			...langs.map((l) => csvCell(r, l))
		])].map((row) => row.map(esc).join(','));
		const blob = new Blob([lines.join('\n') + '\n'], { type: 'text/csv;charset=utf-8' });
		const a = document.createElement('a');
		a.href = URL.createObjectURL(blob);
		a.download = `ochorus-coverage-${tab}-${new Date().toISOString().slice(0, 10)}.csv`;
		a.click();
		setTimeout(() => URL.revokeObjectURL(a.href), 1000);
	}
	const toggleGroup = (key: string) => (collapsed = { ...collapsed, [key]: !collapsed[key] });

	// Priority = reader demand × open gaps. A work's weight is 1 + its distinct
	// readers (so an unread work still ranks by its gaps); each open gap counts
	// 1–2× by how much that language's readers search in vain (⌕, scaled to the
	// busiest column). With "Gaps in" set every row is a gap there, so the order
	// is simply most-read first.
	const maxUnmet = $derived(Math.max(1, ...langs.map((l) => l.unmet_searches ?? 0)));
	const gapWeight = (l: AdminCoverageLanguage) => 1 + (l.unmet_searches ?? 0) / maxUnmet;
	const priority = (r: AdminCoverageRow) =>
		(1 + (r.readers ?? 0)) *
		(gapLang ? 1 : langs.reduce((n, l) => n + (isGap(l, r) ? gapWeight(l) : 0), 0));

	const visibleRows = $derived.by(() => {
		let out = rows;
		const term = q.trim().toLowerCase();
		if (term)
			out = out.filter(
				(r) =>
					r.title.toLowerCase().includes(term) || (r.author ?? '').toLowerCase().includes(term)
			);
		if (unreviewedOnly) out = out.filter(hasUnreviewed);
		if (gapLang) out = out.filter((r) => !r.cells[gapLang] && !r.blocked);
		if (staleOnly) out = out.filter((r) => r.stale?.length);
		if (tab === 'books' && seriesFilter) {
			out = out
				.filter((r) => r.series === seriesFilter)
				.sort((a, b) => (a.series_position ?? 0) - (b.series_position ?? 0));
		}
		if (sortMode === 'priority') {
			const score = new Map(out.map((r) => [r.slug, priority(r)]));
			out = [...out].sort((a, b) => score.get(b.slug)! - score.get(a.slug)!);
		} else if (sortMode !== 'default')
			out = [...out].sort((a, b) =>
				sortMode === 'least'
					? completeness(a) - completeness(b)
					: completeness(b) - completeness(a)
			);
		return out;
	});

	// Per-language totals for the active matrix (how many visible works exist in each).
	const totals = $derived(
		langs.map((l) => visibleRows.reduce((n, r) => n + (r.cells[l.code] ? 1 : 0), 0))
	);
	// Completion per language over the visible works that CAN exist there — a
	// copyright-blocked work never will, so it's out of the denominator (and of
	// the numerator: its unpublished editions don't count as progress).
	const reachable = $derived(visibleRows.filter((r) => !r.blocked));
	const completion = $derived(
		langs.map((l) => {
			const have = reachable.reduce((n, r) => n + (r.cells[l.code] ? 1 : 0), 0);
			const of = reachable.length;
			return { have, of, pct: of ? Math.round((have / of) * 100) : 0 };
		})
	);

	// Every cell is the same fixed tile, and each state differs in FILL and
	// border, not just a glyph — so "everything awaiting review in sw" reads as a
	// run of gold down a column, and the states survive greyscale. The legend
	// draws its swatches from these same classes.
	const TILE =
		'inline-flex h-6 min-w-[2.2rem] items-center align-middle justify-center rounded-md px-1.5 text-micro font-semibold leading-none';
	// The "English changed" mark, pinned to a tile's corner by a relative wrapper.
	const STALE =
		'absolute -top-2 -right-2 grid h-4 w-4 place-items-center rounded-full bg-danger text-micro leading-none text-bg';
	// The small status pill under a work's title ("under copyright", "no title").
	const PILL = 'mt-0.5 inline-block rounded-full border px-1.5 text-micro';
	const CELL = {
		public_domain: { label: 'PD', cls: 'bg-surface-2 text-muted' },
		present: { label: '●', cls: 'bg-surface-2 text-text' },
		ai_reviewed: { label: 'AI✓', cls: 'bg-accent text-accent-contrast' },
		ai_unreviewed: { label: 'AI', cls: 'border border-warning bg-warning/10 text-warning' },
		queued: { label: '◷', cls: 'border border-accent-soft-border bg-accent-soft text-accent' },
		translating: { label: '◐', cls: 'border border-accent bg-surface text-accent' },
		missing: { label: '', cls: 'border border-dashed border-border-strong/60' },
		blocked: { label: '⊘', cls: 'text-muted opacity-60' }
	} as const;
	// A state the API adds before this page knows it shows as itself, neutrally,
	// rather than passing for one of the states above.
	const cellMeta = (v: string) =>
		CELL[v as keyof typeof CELL] ?? { label: v, cls: 'border border-border text-muted' };

	// --- Translation queue -----------------------------------------------------
	// Each missing cell (a work not yet in a language) becomes a click target that
	// files a translation job — the same GitHub-issue queue the per-language pages
	// use (POST /api/admin/translation-jobs/). A cell with an open job shows its
	// state instead of the button and links to the issue. A row / column header can
	// also queue every gap along it at once, behind a count confirmation.
	//
	// The matrix tab maps 1:1 onto a job type (plural → singular).
	const jobType = $derived<TranslationJobType>(JOB_TYPE[tab]);

	let jobs = $state<AdminTranslationJob[]>([]);
	// null = the jobs GET failed (unknown): keep the buttons and let POST surface
	// the real error; false = the queue isn't configured (no token) → no buttons.
	let jobsConfigured = $state<boolean | null>(null);
	let queueing = $state<string | null>(null); // "type:slug:lang" while POSTing one
	let queueError = $state<string | null>(null);
	// A bulk enqueue awaiting the user's confirmation (the flooding guard): filing
	// N jobs means N worker sessions, so a row/column press asks before it fires.
	// The job type is captured here, at stage time, so switching tabs while the
	// confirmation is up can't file the targets under the new tab's type.
	let pendingBulk = $state<{
		label: string;
		type: TranslationJobType;
		targets: { slug: string; lang: string }[];
	} | null>(null);
	// Live progress while a confirmed bulk runs (jobs are filed one at a time).
	let bulkProgress = $state<{ done: number; total: number } | null>(null);
	// Stop asks the run to finish the job in flight and file no more.
	let bulkStopping = $state(false);
	let bulkNote = $state<string | null>(null);
	// Any queue POST in flight — disables every enqueue control so two runs can't
	// overlap and trip the API's per-caller throttle.
	const busy = $derived(queueing !== null || bulkProgress !== null);

	async function loadJobs() {
		try {
			const res = await getAdminTranslationJobs();
			jobs = res.jobs;
			jobsConfigured = res.configured;
		} catch {
			jobsConfigured = null;
		}
	}

	const jobKey = (slug: string, lang: string) => `${jobType}:${slug}:${lang}`;
	// Index the open jobs by `type:slug:lang` so each of the matrix's many cells
	// is an O(1) lookup rather than a linear scan of the whole queue.
	const jobIndex = $derived(
		new Map(jobs.map((j) => [`${j.type}:${j.slug}:${j.language}`, j]))
	);
	const jobFor = (slug: string, lang: string) => jobIndex.get(jobKey(slug, lang));
	// A cell is a queueable gap when the language is a translation target, the work
	// has no row in it, and no job is already open. Shared by the buttons, the bulk
	// counts, and the bulk target lists — so a non-queueable column (a stray content
	// language) never offers a button that the POST would only reject.
	// A copyright-blocked work has no gaps: nothing of it may be translated.
	const isGap = (l: AdminCoverageLanguage, r: AdminCoverageRow) =>
		!r.blocked && l.queueable && !r.cells[l.code] && !jobFor(r.slug, l.code);
	// Missing-and-unqueued count per language column, for the header's "queue all".
	// Over the visible rows, so a filtered view queues only what it shows.
	const colGaps = $derived(
		langs.map((l) => visibleRows.reduce((n, r) => n + (isGap(l, r) ? 1 : 0), 0))
	);

	// File one job; returns null on success or a message to show. Type is passed in
	// (not read from jobType) so a bulk run is unaffected by a mid-run tab switch.
	async function enqueueOne(type: TranslationJobType, slug: string, lang: string): Promise<string | null> {
		try {
			const res = await createAdminTranslationJob({ type, slug, language: lang });
			if (!jobs.some((j) => j.url === res.job.url)) jobs = [...jobs, res.job];
			return null;
		} catch (e) {
			const body = e instanceof ApiError ? (e.body as { detail?: string } | null) : null;
			return body?.detail ?? (e instanceof Error ? e.message : 'failed');
		}
	}

	async function queue(slug: string, lang: string) {
		queueError = null;
		queueing = jobKey(slug, lang);
		const err = await enqueueOne(jobType, slug, lang);
		if (err) queueError = err === 'failed' ? "Couldn't queue the translation — try again." : err;
		queueing = null;
	}

	// Stage a row (a work into all its missing languages) or a column (all missing
	// works into a language) for confirmation. No-op when there's nothing to queue.
	function bulkRow(r: AdminCoverageRow) {
		const targets = langs.filter((l) => isGap(l, r)).map((l) => ({ slug: r.slug, lang: l.code }));
		if (targets.length)
			pendingBulk = { label: `“${r.title}” into every missing language`, type: jobType, targets };
	}
	// --- Selecting gaps: ⇧-click a gap to start, ⇧-click another to take every
	// gap in the rectangle between them; ⌘/Ctrl-click toggles one. A plain click
	// still queues one straight away. Queueing a selection goes through the same
	// count confirmation as a row / column.
	const cellKey = (slug: string, lang: string) => `${slug}:${lang}`;
	let selected = $state<Record<string, true>>({});
	let anchor = $state<{ slug: string; lang: string } | null>(null);
	// Only cells still gaps count — one queued meanwhile drops out by itself.
	const selectedTargets = $derived(
		shownRows.flatMap((r) =>
			langs.filter((l) => selected[cellKey(r.slug, l.code)] && isGap(l, r)).map((l) => ({ slug: r.slug, lang: l.code }))
		)
	);
	const selectedByLang = $derived(
		Object.entries(
			selectedTargets.reduce<Record<string, number>>((m, t) => ((m[t.lang] = (m[t.lang] ?? 0) + 1), m), {})
		)
	);
	function clearSelection() {
		selected = {};
		anchor = null;
	}
	// A different tab is a different job type — never carry a selection across.
	$effect(() => {
		void tab;
		clearSelection();
	});
	function selectCell(e: MouseEvent, r: AdminCoverageRow, l: AdminCoverageLanguage) {
		const k = cellKey(r.slug, l.code);
		if (e.shiftKey && anchor) {
			const ri = [shownRows.findIndex((x) => x.slug === anchor!.slug), shownRows.indexOf(r)].sort((a, b) => a - b);
			const li = [langs.findIndex((x) => x.code === anchor!.lang), langs.indexOf(l)].sort((a, b) => a - b);
			if (ri[0] >= 0 && li[0] >= 0) {
				const next = { ...selected };
				for (const row of shownRows.slice(ri[0], ri[1] + 1))
					for (const col of langs.slice(li[0], li[1] + 1))
						if (isGap(col, row)) next[cellKey(row.slug, col.code)] = true;
				selected = next;
				return;
			}
		}
		const { [k]: was, ...rest } = selected;
		selected = was ? rest : { ...rest, [k]: true };
		anchor = { slug: r.slug, lang: l.code };
	}
	function queueSelection() {
		if (!selectedTargets.length) return;
		pendingBulk = {
			label: `the ${selectedTargets.length} selected gap${selectedTargets.length === 1 ? '' : 's'}`,
			type: jobType,
			targets: selectedTargets
		};
		clearSelection();
	}

	function bulkCol(l: AdminCoverageLanguage) {
		const targets = visibleRows.filter((r) => isGap(l, r)).map((r) => ({ slug: r.slug, lang: l.code }));
		if (targets.length)
			pendingBulk = { label: `every missing work into ${l.name}`, type: jobType, targets };
	}

	async function runBulk() {
		if (!pendingBulk) return;
		const { targets, type } = pendingBulk; // type pinned at stage time
		pendingBulk = null;
		queueError = null;
		bulkNote = null;
		bulkStopping = false;
		bulkProgress = { done: 0, total: targets.length };
		let failed = 0;
		let firstErr: string | null = null;
		for (const t of targets) {
			if (bulkStopping) break;
			const err = await enqueueOne(type, t.slug, t.lang);
			if (err) {
				failed++;
				firstErr ??= err;
			}
			bulkProgress = { done: bulkProgress.done + 1, total: targets.length };
		}
		const filed = bulkProgress.done - failed;
		if (bulkStopping) bulkNote = `Stopped — filed ${filed} of ${targets.length}; the rest were not queued.`;
		bulkProgress = null;
		bulkStopping = false;
		if (failed) {
			// Don't surface the generic 'failed' sentinel — only a real backend detail.
			const detail = firstErr && firstErr !== 'failed' ? ` — ${firstErr}` : '';
			queueError = `Queued ${filed} of ${targets.length}; ${failed} failed${detail}.`;
		}
	}
</script>

<svelte:head><title>Admin · Coverage — Ochorus</title><meta name="robots" content="noindex" /></svelte:head>

<div class="mx-auto max-w-6xl px-5 py-10">
	<header class="mb-6">
		<p class="eyebrow mb-2 text-accent">Admin</p>
		<h1 class="text-display">Coverage matrix</h1>
		<p class="mt-2 text-body text-muted">Every work × language — where each is translated, and where the gaps are.</p>
	</header>

	<AdminGate resource={coverage} errorTitle="Couldn't load coverage">
		{#snippet children(d)}
			<!-- Tabs -->
			<div class="mb-4 flex flex-wrap items-center gap-2">
				{#each TABS as t (t.key)}
					<button
						class="rounded-full border px-4 py-1.5 text-small font-semibold {tab === t.key
							? 'border-accent-soft-border bg-accent-soft text-accent'
							: 'border-border text-muted hover:text-text'}"
						onclick={() => (tab = t.key)}
					>
						{t.label} ({d[t.key]?.length ?? 0})
					</button>
				{/each}
			</div>

			<!-- Planner controls: filter, order and narrow to the review backlog. -->
			<div class="mb-3 flex flex-wrap items-center gap-2">
				<input
					type="text"
					bind:value={q}
					placeholder="Filter by title or author…"
					aria-label="Filter works"
					class="field min-w-48 flex-1 text-small"
				/>
				<select bind:value={sortMode} aria-label="Sort works" class="field text-small">
					<option value="default">Order: as listed</option>
					<option value="priority">Priority: most-read, most gaps</option>
					<option value="least">Least complete first</option>
					<option value="most">Most complete first</option>
				</select>
				<select bind:value={gapLang} aria-label="Show only works missing in a language" class="field text-small">
					<option value="">Gaps in: any language</option>
					{#each langs as l (l.code)}
						<option value={l.code}>Gaps in: {l.name}</option>
					{/each}
				</select>
				<label class="flex items-center gap-1.5 text-small text-muted">
					<input type="checkbox" bind:checked={unreviewedOnly} />
					Only unreviewed AI
				</label>
				{#if tab === 'books' && seriesOptions.length}
					<select bind:value={seriesFilter} aria-label="Narrow to a series" class="field text-small">
						<option value="">All books</option>
						{#each seriesOptions as s (s.slug)}
							<option value={s.slug}>Series: {s.title}</option>
						{/each}
					</select>
				{/if}
				{#if tab === 'books' || tab === 'sermons'}
					<select bind:value={groupBy} aria-label="Group works" class="field text-small">
						<option value="none">Group: none</option>
						<option value="author">Group: author</option>
						{#if tab === 'books'}<option value="series">Group: series</option>{/if}
					</select>
				{/if}
				{#if tabHasStale}
					<label class="flex items-center gap-1.5 text-small text-muted">
						<input type="checkbox" bind:checked={staleOnly} />
						Only out of date
					</label>
				{/if}
				<details
					class="relative ml-auto"
					bind:open={langMenuOpen}
					use:dismissable={{ open: langMenuOpen, onDismiss: () => (langMenuOpen = false) }}
				>
					<summary class="btn btn-sm btn-ghost cursor-pointer list-none">
						Languages{hiddenCount ? ` (${hiddenCount} hidden)` : ''}
					</summary>
					<div
						class="absolute right-0 z-40 mt-1 w-56 rounded-card border border-border bg-surface p-2 text-small shadow-lg"
					>
						{#each allLangs as l (l.code)}
							<label class="flex items-center gap-2 rounded px-2 py-1 hover:bg-surface-2">
								<input
									type="checkbox"
									checked={!hiddenLangs.includes(l.code)}
									onchange={(e) =>
										setHidden(
											(e.currentTarget as HTMLInputElement).checked
												? hiddenLangs.filter((c) => c !== l.code)
												: [...hiddenLangs, l.code]
										)}
								/>
								<span class="text-text">{l.name}</span>
								<span class="ml-auto text-muted">{l.code}</span>
							</label>
						{/each}
						{#if hiddenLangs.length}
							<button type="button" class="btn btn-sm btn-ghost mt-1 w-full" onclick={() => setHidden([])}>
								Show all
							</button>
						{/if}
					</div>
				</details>
				<label class="flex items-center gap-1.5 text-small text-muted">
					<input
						type="checkbox"
						checked={compact}
						onchange={(e) => setCompact((e.currentTarget as HTMLInputElement).checked)}
					/>
					Compact
				</label>
				<button type="button" class="btn btn-sm btn-ghost" onclick={copyLink} title="Copy a link to exactly this view">
					{copied ? 'Copied' : 'Copy link'}
				</button>
				<button type="button" class="btn btn-sm btn-ghost" onclick={downloadCsv} title="Download the works on screen (all filtered rows) as CSV">
					CSV
				</button>
			</div>

			<!-- Legend -->
			{#snippet swatch(k: keyof typeof CELL, text: string, stale = false)}
				<span class="flex items-center gap-1.5"
					><span class="relative inline-flex"
						><span class="{TILE} {CELL[k].cls}">{CELL[k].label}</span>{#if stale}<span
								class={STALE}
								aria-hidden="true">↻</span
							>{/if}</span
					>{text}</span
				>
			{/snippet}
			<div class="mb-3 flex flex-wrap items-center gap-x-4 gap-y-1.5 text-small text-muted">
				{#if tab === 'books'}
					{@render swatch('public_domain', 'public domain')}
				{/if}
				{#if tab !== 'plans'}
					{@render swatch('ai_reviewed', 'reviewed')}
					{@render swatch('ai_unreviewed', tab !== 'articles' ? 'unreviewed — click to review' : 'unreviewed')}
				{/if}
				{#if tab !== 'books'}
					{@render swatch('present', 'present')}
				{/if}
				{@render swatch('missing', 'missing')}
				{#if tabHasStale}
					{@render swatch('ai_unreviewed', 'English changed since translated', true)}
				{/if}
				{#if rows.some((r) => r.blocked)}
					{@render swatch('blocked', 'under copyright — not translatable')}
				{/if}
				<span><span class="text-warning">⌕N</span> unmet searches · 30d</span>
				{#if jobsConfigured !== false}
					{@render swatch('queued', 'queued')}
					{@render swatch('translating', 'translating')}
					{#if canQueue}
						<span class="text-muted">— click a gap, or a row / column “+N”, to queue; ⇧-click gaps to select a range</span>
					{/if}
				{/if}
			</div>

			{#if selectedTargets.length && !pendingBulk}
				<div class="mb-3 flex flex-wrap items-center gap-3 rounded-card border border-accent-soft-border bg-accent-soft px-4 py-2.5 text-small text-accent" role="status">
					<span class="font-semibold">{selectedTargets.length} gap{selectedTargets.length === 1 ? '' : 's'} selected</span>
					<span class="text-muted">{selectedByLang.map(([c, n]) => `${c} ${n}`).join(' · ')}</span>
					<span class="ml-auto flex gap-2">
						<button class="btn btn-sm btn-primary" disabled={busy} onclick={queueSelection}>Queue {selectedTargets.length}</button>
						<button class="btn btn-sm btn-ghost" onclick={clearSelection}>Clear</button>
					</span>
				</div>
			{/if}

			{#if pendingBulk}
				<div class="mb-3 flex flex-wrap items-center gap-3 rounded-card border border-accent-soft-border bg-accent-soft px-4 py-2.5 text-small text-accent" role="alertdialog">
					<span>
						Queue {pendingBulk.targets.length} translation{pendingBulk.targets.length === 1 ? '' : 's'}
						— {pendingBulk.label}? Each files a job a worker processes one at a time.
					</span>
					<span class="ml-auto flex gap-2">
						<button class="btn btn-sm btn-primary" onclick={runBulk}>Queue all</button>
						<button class="btn btn-sm btn-ghost" onclick={() => (pendingBulk = null)}>Cancel</button>
					</span>
				</div>
			{:else if bulkProgress}
				<div class="mb-3 flex items-center gap-3 rounded-card border border-border bg-surface-2 px-4 py-2 text-small text-muted" role="status">
					<span class="shrink-0 tabular-nums">
						{bulkStopping ? 'Stopping…' : 'Queueing…'} {bulkProgress.done}/{bulkProgress.total}
					</span>
					<span class="flex-1">
						<ProgressBar
							percent={(bulkProgress.done / bulkProgress.total) * 100}
							label="Queueing translations"
							size="md"
						/>
					</span>
					<button class="btn btn-sm btn-ghost" disabled={bulkStopping} onclick={() => (bulkStopping = true)}>Stop</button>
				</div>
			{:else if bulkNote}
				<div class="mb-3 rounded-card border border-border bg-surface-2 px-4 py-2 text-small text-muted" role="status">
					{bulkNote}
				</div>
			{/if}

			{#if queueError}
				<div class="mb-3 rounded-card border border-warning/40 bg-warning/5 px-4 py-2 text-small text-warning" role="alert">
					{queueError}
				</div>
			{/if}

			<!-- Bounded scroll box so the header sticks on vertical scroll too: a bare
			     overflow-x container leaves `sticky top-0` nothing to stick within.
			     The Work column was already frozen (sticky left-0). -->
			<div class="max-h-[75vh] overflow-auto rounded-card border border-border bg-surface">
				<table
					class="w-full border-collapse text-body"
					onmouseover={trackCol}
					onfocusin={trackCol}
					onmouseleave={() => (hoverCol = null)}
				>
					<thead>
						<tr class="border-b border-border text-small text-muted">
							<th class="sticky left-0 top-0 z-30 bg-surface px-4 py-3 text-left font-semibold">Work</th>
							{#each langs as l, i (l.code)}
								{@const c = completion[i]}
								<th
									data-lang={l.code}
									class="sticky top-0 z-20 px-3 py-3 text-center font-semibold align-top {hoverCol === l.code
										? 'bg-surface-2'
										: 'bg-surface'}"
									title={l.name}
								>
									<a href="/admin/languages/{l.code}" class="text-muted hover:text-accent">{l.code}</a>
									<span
										class="mt-0.5 block text-micro font-normal tabular-nums {c.pct === 100 ? 'text-accent' : 'text-muted'}"
										title={`${l.name}: ${c.have} of ${c.of} works on screen (${c.pct}%)`}
									>{c.pct}%</span>
									<span class="mx-auto mt-0.5 block h-1 w-8 overflow-hidden rounded-full bg-border" aria-hidden="true">
										<span class="block h-full rounded-full bg-accent" style:width="{c.pct}%"></span>
									</span>
									{#if l.unmet_searches}
										<span
											class="mt-0.5 block text-micro font-normal text-warning"
											title={`${l.unmet_searches} reader search${l.unmet_searches === 1 ? '' : 'es'} found nothing in ${l.name} (30d) — demand to translate toward`}
										>⌕{l.unmet_searches}</span>
									{/if}
									{#if canQueue && jobsConfigured !== false && l.queueable && colGaps[i] > 0}
										<button
											type="button"
											class="mt-0.5 block w-full text-micro font-semibold text-muted transition-colors hover:text-accent disabled:opacity-40 disabled:hover:text-muted"
											disabled={busy}
											title={`Queue all ${colGaps[i]} missing ${l.name} translations`}
											aria-label={`Queue all ${colGaps[i]} missing ${l.name} translations`}
											onclick={() => bulkCol(l)}
										>+{colGaps[i]}</button>
									{/if}
								</th>
							{/each}
						</tr>
					</thead>
					<tbody>
						{#if visibleRows.length === 0}
							<tr>
								<td colspan={langs.length + 1} class="px-4 py-8 text-center text-body text-muted">
									No works match these filters.
								</td>
							</tr>
						{/if}
						{#each groups as g (g.key)}
							{#if g.key}
								{@const open = !collapsed[g.key]}
								<tr class="border-b border-border bg-surface-2">
									<td class="sticky left-0 z-10 bg-surface-2 px-4 {compact ? 'py-1' : 'py-2'}">
										<button
											type="button"
											class="flex w-full items-center gap-2 text-left text-small font-semibold text-text hover:text-accent"
											aria-expanded={open}
											onclick={() => toggleGroup(g.key)}
										>
											<span class="text-muted">{open ? '▾' : '▸'}</span>
											<span class="truncate">{g.label}</span>
											<span class="shrink-0 font-normal text-muted">{g.rows.length}</span>
										</button>
									</td>
									<!-- How much of the group each language has: "0/12" is the gap
									     this view exists to show ("all of Murray is missing in sw"). -->
									{#each langs as l (l.code)}
										{@const have = g.rows.reduce((n, r) => n + (r.cells[l.code] ? 1 : 0), 0)}
										<td
											data-lang={l.code}
											class="px-3 text-center text-micro tabular-nums {compact ? 'py-1' : 'py-2'} {have === 0
												? 'text-warning'
												: have === g.rows.length
													? 'text-accent'
													: 'text-muted'}"
										>{have}/{g.rows.length}</td>
									{/each}
								</tr>
								{#if open}
									{#each g.rows as r (r.slug)}{@render workRow(r)}{/each}
								{/if}
							{:else}
								{#each g.rows as r (r.slug)}{@render workRow(r)}{/each}
							{/if}
						{/each}
					</tbody>
					<tfoot>
						<tr class="border-t border-border text-small text-muted">
							<td class="sticky left-0 z-10 bg-surface px-4 py-2.5 font-semibold">Total ({visibleRows.length}{visibleRows.length !== rows.length ? ` of ${rows.length}` : ''})</td>
							{#each totals as n, i (langs[i].code)}
								<td
									data-lang={langs[i].code}
									class="px-3 py-2.5 text-center tabular-nums font-semibold text-text {colTint(langs[i].code)}"
								>
									{n}<span class="font-normal text-muted">/{completion[i].of}</span>
								</td>
							{/each}
						</tr>
					</tfoot>
				</table>
			</div>
		{/snippet}
	</AdminGate>
</div>

{#snippet workRow(r: AdminCoverageRow)}
	{@const rowGaps = langs.reduce((n, l) => n + (isGap(l, r) ? 1 : 0), 0)}
	<!-- A blank title (an import or edit that lost it) would leave the row reading
	     as just its author while still offering to queue jobs — so name it by
	     slug and say what's wrong; the work's page is where it gets fixed. -->
	{@const title = r.title?.trim() ?? ''}
	{@const name = title || r.slug}
	<tr class="group/row border-b border-border last:border-0 hover:bg-surface-2">
		<!-- Titles wrap to two lines (one in Compact) — articles run long ("A Retrospect by Hudson
		     Taylor: …"); the full title + author ride on the tooltip. -->
		<td
			class="sticky left-0 z-10 w-[22rem] min-w-[16rem] max-w-[22rem] bg-surface px-4 {compact
				? 'py-1'
				: 'py-2.5'}"
		>
			<a
				href={rowHref(r.slug)}
				class="{compact ? 'line-clamp-1 pr-16' : 'line-clamp-2'} font-medium leading-snug text-text hover:text-accent"
				title={r.author ? `${name} — ${r.author}` : name}
			>{#if title}{title}{:else}<span class="font-mono text-small">{r.slug}</span>{/if}</a>
			{#if !title}
				<span
					class="{PILL} border-danger/40 text-danger"
					title="This work has no title — open it to fix the title before queueing translations"
					>⚠ no title</span
				>
			{/if}
			{#if r.blocked}
				<span
					class="{PILL} border-border text-muted"
					title="Under copyright: every edition stays unpublished and no translation may be filed (corrections.COPYRIGHT_BLOCKED_SLUGS)"
					>© under copyright</span
				>
			{/if}
			{#if !compact && (r.author || r.readers)}
				<span class="block truncate text-small text-muted" title={r.author}>
					{r.author ?? ''}{#if r.readers}{r.author ? ' · ' : ''}<span class="tabular-nums">{r.readers}</span> reader{r.readers === 1 ? '' : 's'}{/if}
				</span>
			{/if}
			{#if canQueue && jobsConfigured !== false && rowGaps > 0}
				<button
					type="button"
					class="text-micro font-semibold text-muted opacity-0 transition group-hover/row:opacity-100 hover:text-accent focus:opacity-100 disabled:opacity-40 {compact
						? 'absolute top-1/2 right-3 -translate-y-1/2 bg-surface-2 px-1'
						: 'mt-1'}"
					disabled={busy}
					title={`Queue all ${rowGaps} missing translations of ${name}`}
					aria-label={`Queue all ${rowGaps} missing translations of ${name}`}
					onclick={() => bulkRow(r)}
				>Queue all {rowGaps}</button>
			{/if}
		</td>
		{#each langs as l (l.code)}
			{@const v = r.cells[l.code]}
			{@const job = v ? undefined : jobFor(r.slug, l.code)}
			<td data-lang={l.code} class="group px-3 text-center {compact ? 'py-1' : 'py-2.5'} {colTint(l.code)}">
				{#if v}
					{@const m = cellMeta(v)}
					{@const review = v === 'ai_unreviewed' && !r.blocked ? reviewHref(r.slug, l.code) : null}
					{@const stale = isStale(r, l.code)}
					<!-- The stale mark is the tile's sibling (a button can't nest in the
					     review link), pinned to its corner by this wrapper. -->
					<span class="relative inline-flex align-middle">
						{#if review}
							<a
								href={review}
								class="{TILE} {m.cls} transition-colors hover:bg-warning/20 hover:no-underline"
								title={`Review ${name} → ${l.name}`}
								aria-label={`Review the ${l.name} translation of ${name}`}
							>{m.label}</a>
						{:else}
							<span class="{TILE} {m.cls}">{m.label}</span>
						{/if}
						{#if stale}{@render staleMark(r, l, name)}{/if}
					</span>
				{:else if job}
					{@const m = job.state === 'in_progress' ? CELL.translating : CELL.queued}
					<a
						href={job.url}
						target="_blank"
						rel="noopener"
						class="{TILE} {m.cls} hover:no-underline"
						title={job.state === 'in_progress'
							? `Translating ${name} → ${l.name}… (open issue)`
							: `Queued: ${name} → ${l.name} (open issue)`}
					>{m.label}</a>
				{:else if r.blocked}
					<span
						class="{TILE} {CELL.blocked.cls}"
						title={`${name} is under copyright — no ${l.name} edition may be made`}
						aria-label="Under copyright — not translatable">{CELL.blocked.label}</span
					>
				{:else if jobsConfigured === false || !l.queueable || !canQueue}
					<span
						class="{TILE} {CELL.missing.cls}"
						title={jobsConfigured === false
							? 'Set GITHUB_TRANSLATION_TOKEN on the API to enable the queue'
							: !canQueue
								? `Missing: ${name} → ${l.name}`
								: `${l.name} isn't a translation target — nothing to queue`}
						aria-label="Missing"
					></span>
				{:else}
					{@const spot = queueing === jobKey(r.slug, l.code)}
					{@const picked = !!selected[cellKey(r.slug, l.code)]}
					<button
						type="button"
						aria-pressed={picked}
						class="{TILE} transition-colors hover:border-solid hover:border-accent-soft-border hover:bg-accent-soft hover:text-accent disabled:opacity-50 disabled:hover:bg-transparent {picked
							? 'border border-accent bg-accent-soft text-accent'
							: `${CELL.missing.cls} text-muted`}"
						disabled={busy}
						title={`Queue a ${l.name} translation of ${name}`}
						aria-label={`Queue a ${l.name} translation of ${name}`}
						onclick={(e) =>
							e.shiftKey || e.metaKey || e.ctrlKey ? selectCell(e, r, l) : queue(r.slug, l.code)}
					>
						{#if spot}
							<span>…</span>
						{:else}
							<span class={picked ? 'inline' : 'hidden group-hover:inline'}>{picked ? '✓' : '+'}</span>
						{/if}
					</button>
				{/if}
			</td>
		{/each}
	</tr>
{/snippet}

<!-- The stale mark sits ON the tile's corner, absolutely positioned, so a stale
     cell stays centred in its column instead of being shoved aside by a glyph. -->
{#snippet staleMark(r: AdminCoverageRow, l: AdminCoverageLanguage, name: string)}
	{#if STALE_KIND[tab] && auth.can('review', 'act', l.code)}
		<button
			type="button"
			class="{STALE} hover:bg-accent disabled:opacity-50"
			disabled={markingCurrent !== null}
			title={`The English changed after this ${l.name} translation was made — re-translate it, or click once you've checked it still matches`}
			aria-label={`${l.name} translation of ${name} predates an English change — mark it still current`}
			onclick={() => markCurrent(r, l)}>↻</button
		>
	{:else}
		<span
			class={STALE}
			title={`The English changed after this ${l.name} translation was made — re-translate or re-review`}
			aria-label="English changed since translated">↻</span
		>
	{/if}
{/snippet}
