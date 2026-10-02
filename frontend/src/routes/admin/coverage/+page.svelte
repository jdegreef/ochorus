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
	// English is every work's source, not a translation target: the matrix draws
	// it once as a muted "Source" column, and every translation figure — the
	// columns, their totals, the legend, a work's coverage — runs over the rest.
	// (Hidden languages are out of both, so hiding one changes those figures.)
	const SOURCE = 'en';
	const sourceLang = $derived(langs.find((l) => l.code === SOURCE));
	const targetLangs = $derived(langs.filter((l) => l.code !== SOURCE));
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
	// The toolbar's two pop-downs: View (settings you set once) and More (export).
	let viewOpen = $state(false);
	let moreOpen = $state(false);
	let helpOpen = $state(false);
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
	// A blank title (an import or edit that lost it) would leave a row, a prompt
	// or a CSV line naming nothing — so such a work goes by its slug everywhere,
	// and can't be queued until its title is fixed (see isGap).
	const untitled = (r: AdminCoverageRow) => !r.title?.trim();
	const workName = (r: AdminCoverageRow) => r.title?.trim() || r.slug;
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
	// A work's original text, not a translation: a public-domain edition (a
	// book's original — French for Pascal, so not always the English one), or an
	// English sermon/bio/article (their English is the original). Drawn as a
	// muted language tile and never counted as translation progress.
	const isOriginal = (r: AdminCoverageRow, code: string) =>
		r.cells[code] === 'public_domain' || (code === SOURCE && r.cells[code] === 'present');
	const isTranslated = (r: AdminCoverageRow, code: string) => !!r.cells[code] && !isOriginal(r, code);
	// How many target languages a work is translated into — the completeness
	// sort key and the coverage figure on its row.
	const completeness = (r: AdminCoverageRow) =>
		targetLangs.reduce((n, l) => n + (isTranslated(r, l.code) ? 1 : 0), 0);
	// An AI translation awaiting review — the backlog. A copyright-blocked work's
	// editions stay unpublished, so there is nothing of it to review.
	const isUnreviewed = (r: AdminCoverageRow, code: string) =>
		r.cells[code] === 'ai_unreviewed' && !r.blocked;
	const hasUnreviewed = (r: AdminCoverageRow) => langs.some((l) => isUnreviewed(r, l.code));
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
				`Mark the ${l.name} “${workName(r)}” as still matching its English? Do this only after checking the English change doesn't affect the translation.`
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
	const CSV_LABEL: Record<CellState, string> = {
		source: 'original',
		ai_reviewed: 'AI reviewed',
		ai_unreviewed: 'AI unreviewed',
		present: 'present',
		queued: 'queued',
		translating: 'translating',
		blocked: 'blocked (copyright)',
		missing: ''
	};
	function csvCell(r: AdminCoverageRow, l: AdminCoverageLanguage): string {
		const base = r.cells[l.code] === 'public_domain' ? 'PD' : CSV_LABEL[cellState(r, l)];
		return isStale(r, l.code) ? `${base} (out of date)` : base;
	}
	function downloadCsv() {
		const esc = (x: string | number) => {
			const t = String(x);
			return /[",\n]/.test(t) ? `"${t.replaceAll('"', '""')}"` : t;
		};
		const header = ['Work', 'Slug', 'Author', 'Readers', ...langs.map((l) => l.code)];
		const lines = [header, ...visibleRows.map((r) => [
			workName(r),
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
	// One gap's worth: the work's readers × its language's weight × (1 + the
	// readers of THAT language reading it elsewhere for want of it). The last is
	// the one per-cell signal, so a gap three Swahili readers are waiting on
	// outranks the same work's gap in a language nobody has asked for. A row's
	// priority is the sum of its gaps; "Translate next" ranks the gaps themselves.
	const asking = (r: AdminCoverageRow, l: AdminCoverageLanguage) => r.demand?.[l.code] ?? 0;
	const gapScore = (r: AdminCoverageRow, l: AdminCoverageLanguage) =>
		isGap(l, r) ? (1 + (r.readers ?? 0)) * gapWeight(l) * (1 + asking(r, l)) : 0;
	const priority = (r: AdminCoverageRow) =>
		gapLang ? 1 + (r.readers ?? 0) : langs.reduce((n, l) => n + gapScore(r, l), 0);

	const visibleRows = $derived.by(() => {
		let out = rows;
		const term = q.trim().toLowerCase();
		if (term)
			out = out.filter(
				(r) =>
					workName(r).toLowerCase().includes(term) || (r.author ?? '').toLowerCase().includes(term)
			);
		if (unreviewedOnly) out = out.filter(hasUnreviewed);
		// Only a translation column can have gaps — a link carrying ?gaps=en (or a
		// hidden language) mustn't filter invisibly.
		if (gapLang && targetLangs.some((l) => l.code === gapLang))
			out = out.filter((r) => !r.cells[gapLang] && !r.blocked);
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
		targetLangs.map((l) => visibleRows.reduce((n, r) => n + (isTranslated(r, l.code) ? 1 : 0), 0))
	);
	// Completion per language over the visible works that CAN exist there — a
	// copyright-blocked work never will, so it's out of the denominator (and of
	// the numerator: its unpublished editions don't count as progress).
	const reachable = $derived(visibleRows.filter((r) => !r.blocked));
	const completion = $derived(
		targetLangs.map((l) => {
			const have = reachable.reduce((n, r) => n + (isTranslated(r, l.code) ? 1 : 0), 0);
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
	// The summary tiles' colours: the border/fill when its filter is on, the
	// hover border when it's off, and the number's ink when it's non-zero.
	const TONE = {
		accent: { active: 'border-accent-soft-border bg-accent-soft', hover: 'enabled:hover:border-accent-soft-border', ink: '' },
		warning: { active: 'border-warning bg-warning/10', hover: 'enabled:hover:border-warning', ink: 'text-warning' },
		danger: { active: 'border-danger bg-danger/10', hover: 'enabled:hover:border-danger', ink: 'text-danger' },
		none: { active: '', hover: '', ink: '' }
	} as const;
	// A state the API adds before this page knows it shows as itself, neutrally,
	// rather than passing for one of the states above.
	const cellMeta = (v: string) =>
		CELL[v as keyof typeof CELL] ?? { label: '?', cls: 'border border-border text-muted' };
	// One cell's state, for the legend's counts and its highlight lens. The
	// source column has no state here (it isn't a translation).
	type CellState =
		| 'source'
		| 'ai_reviewed'
		| 'ai_unreviewed'
		| 'present'
		| 'queued'
		| 'translating'
		| 'blocked'
		| 'missing';
	function cellState(r: AdminCoverageRow, l: AdminCoverageLanguage): CellState {
		const v = r.cells[l.code];
		if (v) {
			if (isOriginal(r, l.code)) return 'source';
			return v === 'ai_reviewed' || v === 'ai_unreviewed' ? v : 'present';
		}
		const job = jobFor(r.slug, l.code);
		if (job) return job.state === 'in_progress' ? 'translating' : 'queued';
		return r.blocked ? 'blocked' : 'missing';
	}

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
	// The queue is usable here: a super admin, and the API has a token for it.
	const queueOn = $derived(canQueue && jobsConfigured !== false);
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
		!r.blocked && !untitled(r) && l.queueable && !r.cells[l.code] && !jobFor(r.slug, l.code);
	// Missing-and-unqueued count per language column, for the header's "queue all".
	// Over the visible rows, so a filtered view queues only what it shows.
	const colGaps = $derived(
		targetLangs.map((l) => visibleRows.reduce((n, r) => n + (isGap(l, r) ? 1 : 0), 0))
	);

	// --- Today's view: the tab's backlog in four numbers, and its gaps ranked.
	// Both read the whole tab (not the filtered rows) — they answer "what's
	// waiting?". The review and out-of-date tiles count WORKS, the unit of the
	// filter they toggle, so a tile's number is the rows it shows; "Open gaps"
	// counts cells and toggles the Priority order.
	const summary = $derived.by(() => {
		let gaps = 0;
		for (const r of rows) for (const l of langs) if (isGap(l, r)) gaps++;
		const unreviewed = rows.filter(hasUnreviewed).length;
		const stale = rows.filter((r) => r.stale?.length).length;
		const tabJobs = jobs.filter((j) => j.type === jobType && langs.some((l) => l.code === j.language));
		const translating = tabJobs.filter((j) => j.state === 'in_progress').length;
		return { gaps, unreviewed, stale, inFlight: tabJobs.length, translating };
	});
	// "Translate next": every open gap, scored like the Priority sort scores a
	// row — the work's readers × how much that language searches in vain — so
	// the top of the list is the translation most likely to be read. Readers are
	// unbounded and the language weight is only 1–2×, so one popular work would
	// take every slot: each work gets at most NEXT_PER_WORK. Ties keep the
	// tab's own (curated) order. Empty until the job list has loaded — before
	// that a queued gap still looks open.
	const NEXT_COUNT = 10;
	const NEXT_PER_WORK = 2;
	const nextGaps = $derived.by(() => {
		if (jobsConfigured !== true) return [];
		const scored: { r: AdminCoverageRow; l: AdminCoverageLanguage; score: number }[] = [];
		for (const r of rows)
			for (const l of langs) {
				const score = gapScore(r, l);
				if (score) scored.push({ r, l, score });
			}
		scored.sort((a, b) => b.score - a.score);
		const perWork = new Map<string, number>();
		const out: typeof scored = [];
		for (const g of scored) {
			const n = perWork.get(g.r.slug) ?? 0;
			if (n >= NEXT_PER_WORK) continue;
			perWork.set(g.r.slug, n + 1);
			out.push(g);
			if (out.length === NEXT_COUNT) break;
		}
		return out;
	});
	const queueNext = () =>
		stageBulk(
			`the ${nextGaps.length} most-wanted gap${nextGaps.length === 1 ? '' : 's'}`,
			nextGaps.map(({ r, l }) => ({ slug: r.slug, lang: l.code }))
		);

	// --- Legend as a lens: each state's count over the works on screen, and the
	// one picked (if any) — every other cell fades, so the picked ones stand out
	// without hiding a row. "stale" is a flag on top of a state, so it's its own.
	type Lens = CellState | 'stale';
	let lens = $state<Lens | null>(null);
	// Each chip's swatch is its state's tile; "stale" draws an AI tile with the ↻.
	const LENSES: { k: Lens; label: string }[] = [
		{ k: 'source', label: 'Original text' },
		{ k: 'ai_reviewed', label: 'Reviewed' },
		{ k: 'ai_unreviewed', label: 'Unreviewed AI' },
		{ k: 'present', label: 'Present' },
		{ k: 'missing', label: 'Missing' },
		{ k: 'queued', label: 'Queued' },
		{ k: 'translating', label: 'Translating' },
		{ k: 'stale', label: 'English changed' },
		{ k: 'blocked', label: 'Under copyright' }
	];
	const legendCounts = $derived.by(() => {
		const n = Object.fromEntries(LENSES.map((o) => [o.k, 0])) as Record<Lens, number>;
		for (const r of visibleRows)
			for (const l of langs) {
				n[cellState(r, l)]++;
				if (isStale(r, l.code)) n.stale++;
			}
		return n;
	});
	// A picked lens with nothing left to show (a filter) reads as off rather
	// than fading the whole matrix; a tab switch clears it outright (below).
	const activeLens = $derived(lens && legendCounts[lens] ? lens : null);
	const lensHit = (r: AdminCoverageRow, l: AdminCoverageLanguage) =>
		activeLens === 'stale' ? isStale(r, l.code) : cellState(r, l) === activeLens;

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

	// Stage a bulk enqueue for confirmation — a row (a work into all its missing
	// languages), a column (all missing works into a language), a selection or
	// the "Translate next" list. No-op when there's nothing to queue.
	function stageBulk(label: string, targets: { slug: string; lang: string }[]) {
		if (targets.length) pendingBulk = { label, type: jobType, targets };
	}
	const bulkRow = (r: AdminCoverageRow) =>
		stageBulk(
			`“${workName(r)}” into every missing language`,
			langs.filter((l) => isGap(l, r)).map((l) => ({ slug: r.slug, lang: l.code }))
		);
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
		lens = null;
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
		stageBulk(
			`the ${selectedTargets.length} selected gap${selectedTargets.length === 1 ? '' : 's'}`,
			selectedTargets
		);
		clearSelection();
	}
	const bulkCol = (l: AdminCoverageLanguage) =>
		stageBulk(
			`every missing work into ${l.name}`,
			visibleRows.filter((r) => isGap(l, r)).map((r) => ({ slug: r.slug, lang: l.code }))
		);

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
		if (bulkStopping && bulkProgress.done < targets.length) bulkNote = `Stopped — filed ${filed} of ${targets.length}; the rest were not queued.`;
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

			<!-- What's waiting, before the detail. "Open gaps" toggles the Priority
			     order; the review and out-of-date tiles toggle their filters. -->
			{@const reviewKind = REVIEW_KIND[tab]}
			{#snippet tile(
				label: string,
				value: number,
				hint: string,
				tone: 'accent' | 'warning' | 'danger' | 'none',
				active = false,
				onclick?: () => void,
				title = ''
			)}
				{@const t = TONE[tone]}
				{@const box = 'flex flex-col items-start gap-1 rounded-card border bg-surface px-4 py-3 text-left transition-colors'}
				{#snippet body()}
					<span class="text-small text-muted">{label}</span>
					<span class="stat-number-sm {value ? t.ink : ''}">{value}</span>
					<span class="text-micro text-muted">{hint}</span>
				{/snippet}
				{#if onclick}
					<button
						type="button"
						class="{box} disabled:cursor-default {active ? t.active : `border-border ${t.hover}`}"
						{onclick}
						aria-pressed={active}
						disabled={!value && !active}
						{title}>{@render body()}</button
					>
				{:else}
					<div class="{box} border-border" {title}>{@render body()}</div>
				{/if}
			{/snippet}
			<div class="mb-4 grid grid-cols-2 gap-2 sm:grid-cols-4">
				{@render tile(
					'Open gaps',
					summary.gaps,
					sortMode === 'priority' ? 'Ordered by priority' : 'Order by priority',
					'accent',
					sortMode === 'priority',
					() => (sortMode = sortMode === 'priority' ? 'default' : 'priority'),
					'Order the works by readers × open gaps'
				)}
				{@render tile(
					'Works awaiting review',
					summary.unreviewed,
					unreviewedOnly ? 'Showing only these' : 'Show only these',
					'warning',
					unreviewedOnly,
					() => (unreviewedOnly = !unreviewedOnly),
					'Show only works with an AI translation awaiting review'
				)}
				{@render tile(
					'Works out of date',
					summary.stale,
					staleOnly ? 'Showing only these' : 'Show only these',
					'danger',
					staleOnly,
					() => (staleOnly = !staleOnly),
					'Show only works whose English changed after they were translated'
				)}
				{@render tile(
					'In flight',
					summary.inFlight,
					`${summary.inFlight - summary.translating} queued · ${summary.translating} translating`,
					'none'
				)}
			</div>
			{#if reviewKind && summary.unreviewed}
				<p class="-mt-2 mb-4 text-small">
					<a href="/admin/review?{new URLSearchParams({ kind: reviewKind })}">Open the review queue →</a>
				</p>
			{/if}

			{#if queueOn && nextGaps.length}
				<section class="mb-4 rounded-card border border-border bg-surface" aria-labelledby="translate-next">
					<div class="flex flex-wrap items-center gap-x-3 gap-y-1 px-4 py-2.5">
						<h2 id="translate-next" class="font-sans text-body font-semibold">Translate next</h2>
						<span class="text-small text-muted">open gaps ranked by readers × searches with no result</span>
						<button type="button" class="btn btn-sm btn-primary ml-auto" disabled={busy} onclick={queueNext}
							>Queue top {nextGaps.length}</button
						>
					</div>
					<ol class="border-t border-border text-small">
						{#each nextGaps as { r, l } (`${r.slug}:${l.code}`)}
							<li class="flex items-center gap-3 border-b border-border px-4 py-1.5 last:border-0">
								<span class="min-w-0 flex-1 truncate">
									<a href={rowHref(r.slug)} class="text-text hover:text-accent">{workName(r)}</a>
									<span class="text-muted">→</span>
									<span class="font-semibold">{l.name}</span>
								</span>
								{#if r.readers}<span class="shrink-0 tabular-nums text-muted">{r.readers} reader{r.readers === 1 ? '' : 's'}</span>{/if}
								{#if l.unmet_searches}<span class="shrink-0 tabular-nums text-warning" title={`${l.unmet_searches} ${l.name} search${l.unmet_searches === 1 ? '' : 'es'} found nothing (30d)`}>⌕{l.unmet_searches}</span>{/if}
								<button
									type="button"
									class="shrink-0 font-semibold text-accent hover:underline disabled:opacity-40 disabled:no-underline"
									disabled={busy}
									onclick={() => queue(r.slug, l.code)}
								>{queueing === jobKey(r.slug, l.code) ? '…' : 'Queue'}</button>
							</li>
						{/each}
					</ol>
				</section>
			{/if}

			<!-- Planner controls: search and "Gaps in" on the surface; the settings you
			     set once live under View, export under More. The review and out-of-date
			     filters are the tiles above. -->
			<div class="mb-3 flex flex-wrap items-center gap-2">
				<input
					type="text"
					bind:value={q}
					placeholder="Filter by title or author…"
					aria-label="Filter works"
					class="field min-w-48 flex-1 text-small"
				/>
				<select bind:value={gapLang} aria-label="Show only works missing in a language" class="field text-small">
					<option value="">Gaps in: any language</option>
					{#each targetLangs as l (l.code)}
						<option value={l.code}>Gaps in: {l.name}</option>
					{/each}
				</select>
				<details
					class="relative"
					bind:open={viewOpen}
					use:dismissable={{ open: viewOpen, onDismiss: () => (viewOpen = false) }}
				>
					<summary class="btn btn-sm cursor-pointer list-none">
						View{hiddenCount ? ` · ${hiddenCount} hidden` : ''} ▾
					</summary>
					<div
						class="absolute right-0 z-40 mt-1 grid w-72 gap-3 rounded-card border border-border bg-surface p-3 text-small shadow-lg"
					>
						<label class="grid gap-1">
							<span class="text-micro text-muted">Order</span>
							<select bind:value={sortMode} class="field text-small">
								<option value="default">As listed</option>
								<option value="priority">Priority: most-read, most gaps</option>
								<option value="least">Least complete first</option>
								<option value="most">Most complete first</option>
							</select>
						</label>
						{#if tab === 'books' || tab === 'sermons'}
							<label class="grid gap-1">
								<span class="text-micro text-muted">Group</span>
								<select bind:value={groupBy} class="field text-small">
									<option value="none">None</option>
									<option value="author">By author</option>
									{#if tab === 'books'}<option value="series">By series</option>{/if}
								</select>
							</label>
						{/if}
						{#if tab === 'books' && seriesOptions.length}
							<label class="grid gap-1">
								<span class="text-micro text-muted">Series</span>
								<select bind:value={seriesFilter} class="field text-small">
									<option value="">All books</option>
									{#each seriesOptions as s (s.slug)}
										<option value={s.slug}>{s.title}</option>
									{/each}
								</select>
							</label>
						{/if}
						<fieldset class="grid gap-0.5">
							<legend class="mb-1 text-micro text-muted">Languages shown</legend>
							{#each allLangs as l (l.code)}
								<label class="flex items-center gap-2 rounded px-1 py-0.5 hover:bg-surface-2">
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
						</fieldset>
						<label class="flex items-center gap-2 border-t border-border pt-2">
							<input
								type="checkbox"
								checked={compact}
								onchange={(e) => setCompact((e.currentTarget as HTMLInputElement).checked)}
							/>
							Compact rows
						</label>
					</div>
				</details>
				<details
					class="relative"
					bind:open={moreOpen}
					use:dismissable={{ open: moreOpen, onDismiss: () => (moreOpen = false) }}
				>
					<summary class="btn btn-sm btn-ghost cursor-pointer list-none" aria-label="More: copy link, download CSV">⋯</summary>
					<div
						class="absolute right-0 z-40 mt-1 grid w-56 gap-1 rounded-card border border-border bg-surface p-2 text-small shadow-lg"
					>
						<button type="button" class="btn btn-sm btn-ghost justify-start" onclick={copyLink}>
							{copied ? 'Copied' : 'Copy link to this view'}
						</button>
						<button type="button" class="btn btn-sm btn-ghost justify-start" onclick={downloadCsv}>
							Download CSV
						</button>
					</div>
				</details>
			</div>

			<!-- Legend as a lens: each state is a chip with its count over the works on
			     screen; picking one fades every other cell (rows stay put). -->
			<div class="mb-3 flex flex-wrap items-center gap-1.5 text-small">
				{#each LENSES as o (o.k)}
					{#if legendCounts[o.k]}
						{@const cell =
							o.k === 'source'
								? { label: SOURCE.toUpperCase(), cls: CELL.public_domain.cls }
								: CELL[o.k === 'stale' ? 'ai_unreviewed' : o.k]}
						<button
							type="button"
							class="chip inline-flex items-center gap-1.5 !py-0.5 !ps-1"
							class:active={activeLens === o.k}
							aria-pressed={activeLens === o.k}
							onclick={() => (lens = activeLens === o.k ? null : o.k)}
						>
							<span class="relative inline-flex"
								><span class="{TILE} {cell.cls}">{cell.label}</span>{#if o.k === 'stale'}<span
										class={STALE}
										aria-hidden="true">↻</span
									>{/if}</span
							>
							{o.label}
							<span class="count">{legendCounts[o.k]}</span>
						</button>
					{/if}
				{/each}
				{#if visibleRows.some((r) => r.demand)}
					<span
						class="inline-flex items-center gap-1.5 text-muted"
						title="A missing translation that readers of that language are reading in another language, for want of it. The number is how many readers; it also raises the gap in the priority order."
						><span class="{TILE} border border-accent-soft-border bg-accent-soft font-semibold text-accent">3</span>readers asking</span
					>
				{/if}
				<details
					class="relative"
					bind:open={helpOpen}
					use:dismissable={{ open: helpOpen, onDismiss: () => (helpOpen = false) }}
				>
					<summary class="cursor-pointer list-none rounded-full border border-border px-2 py-0.5 text-muted hover:text-text" aria-label="How to use the matrix">?</summary>
					<div class="absolute left-0 z-40 mt-1 grid w-80 gap-1.5 rounded-card border border-border bg-surface p-3 text-small text-muted shadow-lg">
						<p>Click a chip to highlight those cells; click it again to clear.</p>
						{#if tab !== 'articles' && tab !== 'plans'}<p>Click a gold <strong>AI</strong> cell to review that translation.</p>{/if}
						{#if queueOn}
							<p>Click an empty cell to queue one translation, or a column's or row's “+N” to queue them all.</p>
							<p>⇧-click two empty cells to select every gap between them; ⌘/Ctrl-click toggles one.</p>
						{/if}
						<p>A red ↻ means the English changed after the translation was made.</p>
					</div>
				</details>
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
					<div class="flex-1">
						<ProgressBar
							percent={(bulkProgress.done / bulkProgress.total) * 100}
							label="Queueing translations"
							size="md"
						/>
					</div>
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
							<!-- The Work header labels the stacked figures once; every language
							     column keeps each figure on the same line (a dash when there's
							     none), so they compare across. -->
							<th class="sticky left-0 top-0 z-30 bg-surface px-4 py-3 text-left align-top font-semibold">
								<!-- Built line for line like a language header (code, name,
								     %, bar, ⌕, +N), so each label sits level with its figure. -->
								<span class="flex justify-between gap-3">
									<span>Work</span>
									<span class="text-right text-micro font-normal text-muted">
										<span class="block text-small">&nbsp;</span>
										<span class="block">&nbsp;</span>
										<span class="mt-0.5 block">translated</span>
										<span class="mt-0.5 block h-1" aria-hidden="true"></span>
										<span class="mt-0.5 block">searches with no result · 30d</span>
										{#if queueOn}<span class="mt-1 block border border-transparent">queue the gaps</span>{/if}
									</span>
								</span>
							</th>
							{#if sourceLang}
								<th
									class="sticky top-0 z-20 border-r-2 border-border bg-surface px-3 py-3 text-center align-bottom text-micro font-normal text-muted"
									title="English: the original for most works (a gold AI tile means this English is a translation — Pascal's books are French originals)"
								>English<br />source</th>
							{/if}
							{#each targetLangs as l, i (l.code)}
								{@const c = completion[i]}
									<th
										data-lang={l.code}
										class="sticky top-0 z-20 px-3 py-3 text-center align-top font-semibold {hoverCol === l.code
											? 'bg-surface-2'
											: 'bg-surface'}"
									>
										<a href="/admin/languages/{l.code}" class="text-text hover:text-accent">{l.code}</a>
										<span class="block text-micro font-normal text-muted">{l.name}</span>
										<span
											class="mt-0.5 block text-micro font-normal tabular-nums {c.pct === 100 ? 'text-accent' : 'text-text'}"
											title={`${l.name}: ${c.have} of ${c.of} works on screen (${c.pct}%)`}
										>{c.pct}%</span>
										<span class="mx-auto mt-0.5 block h-1 w-8 overflow-hidden rounded-full bg-border" aria-hidden="true">
											<span class="block h-full rounded-full bg-accent" style:width="{c.pct}%"></span>
										</span>
										<span
											class="mt-0.5 block text-micro font-normal tabular-nums {l.unmet_searches ? 'text-warning' : 'text-muted'}"
											title={l.unmet_searches
												? `${l.unmet_searches} reader search${l.unmet_searches === 1 ? '' : 'es'} found nothing in ${l.name} (30d) — demand to translate toward`
												: `No ${l.name} searches came up empty (30d)`}
										>{l.unmet_searches ? `⌕ ${l.unmet_searches}` : '—'}</span>
										{#if queueOn}
											{#if l.queueable && colGaps[i] > 0}
												<button
													type="button"
													class="mt-1 rounded-md border border-border bg-surface px-1.5 text-micro font-semibold tabular-nums text-text transition-colors hover:border-accent-soft-border hover:text-accent disabled:opacity-40"
													disabled={busy}
													title={`Queue all ${colGaps[i]} missing ${l.name} translations`}
													aria-label={`Queue all ${colGaps[i]} missing ${l.name} translations`}
													onclick={() => bulkCol(l)}
												>+{colGaps[i]}</button>
											{:else}
												<span class="mt-1 block text-micro font-normal text-muted">—</span>
											{/if}
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
									{#if sourceLang}<td class="border-r-2 border-border"></td>{/if}
									{#each targetLangs as l (l.code)}
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
							{#if sourceLang}
								<td class="border-r-2 border-border px-3 py-2.5 text-center tabular-nums text-muted">
									{visibleRows.filter((r) => r.cells[SOURCE]).length}
								</td>
							{/if}
							{#each totals as n, i (targetLangs[i].code)}
								<td
									data-lang={targetLangs[i].code}
									class="px-3 py-2.5 text-center tabular-nums font-semibold text-text {colTint(targetLangs[i].code)}"
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
	{@const name = workName(r)}
	<tr class="group/row border-b border-border last:border-0 hover:bg-surface-2">
		<!-- Titles wrap to two lines (one in Compact) — articles run long ("A Retrospect by Hudson
		     Taylor: …"); the full title + author ride on the tooltip. -->
		<td
			class="sticky left-0 z-10 w-[22rem] min-w-[16rem] max-w-[22rem] bg-surface ps-4 {r.blocked ? 'pe-4' : 'pe-24'} {compact
				? 'py-1'
				: 'py-2.5'}"
		>
			<a
				href={rowHref(r.slug)}
				class="{compact ? 'line-clamp-1' : 'line-clamp-2'} font-medium leading-snug text-text hover:text-accent"
				title={r.author ? `${name} — ${r.author}` : name}
			>{#if untitled(r)}<span class="font-mono text-small">{r.slug}</span>{:else}{name}{/if}</a>
			{#if !r.blocked}
				{@const have = completeness(r)}
				<!-- The row's own coverage, on the right edge. In Compact the hover
				     "Queue all" takes this spot (the action on the same number), so the
				     meter steps aside while the row is hovered. -->
				<span
					class="absolute top-1/2 right-3 flex -translate-y-1/2 items-center gap-1.5 text-micro tabular-nums text-muted transition-opacity {compact &&
					queueOn &&
					rowGaps > 0
						? 'group-hover/row:opacity-0'
						: ''}"
					title={`${name}: in ${have} of ${targetLangs.length} languages`}
				>
					<span class="block w-8">
						<ProgressBar
							percent={targetLangs.length ? (have / targetLangs.length) * 100 : 0}
							label={`${name}: translated into ${have} of ${targetLangs.length} languages`}
						/>
					</span>
					{have}/{targetLangs.length}
				</span>
			{/if}
			{#if untitled(r)}
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
			{#if queueOn && rowGaps > 0}
				<button
					type="button"
					class="pointer-events-none text-micro font-semibold text-muted opacity-0 transition group-hover/row:pointer-events-auto group-hover/row:opacity-100 hover:text-accent focus:pointer-events-auto focus:opacity-100 disabled:opacity-40 {compact
						? 'absolute top-1/2 right-3 -translate-y-1/2 bg-surface-2 px-1'
						: 'mt-1'}"
					disabled={busy}
					title={`Queue all ${rowGaps} missing translations of ${name}`}
					aria-label={`Queue all ${rowGaps} missing translations of ${name}`}
					onclick={() => bulkRow(r)}
				>Queue all {rowGaps}</button>
			{/if}
		</td>
		{#if sourceLang}{@render cell(r, sourceLang, name, true)}{/if}
		{#each targetLangs as l (l.code)}{@render cell(r, l, name)}{/each}
	</tr>
{/snippet}

<!-- One matrix cell, drawn from cellState — the same classifier the legend,
     its lens and the CSV read, so the tiles and the counts can't disagree. -->
{#snippet cell(r: AdminCoverageRow, l: AdminCoverageLanguage, name: string, isSource = false)}
	{@const st = cellState(r, l)}
	<td
		data-lang={l.code}
		class="group px-3 text-center transition-opacity {compact ? 'py-1' : 'py-2.5'} {colTint(l.code)} {isSource
			? 'border-r-2 border-border'
			: ''} {activeLens && !lensHit(r, l) ? 'opacity-20' : ''}"
	>
		{#if st === 'source'}
			<span class="{TILE} {CELL.public_domain.cls}" title={`${name}: the original ${l.name} text`}
				>{l.code.toUpperCase()}</span
			>
		{:else if st === 'ai_reviewed' || st === 'ai_unreviewed' || st === 'present'}
			{@const m = cellMeta(r.cells[l.code]!)}
			{@const review = isUnreviewed(r, l.code) ? reviewHref(r.slug, l.code) : null}
			<!-- The stale mark is the tile's sibling (a button can't nest in the review
			     link), pinned to its corner by this wrapper. -->
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
				{#if isStale(r, l.code)}{@render staleMark(r, l, name)}{/if}
			</span>
		{:else if st === 'queued' || st === 'translating'}
			{@const job = jobFor(r.slug, l.code)!}
			<a
				href={job.url}
				target="_blank"
				rel="noopener"
				class="{TILE} {CELL[st].cls} hover:no-underline"
				title={st === 'translating'
					? `Translating ${name} → ${l.name}… (open issue)`
					: `Queued: ${name} → ${l.name} (open issue)`}
			>{CELL[st].label}</a>
		{:else if st === 'blocked'}
			<span
				class="{TILE} {CELL.blocked.cls}"
				title={`${name} is under copyright — no ${l.name} edition may be made`}
				aria-label="Under copyright — not translatable">{CELL.blocked.label}</span
			>
		{:else if !isGap(l, r) || !queueOn}
			<!-- Demand shows here too: someone who can read the matrix but not
			     queue should still see where readers are waiting. -->
			{@const wanting = asking(r, l)}
			<span
				class="{TILE} {wanting
					? 'border border-accent-soft-border bg-accent-soft font-semibold tabular-nums text-accent'
					: CELL.missing.cls}"
				title={(jobsConfigured === false
					? 'Set GITHUB_TRANSLATION_TOKEN on the API to enable the queue'
					: untitled(r)
						? `Fix the title of ${name} before queueing translations`
						: !canQueue
							? `Missing: ${name} → ${l.name}`
							: `${l.name} isn't a translation target — nothing to queue`) +
					(wanting
						? ` · ${wanting} ${l.name} reader${wanting === 1 ? ' is' : 's are'} reading it in another language`
						: '')}
				aria-label={wanting ? `Missing, ${wanting} readers asking` : 'Missing'}
				>{wanting || ''}</span
			>
		{:else}
			{@const spot = queueing === jobKey(r.slug, l.code)}
			{@const picked = !!selected[cellKey(r.slug, l.code)]}
			{@const wanting = asking(r, l)}
			{@const why = wanting
				? ` · ${wanting} ${l.name} reader${wanting === 1 ? ' is' : 's are'} reading it in another language`
				: ''}
			<button
				type="button"
				aria-pressed={picked}
				class="{TILE} transition-colors hover:border-solid hover:border-accent-soft-border hover:bg-accent-soft hover:text-accent disabled:opacity-50 disabled:hover:bg-transparent {picked
					? 'border border-accent bg-accent-soft text-accent'
					: wanting
						? 'border border-accent-soft-border bg-accent-soft font-semibold text-accent'
						: `${CELL.missing.cls} text-muted`}"
				disabled={busy}
				title={`Queue a ${l.name} translation of ${name}${why}`}
				aria-label={`Queue a ${l.name} translation of ${name}${why}`}
				onclick={(e) =>
					e.shiftKey || e.metaKey || e.ctrlKey ? selectCell(e, r, l) : queue(r.slug, l.code)}
			>
				{#if spot}
					<span>…</span>
				{:else if wanting && !picked}
					<span class="tabular-nums">{wanting}</span>
				{:else}
					<span class={picked ? 'inline' : 'hidden group-hover:inline'}>{picked ? '✓' : '+'}</span>
				{/if}
			</button>
		{/if}
	</td>
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
