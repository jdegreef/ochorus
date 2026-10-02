<script lang="ts">
	import { browser } from '$app/environment';
	import { replaceState } from '$app/navigation';
	import { ApiError } from '$lib/api';
	import { adminResource } from '$lib/adminResource.svelte';
	import { auth } from '$lib/auth.svelte';
	import AdminGate from '$lib/components/AdminGate.svelte';
	import ProgressBar from '$lib/components/ProgressBar.svelte';
	import {
		getReviewQueue,
		getReviewDetail,
		decideReview,
		undoReview,
		decideVerse,
		undoVerse,
		type ReviewItem,
		type ReviewDetail,
		type ReviewTarget,
		type ReviewKind,
		type ReviewLane,
		type VerseOutcome
	} from '$lib/library-admin';

	// Filters. Read in exactly one place (the fetcher). They live in the
	// querystring so a reload — or coming back from another admin page — restores
	// the exact view, and a filtered queue is shareable. Seeded from the URL here;
	// written by applyFilters / goPage via syncUrl().
	const initialParams = browser ? new URLSearchParams(location.search) : new URLSearchParams();
	let fKind = $state(initialParams.get('kind') ?? '');
	let fLanguage = $state(initialParams.get('language') ?? '');
	// The lane ('' = all of them). Bookmarks from before lanes still land where
	// they did: `flagged=1` was the verses lane, `outcome=needs_work` its own.
	const initialLane: ReviewLane | '' =
		initialParams.get('flagged') === '1'
			? 'verses'
			: initialParams.get('outcome') === 'needs_work'
				? 'needs_work'
				: ((initialParams.get('lane') ?? '') as ReviewLane | '');
	let fLane = $state(initialLane);
	// Each lane's natural order: in the verses lane that is fewest verses left,
	// so half-finished work gets closed out first.
	const defaultSort = (lane: ReviewLane | '') => (lane === 'verses' ? 'remaining' : 'oldest');
	let fSort = $state(initialParams.get('sort') ?? defaultSort(initialLane));
	let page = $state(Math.max(1, Number(initialParams.get('p')) || 1));
	// One work, from a coverage-matrix cell (`?slug=…&kind=…&language=…`). The
	// first load opens its review panel, so the cell lands on the text itself.
	let fSlug = $state(initialParams.get('slug') ?? '');
	let autoOpen = initialParams.has('slug');

	// Mirror the current filters into the URL without a navigation. Defaults are
	// omitted so the querystring stays as short as what the reviewer actually set.
	function syncUrl() {
		if (!browser) return;
		const p = new URLSearchParams();
		if (fKind) p.set('kind', fKind);
		if (fLanguage) p.set('language', fLanguage);
		if (fLane) p.set('lane', fLane);
		if (fSort !== 'oldest') p.set('sort', fSort);
		if (fSlug) p.set('slug', fSlug);
		if (page > 1) p.set('p', String(page));
		const qs = p.toString();
		replaceState(`${location.pathname}${qs ? `?${qs}` : ''}`, {});
	}

	const key = (kind: string, slug: string, language: string) => `${kind}:${slug}:${language}`;
	const target = (i: ReviewItem): ReviewTarget => ({
		kind: i.kind,
		slug: i.slug,
		language: i.language
	});

	let busy = $state<Record<string, boolean>>({});
	let rowError = $state<Record<string, string>>({});
	// A decided row stays on screen as a confirmation strip for the rest of the
	// session rather than vanishing: undo needs something to grab onto, and the
	// reviewer keeps a visible sense of progress. This replaces the old
	// behaviour of splicing the row out of the list on success.
	let settled = $state<Record<string, { outcome: string; title: string }>>({});
	let selected = $state<Record<string, boolean>>({});

	// Settling one verse. Keyed by reference within the open item, so two
	// panels can never write each other's busy flag.
	let verseBusy = $state<Record<string, boolean>>({});
	let verseError = $state<string | null>(null);

	async function settleVerse(reference: string, outcome: VerseOutcome | null) {
		if (!detail) return;
		// Pin the panel this decision belongs to. `detail` is replaced wholesale
		// when the reviewer changes chapter or opens another item, so re-reading
		// it after the await either throws on null — reporting a failure for a
		// decision that saved — or patches the wrong translation's note.
		const opened = detail;
		const t = { kind: detail.kind, slug: detail.slug, language: detail.language };
		// Whether it was ALREADY settled decides the delta. Re-deciding an
		// approved verse as needs_work is a change of mind, not a second unit of
		// progress, and counting it again reads "13 of 12".
		const wasSettled = !!opened.notes.find((n) => n.reference === reference)?.review;
		verseBusy[reference] = true;
		verseError = null;
		try {
			const review = outcome
				? await decideVerse({ ...t, reference, outcome })
				: (await undoVerse({ ...t, reference }), null);
			// Patch in place rather than refetching: the panel holds a whole
			// chapter of both editions, and re-reading it to change one chip
			// would throw the reviewer's scroll position away mid-pass.
			if (detail === opened) {
				detail = {
					...opened,
					notes: opened.notes.map((n) => (n.reference === reference ? { ...n, review } : n))
				};
			}
			// Keep the row's "n of m settled" honest without a queue refetch.
			// `queue.data` is $state, so its rows are the same proxied objects the
			// list renders — mutating one updates the chip in place.
			const row = queue?.results.find(
				(i) => key(i.kind, i.slug, i.language) === key(t.kind, t.slug, t.language)
			);
			const delta = outcome ? (wasSettled ? 0 : 1) : wasSettled ? -1 : 0;
			if (row) row.notes.settled = Math.max(0, row.notes.settled + delta);
		} catch (e) {
			verseError = e instanceof ApiError ? e.message : 'Could not save that decision.';
		} finally {
			verseBusy[reference] = false;
		}
	}

	// Expanded review panel.
	let openKey = $state<string | null>(null);
	let detail = $state<ReviewDetail | null>(null);
	let detailLoading = $state(false);
	let detailError = $state<string | null>(null);
	let scrolledEnough = $state(false);

	// "Needs work" note composer.
	let notingKey = $state<string | null>(null);
	let noteText = $state('');

	const KIND_LABEL: Record<ReviewKind, string> = {
		book: 'Book',
		sermon: 'Sermon',
		bio: 'Author bio'
	};

	// Only identity is a dependency: every filter and page change already calls
	// `load()` by hand. The effect used to see the filters too, because the
	// fetcher reads them synchronously, so each change ran a second redundant
	// load — see the untrack note in adminResource.
	const reviewQueue = adminResource(
		() =>
			getReviewQueue({
				kind: fKind,
				language: fLanguage,
				lane: fLane,
				sort: fSort,
				slug: fSlug,
				page
			}),
		'Something went wrong loading the queue.',
		undefined,
		(q) => {
			// Deep link: open the one matching item once. Several (another kind or
			// language of the same slug) → leave the choice to the reviewer.
			if (!autoOpen) return;
			autoOpen = false;
			if (q.results.length === 1) void openDetail(q.results[0]);
		}
	);
	const queue = $derived(reviewQueue.data);
	const load = reviewQueue.load;

	// Codes are unambiguous to whoever built this and cryptic to a new reviewer —
	// and `uk` for Ukrainian is two actively misleading letters. The names come
	// from the registry with the queue (see ReviewQueue.language_names), so a
	// language an admin added without a deploy reads as itself here. The code is
	// still the fallback: the queue is null while it loads.
	const languageName = (c: string) => queue?.language_names?.[c] ?? c.toUpperCase();

	function applyFilters() {
		page = 1;
		selected = {};
		syncUrl();
		load();
	}

	// Picking a lane also picks its natural order, unless the reviewer chose a
	// sort of their own. Clicking the lane already in view clears it.
	function setLane(lane: ReviewLane) {
		const wasDefault = fSort === defaultSort(fLane);
		fLane = fLane === lane ? '' : lane;
		if (wasDefault) fSort = defaultSort(fLane);
		applyFilters();
	}

	function setLanguage(code: string) {
		fLanguage = code;
		applyFilters();
	}

	function resetFilters() {
		fLane = '';
		fLanguage = '';
		fKind = '';
		fSort = 'oldest';
		applyFilters();
	}

	function goPage(n: number) {
		page = n;
		selected = {};
		syncUrl();
		load();
		if (typeof window !== 'undefined') window.scrollTo({ top: 0, behavior: 'smooth' });
	}

	async function openDetail(item: ReviewItem, chapter?: number) {
		const k = key(item.kind, item.slug, item.language);
		if (openKey === k && !chapter) {
			openKey = null;
			return;
		}
		openKey = k;
		detail = null;
		detailError = null;
		detailLoading = true;
		scrolledEnough = false;
		try {
			detail = await getReviewDetail({ ...target(item), chapter });
		} catch (e) {
			detailError = e instanceof Error ? e.message : 'Could not load the text.';
		} finally {
			detailLoading = false;
		}
	}

	function onPanelScroll(e: Event) {
		const el = e.currentTarget as HTMLElement;
		if (el.scrollTop + el.clientHeight >= el.scrollHeight - 24) scrolledEnough = true;
	}

	// Whether the signed-in user can APPLY an approval in this language (vs only
	// propose it). A super admin can everywhere; a review:act reviewer proposes a
	// provisional decision an approver later confirms. UX only — the API enforces.
	const canApprove = (language: string) => auth.can('review', 'approve', language);
	// The verb for an item's primary button, given who's acting and its state.
	function approveLabel(i: ReviewItem): string {
		if (!canApprove(i.language)) return 'Submit for approval';
		return i.outcome?.provisional ? 'Confirm' : 'Approve';
	}

	async function decide(items: ReviewItem[], outcome: 'approved' | 'needs_work', note = '') {
		const keys = items.map((i) => key(i.kind, i.slug, i.language));
		keys.forEach((k) => (busy = { ...busy, [k]: true }));
		keys.forEach((k) => (rowError = { ...rowError, [k]: '' }));
		try {
			const res = await decideReview({ items: items.map(target), outcome, note });
			for (const d of res.decided) {
				const k = key(d.kind, d.slug, d.language);
				const item = items.find((i) => key(i.kind, i.slug, i.language) === k);
				// A provisional approval changed nothing live — say so. Reporting it as
				// "Approved" is how a reviewer approved the same translations twice
				// and none of them ever reached readers.
				const shown = d.status === 'provisional' ? 'provisional' : outcome;
				settled = { ...settled, [k]: { outcome: shown, title: item?.title ?? d.slug } };
				selected = { ...selected, [k]: false };
			}
			for (const s of res.skipped) {
				rowError = { ...rowError, [key(s.kind, s.slug, s.language)]: s.reason };
			}
			// A provisional approval stays in the queue awaiting its approver.
			if (queue) queue.total -= res.decided.filter((d) => d.status !== 'provisional').length;
		} catch (e) {
			// A batch where EVERY item was held back is a 400 carrying the same
			// per-item reasons as a 207 — show them, not a generic failure (that
			// is how a founder's approvals failed twice with no reason given).
			// Anything else names its status, so a proxy or throttle refusal is
			// told apart from the API's own answer.
			const body = e instanceof ApiError && e.body && typeof e.body === 'object' ? e.body : null;
			const held = body && 'skipped' in body && Array.isArray(body.skipped) ? body.skipped : null;
			if (held?.length) {
				for (const s of held as (ReviewTarget & { reason: string })[]) {
					rowError = { ...rowError, [key(s.kind, s.slug, s.language)]: s.reason };
				}
			} else {
				const msg =
					body && 'detail' in body
						? String(body.detail)
						: `Could not record that decision${e instanceof ApiError ? ` (HTTP ${e.status})` : ''}.`;
				keys.forEach((k) => (rowError = { ...rowError, [k]: msg }));
			}
		} finally {
			keys.forEach((k) => (busy = { ...busy, [k]: false }));
		}
		notingKey = null;
		noteText = '';
		openKey = null;
	}

	async function undo(item: ReviewItem) {
		const k = key(item.kind, item.slug, item.language);
		busy = { ...busy, [k]: true };
		try {
			await undoReview(target(item));
			const { [k]: _dropped, ...rest } = settled;
			settled = rest;
			if (queue) queue.total += 1;
		} catch (e) {
			rowError = { ...rowError, [k]: e instanceof Error ? e.message : 'Undo failed.' };
		} finally {
			busy = { ...busy, [k]: false };
		}
	}

	// Only rows the server would accept in a batch are selectable. The API
	// re-asserts all of this — the checkbox just shouldn't offer what will be
	// refused. Note `notes_recorded`: an item the pipeline never examined is NOT
	// eligible, because "no flags" must never be able to mean "no data".
	const bulkEligible = (i: ReviewItem) =>
		i.lane === 'ready' &&
		!settled[key(i.kind, i.slug, i.language)] &&
		i.flags?.tags_match !== false;

	const visible = $derived(queue?.results ?? []);
	const selectedItems = $derived(
		visible.filter((i) => selected[key(i.kind, i.slug, i.language)] && bulkEligible(i))
	);

	const readyOnPage = $derived(visible.filter(bulkEligible));

	function selectReady() {
		const every = readyOnPage.every((i) => selected[key(i.kind, i.slug, i.language)]);
		const next = { ...selected };
		for (const i of readyOnPage) next[key(i.kind, i.slug, i.language)] = !every;
		selected = next;
	}

	const LANES: { id: ReviewLane; label: string; hint: string; tone: string }[] = [
		{
			id: 'ready',
			label: 'Ready to read',
			hint: 'Examined, nothing flagged. Can be bulk-approved.',
			tone: 'bg-accent'
		},
		{
			id: 'verses',
			label: 'Verses to check',
			hint: 'Settle each verse the translator rendered.',
			tone: 'bg-warning'
		},
		{
			id: 'unexamined',
			label: 'Not examined',
			hint: 'No scripture notes. Read it in full.',
			tone: 'bg-border-strong'
		},
		{
			id: 'needs_work',
			label: 'Needs work',
			hint: 'Sent back for re-translation.',
			tone: 'bg-danger'
		}
	];

	// Whole days since a date, for "waiting 58 d". Amber from a month: the
	// default sort is oldest first, so this is the number that sort is about.
	const STALE_DAYS = 30;
	function daysSince(iso: string): number | null {
		if (!iso) return null;
		const t = Date.parse(iso);
		return Number.isNaN(t) ? null : Math.max(0, Math.floor((Date.now() - t) / 86_400_000));
	}

	// Languages by queue size, biggest first: the tabs a reviewer picks from.
	const languageTabs = $derived(
		Object.entries(queue?.facets.language ?? {}).sort((a, b) => b[1] - a[1])
	);

	const currentLane = $derived(LANES.find((l) => l.id === fLane));
	// The next lane worth opening when the one in view is empty.
	const nextLane = $derived(
		queue && LANES.find((l) => l.id !== fLane && l.id !== 'needs_work' && queue.lanes[l.id] > 0)
	);

	// Narrowed copies: `queue` is nullable, and the arrow functions in the
	// pagination handlers escape the {#if queue} narrowing.
	const curPage = $derived(queue?.page ?? 1);
	const totalPages = $derived(queue?.pages ?? 1);

	// The machine checks as short verdicts, with the raw numbers on hover. Each
	// says only what the machine found; a pass is still "the machine found
	// nothing", never "the prose is good" (see the intro).
	const checks = (i: ReviewItem): { text: string; ok: boolean; title: string }[] => {
		const f = i.flags;
		if (!f) return [];
		const out: { text: string; ok: boolean; title: string }[] = [];
		if (f.ratio != null) {
			const inBand = f.band ? f.ratio >= f.band[0] && f.ratio <= f.band[1] : null;
			out.push({
				text:
					inBand === false
						? `${f.ratio < f.band![0] ? 'Runs short' : 'Runs long'} ${Math.round(f.ratio)}%`
						: `Length ${Math.round(f.ratio)}%`,
				ok: inBand !== false,
				title: f.band
					? `Length vs. English: ${f.ratio}% (expected ${f.band[0]}–${f.band[1]}%)`
					: `Length vs. English: ${f.ratio}% (no expected range measured for this language)`
			});
		}
		out.push({
			text: `Tags ${f.tag_counts[1]}/${f.tag_counts[0]}`,
			ok: f.tags_match,
			title: f.tags_match
				? 'Every formatting tag, link and footnote in the English is in the translation, in order.'
				: 'The tag sequence differs from the English: something was dropped, added or moved.'
		});
		if (!f.quote_style_consistent)
			out.push({ text: 'Quotes mixed', ok: false, title: 'Curly and straight quotes are mixed.' });
		return out;
	};
</script>

<svelte:head><title>Admin · Review queue — Ochorus</title><meta name="robots" content="noindex" /></svelte:head>

<div class="mx-auto max-w-6xl px-5 py-10">
	<header class="mb-6">
		<p class="eyebrow mb-2 text-accent">Admin</p>
		<div class="flex flex-wrap items-baseline gap-x-4 gap-y-1">
			<h1 class="text-display">Review queue</h1>
			{#if queue}
				{@const oldest = daysSince(queue.oldest_created_at)}
				<p class="text-small text-muted">
					{queue.total.toLocaleString()} awaiting review
					{#if oldest != null}· oldest waiting {oldest} day{oldest === 1 ? '' : 's'}{/if}
				</p>
			{/if}
		</div>
		<p class="text-body mt-2 text-muted">
			AI translations awaiting a native-speaker check. Approving marks the text reviewed in the
			coverage and readiness reports; readers never see this state, so read the text first. The
			checks on each row say only that the machine found nothing, never that the prose is good.
		</p>
	</header>

	<AdminGate resource={reviewQueue} errorTitle="Couldn't load the queue">
		{#snippet children(q)}
			<!-- The lanes: what kind of review each item needs. Counts follow the
			     language and type in view; each card is a filter (again to clear). -->
			<div class="mb-4 grid grid-cols-2 gap-2 md:grid-cols-4" role="group" aria-label="Queue lanes">
				{#each LANES as l (l.id)}
					<button
						type="button"
						class="flex flex-col gap-0.5 rounded-card border bg-surface p-3 text-left transition-colors {fLane ===
						l.id
							? 'border-accent ring-1 ring-accent'
							: 'border-border hover:border-border-strong'}"
						aria-pressed={fLane === l.id}
						onclick={() => setLane(l.id)}
					>
						<span class="text-small flex items-center gap-1.5 font-semibold">
							<span class="inline-block h-2 w-2 rounded-sm {l.tone}" aria-hidden="true"></span>
							{l.label}
						</span>
						<span class="text-h3 tabular-nums">{q.lanes[l.id].toLocaleString()}</span>
						<span class="text-micro text-muted">{l.hint}</span>
					</button>
				{/each}
			</div>

			<div class="mb-3 flex flex-wrap items-center gap-1.5" role="group" aria-label="Language">
				<button
					type="button"
					class="btn btn-sm {fLanguage === '' ? 'btn-primary' : 'btn-ghost'}"
					aria-pressed={fLanguage === ''}
					onclick={() => setLanguage('')}>All languages</button
				>
				{#each languageTabs as [code, n] (code)}
					<button
						type="button"
						class="btn btn-sm {fLanguage === code ? 'btn-primary' : 'btn-ghost'}"
						aria-pressed={fLanguage === code}
						onclick={() => setLanguage(code)}
					>
						{languageName(code)} <span class="tabular-nums opacity-70">{n}</span>
					</button>
				{/each}
			</div>

			<div class="mb-4 flex flex-wrap items-center gap-3">
				<label class="text-small flex items-center gap-2">
					<span class="text-muted">Type</span>
					<select class="field" bind:value={fKind} onchange={applyFilters}>
						<option value="">All types</option>
						{#each Object.entries(q.facets.kind) as [k, n] (k)}
							<option value={k}>{KIND_LABEL[k as ReviewKind]} ({n})</option>
						{/each}
					</select>
				</label>
				<label class="text-small flex items-center gap-2">
					<span class="text-muted">Sort</span>
					<select class="field" bind:value={fSort} onchange={applyFilters}>
						<option value="oldest">Waiting longest</option>
						<option value="remaining">Fewest verses left</option>
						<option value="flagged">Most unverified verses</option>
						<option value="largest">Largest first</option>
					</select>
				</label>
				{#if readyOnPage.length}
					<button class="btn btn-sm btn-ghost" onclick={selectReady}>
						Select {readyOnPage.length} ready on this page
					</button>
				{/if}
				<p class="text-small ml-auto text-muted">
					Showing {q.filtered.toLocaleString()} of {q.total.toLocaleString()}
					{#if fLane || fLanguage || fKind || fSort !== 'oldest'}
						· <button type="button" class="link" onclick={resetFilters}>Reset</button>
					{/if}
				</p>
				{#if fSlug}
					<p class="text-small flex w-full items-center gap-2 border-t border-border pt-3 text-muted">
						Showing one work: <span class="font-semibold text-text">{q.results[0]?.title ?? fSlug}</span>
						<button
							class="btn btn-sm btn-ghost ml-auto"
							onclick={() => {
								fSlug = '';
								resetFilters();
							}}>Show the whole queue</button
						>
					</p>
				{/if}
			</div>

			{#if selectedItems.length}
				<!-- Pinned while scrolling, so the action stays beside the rows being picked. -->
				<div
					class="sticky top-2 z-10 mb-4 flex flex-wrap items-center gap-3 rounded-card border border-accent-soft-border bg-accent-soft p-3 shadow-sm"
				>
					<span class="text-small font-semibold">{selectedItems.length} selected</span>
					<span class="text-small text-muted">Read each one before approving.</span>
					<button
						class="btn btn-sm btn-primary ml-auto"
						onclick={() => decide(selectedItems, 'approved')}
					>
						{selectedItems.every((i) => canApprove(i.language)) ? 'Approve' : 'Submit'}
						{selectedItems.length} selected
					</button>
					<button class="btn btn-sm btn-ghost" onclick={() => (selected = {})}>
						Clear
					</button>
				</div>
			{/if}

			{#if q.total === 0 && q.filtered === 0 && !fLane}
				<div class="rounded-card border border-border bg-surface p-8 text-center">
					<p class="text-h3">All clear</p>
					<p class="text-body mt-1 text-muted">Nothing is awaiting review.</p>
				</div>
			{:else if !visible.length}
				<div class="rounded-card border border-dashed border-border-strong bg-surface p-8 text-center">
					{#if fLane}
						<p class="text-h3">
							{fLanguage ? languageName(fLanguage) : 'The queue'} has nothing in “{currentLane?.label}”
						</p>
						{#if nextLane}
							<p class="text-body mt-1 text-muted">
								{q.lanes[nextLane.id].toLocaleString()} still in “{nextLane.label}”.
							</p>
							<button class="btn btn-sm btn-primary mt-3" onclick={() => setLane(nextLane.id)}>
								Open {nextLane.label.toLowerCase()}
							</button>
						{/if}
					{:else}
						<p class="text-body text-muted">Nothing matches those filters.</p>
					{/if}
				</div>
			{/if}

			<ul class="space-y-1.5">
				{#each visible as i (key(i.kind, i.slug, i.language))}
					{@const k = key(i.kind, i.slug, i.language)}
					<li class="rounded-card border border-border bg-surface">
						{#if settled[k]}
							<div class="flex items-center gap-3 px-4 py-2.5">
								<span
									class="text-small font-semibold {settled[k].outcome === 'provisional' ? 'text-warning' : ''}"
									title={settled[k].outcome === 'provisional'
										? 'Recorded but NOT applied: your role can propose approvals, and an approver must confirm this one before it counts as reviewed.'
										: undefined}
								>
									{settled[k].outcome === 'approved'
										? 'Approved'
										: settled[k].outcome === 'provisional'
											? 'Submitted for approval — not live until an approver confirms'
											: 'Marked needs work'}
								</span>
								<span class="text-small truncate text-muted">{settled[k].title}</span>
								<button
									class="btn btn-sm btn-ghost ml-auto"
									disabled={busy[k]}
									onclick={() => undo(i)}
								>
									{busy[k] ? 'Undoing…' : 'Undo'}
								</button>
							</div>
						{:else}
							{@const waited = daysSince(i.created_at)}
							<div class="flex flex-wrap items-center gap-x-3 gap-y-1.5 px-4 py-2.5">
								<input
									type="checkbox"
									disabled={!bulkEligible(i)}
									checked={!!selected[k]}
									onchange={(e) =>
										(selected = {
											...selected,
											[k]: (e.currentTarget as HTMLInputElement).checked
										})}
									aria-label="Select {i.title} for bulk approval"
									title={bulkEligible(i)
										? undefined
										: 'Not bulk-approvable: flagged verses, not examined, or failing a check. Review it on its own.'}
								/>
								<div class="min-w-0 flex-1 basis-56">
									<div class="flex flex-wrap items-baseline gap-x-2">
										<span class="truncate font-semibold text-text">{i.title}</span>
										<span class="text-micro rounded-sm border border-border px-1.5 text-muted">
											{KIND_LABEL[i.kind]}
										</span>
										{#if !fLanguage}
											<span class="text-micro rounded-sm border border-border px-1.5 text-muted">
												{languageName(i.language)}
											</span>
										{/if}
									</div>
									<div class="text-small truncate text-muted">
										{#if !(i.kind === 'bio' && i.author === i.title)}{i.author} ·{/if}
										{#if i.chapters}{i.chapters} ch{:else if i.words}{i.words.toLocaleString()} words{/if}
										{#if i.scripture_ref}· {i.scripture_ref}{/if}
										{#if i.provenance?.job_issue}· job #{i.provenance.job_issue}{/if}
										{#if i.provenance?.pull_request}· PR #{i.provenance.pull_request}{/if}
									</div>
								</div>

								{#if i.lane === 'verses'}
									{@const pct = Math.round((100 * i.notes.settled) / Math.max(1, i.notes.self_rendered))}
									<span class="text-small inline-flex items-center gap-1.5" title="Verses the translator rendered itself, settled by a reviewer">
										<span class="inline-block w-14">
											<ProgressBar percent={pct} label="{i.title}: flagged verses settled" />
										</span>
										<span class={i.notes.settled >= i.notes.self_rendered ? 'font-semibold' : 'font-semibold text-warning'}>
											{i.notes.settled} of {i.notes.self_rendered}
										</span>
										<span class="text-muted">verses settled</span>
									</span>
								{:else if i.lane === 'unexamined' && fLane !== 'unexamined'}
									<span
										class="text-micro rounded-full border border-border-strong px-2 text-muted"
										title="The pipeline recorded no scripture notes, so nothing was checked. Read it in full."
										>Not examined</span
									>
								{/if}

								{#each checks(i) as c (c.text)}
									<span
										class="text-micro rounded-full border px-2 font-medium {c.ok
											? 'border-border text-muted'
											: 'border-warning/40 text-warning'}"
										title={c.title}>{c.text}</span
									>
								{/each}

								{#if waited != null}
									<span
										class="text-small w-12 text-right tabular-nums {waited >= STALE_DAYS
											? 'font-semibold text-warning'
											: 'text-muted'}"
										title="Waiting since {new Date(i.created_at).toLocaleDateString()}">{waited} d</span
									>
								{/if}

								<button
									class="btn btn-sm btn-ghost shrink-0"
									onclick={() => openDetail(i)}
									aria-expanded={openKey === k}
								>
									{openKey === k ? 'Close' : 'Review'}
								</button>
							</div>

							{#if i.outcome?.outcome === 'needs_work'}
								<p class="text-small px-4 pb-2.5 text-warning">
									Needs work{i.outcome.note ? `: ${i.outcome.note}` : ''}
								</p>
							{/if}
							{#if i.outcome?.outcome === 'approved' && i.outcome?.provisional}
								<p class="text-small px-4 pb-2.5 text-accent">
									{#if canApprove(i.language)}
										Proposed{i.outcome.reviewer ? ` by ${i.outcome.reviewer}` : ''} — awaiting your confirmation.
									{:else}
										Submitted{i.outcome.reviewer ? ` by ${i.outcome.reviewer}` : ''} — awaiting an approver's confirmation.
									{/if}
								</p>
							{/if}
							{#if rowError[k]}<p class="text-small px-4 pb-2.5 text-warning">{rowError[k]}</p>{/if}

									{#if openKey === k}
										<div class="border-t border-border p-4">
											{#if detailLoading}
												<p class="text-body text-muted">Loading the text…</p>
											{:else if detailError}
												<p class="text-body text-warning">{detailError}</p>
											{:else if detail}
												{#if detail.chapters.length}
													<div class="mb-3 flex flex-wrap gap-1">
														{#each detail.chapters as c (c.order)}
															<button
																class="btn btn-sm btn-ghost"
																onclick={() => openDetail(i, c.order)}
															>
																{c.order}
															</button>
														{/each}
													</div>
												{/if}

												{#if !detail.aligned}
													<p class="text-small mb-3 font-semibold text-warning">
														Blocks don't line up — {detail.block_counts[0]} in English, {detail
															.block_counts[1]} in {languageName(detail.language)}. Shown unpaired;
														read them side by side rather than trusting the rows to correspond.
													</p>
												{/if}

												{#if detail.notes.length}
													{@const flagged = detail.notes.filter(
														(n) => n.status === 'self_rendered'
													)}
													<div class="mb-3 rounded-sm border border-border bg-bg p-3">
														<p class="text-small mb-2 font-semibold">
															Verses to check
															{#if flagged.length}
																<span class="font-normal text-muted">
																	— {flagged.filter((n) => n.review).length} of {flagged.length} settled
																</span>
															{/if}
														</p>
														{#if verseError}
															<p class="text-small mb-2 text-warning">{verseError}</p>
														{/if}
														<ul class="space-y-2">
															{#each detail.notes as n (n.reference + n.status)}
																<li class="text-small border-t border-border pt-2 first:border-0 first:pt-0">
																	<div class="flex flex-wrap items-baseline gap-x-2">
																		<span
																			class={n.status === 'self_rendered'
																				? 'font-semibold text-warning'
																				: ''}
																		>
																			{n.reference}
																		</span>
																		{#if n.status === 'mined'}
																			<span class="text-muted"
																				>mined{n.source_file ? ` from ${n.source_file}` : ''}</span
																			>
																		{:else}
																			<span class="text-muted">rendered by the translator</span>
																		{/if}
																		{#if n.chapter}
																			<button
																				type="button"
																				class="link text-small"
																				onclick={() => openDetail(i, n.chapter ?? undefined)}
																			>
																				ch {n.chapter}
																			</button>
																		{/if}
																	</div>

																	{#if n.text}
																		<p class="mt-1 text-muted" dir="auto">{n.text}</p>
																	{:else}
																		<p class="mt-1 text-muted italic">
																			The text has moved since this note was written — open the chapter
																			to find it.
																		</p>
																	{/if}

																	{#if n.status === 'self_rendered'}
																		<div class="mt-1 flex flex-wrap items-center gap-2">
																			{#if n.review}
																				<span
																					class={n.review.outcome === 'approved'
																						? 'font-semibold'
																						: 'font-semibold text-warning'}
																				>
																					{n.review.outcome === 'approved'
																						? 'Rendering is right'
																						: 'Needs work'}
																				</span>
																				{#if n.review.reviewer}
																					<span class="text-muted">— {n.review.reviewer}</span>
																				{/if}
																				<button
																					type="button"
																					class="link"
																					disabled={verseBusy[n.reference]}
																					onclick={() => settleVerse(n.reference, null)}
																				>
																					Undo
																				</button>
																			{:else}
																				<button
																					type="button"
																					class="btn btn-small"
																					disabled={verseBusy[n.reference]}
																					onclick={() => settleVerse(n.reference, 'approved')}
																				>
																					Rendering is right
																				</button>
																				<button
																					type="button"
																					class="btn btn-small"
																					disabled={verseBusy[n.reference]}
																					onclick={() => settleVerse(n.reference, 'needs_work')}
																				>
																					Needs work
																				</button>
																			{/if}
																		</div>
																	{/if}
																</li>
															{/each}
														</ul>
													</div>
												{/if}

												<div
													class="max-h-[28rem] overflow-y-auto rounded-sm border border-border"
													onscroll={onPanelScroll}
												>
													<table class="w-full table-fixed border-collapse">
														<thead class="sticky top-0 bg-surface-2">
															<tr class="text-small text-left text-muted">
																<th class="w-1/2 p-2 font-semibold">English</th>
																<th class="w-1/2 p-2 font-semibold"
																	>{languageName(detail.language)}</th
																>
															</tr>
														</thead>
														<tbody>
															{#each Array(Math.max(detail.source.blocks.length, detail.target.blocks.length)) as _, bi (bi)}
																<tr class="border-t border-border align-top">
																	<td class="text-small p-2">{detail.source.blocks[bi] ?? ''}</td>
																	<td class="text-small p-2" dir="auto"
																		>{detail.target.blocks[bi] ?? ''}</td
																	>
																</tr>
															{/each}
														</tbody>
													</table>
												</div>

												{#if notingKey === k}
													<div class="mt-3">
														<label class="text-small mb-1 block text-muted" for="note-{k}">
															What needs work?
														</label>
														<textarea
															id="note-{k}"
															class="field w-full"
															rows="2"
															bind:value={noteText}
															placeholder="e.g. Ezekiel 36:32 doesn't match the Union wording"
														></textarea>
														<div class="mt-2 flex gap-2">
															<button
																class="btn btn-sm btn-primary"
																onclick={() => decide([i], 'needs_work', noteText)}
															>
																Save
															</button>
															<button
																class="btn btn-sm btn-ghost"
																onclick={() => {
																	notingKey = null;
																	noteText = '';
																}}
															>
																Cancel
															</button>
														</div>
													</div>
												{:else}
													<div class="mt-3 flex flex-wrap items-center gap-2">
														<button
															class="btn btn-sm btn-primary"
															disabled={busy[k] || !scrolledEnough}
															onclick={() => decide([i], 'approved')}
														>
															{busy[k] ? 'Saving…' : approveLabel(i)}
														</button>
														<button
															class="btn btn-sm btn-ghost"
															onclick={() => {
																notingKey = k;
																noteText = '';
															}}
														>
															Needs work
														</button>
														{#if !scrolledEnough}
															<span class="text-small text-muted">
																Scroll to the end of the text to enable approval.
															</span>
														{/if}
													</div>
												{/if}
											{/if}
										</div>
									{/if}
								{/if}
							</li>
						{/each}
					</ul>

			{#if q.pages > 1}
				<nav class="flex items-center gap-3" aria-label="Pagination">
					<button
						class="btn btn-sm btn-ghost"
						disabled={curPage <= 1}
						onclick={() => goPage(curPage - 1)}
					>
						Previous
					</button>
					<span class="text-small text-muted">Page {curPage} of {totalPages}</span>
					<button
						class="btn btn-sm btn-ghost"
						disabled={curPage >= totalPages}
						onclick={() => goPage(curPage + 1)}
					>
						Next
					</button>
				</nav>
			{/if}
		{/snippet}
	</AdminGate>
</div>
