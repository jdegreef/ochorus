<script lang="ts">
	import { auth } from '$lib/auth.svelte';
	import { ApiError } from '$lib/api';
	import {
		getReviewQueue,
		getReviewDetail,
		decideReview,
		undoReview,
		type ReviewQueue,
		type ReviewItem,
		type ReviewDetail,
		type ReviewTarget,
		type ReviewKind
	} from '$lib/library';

	let queue = $state<ReviewQueue | null>(null);
	let loading = $state(true);
	let denied = $state(false);
	let error = $state<string | null>(null);
	let seq = 0;

	// Filters. Read in exactly one place (`load`), so moving them into the
	// querystring later is a local change.
	let fKind = $state('');
	let fLanguage = $state('');
	let fFlagged = $state(false);
	let fOutcome = $state('');
	let fSort = $state('oldest');
	let page = $state(1);

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

	// Expanded review panel.
	let openKey = $state<string | null>(null);
	let detail = $state<ReviewDetail | null>(null);
	let detailLoading = $state(false);
	let detailError = $state<string | null>(null);
	let scrolledEnough = $state(false);

	// "Needs work" note composer.
	let notingKey = $state<string | null>(null);
	let noteText = $state('');

	const LANGUAGE_NAMES: Record<string, string> = {
		en: 'English',
		es: 'Spanish',
		pt: 'Portuguese',
		sw: 'Swahili',
		lg: 'Luganda',
		ar: 'Arabic',
		uk: 'Ukrainian',
		hi: 'Hindi'
	};
	// Codes are unambiguous to whoever built this and cryptic to a new reviewer —
	// and `uk` for Ukrainian is two actively misleading letters.
	const languageName = (c: string) => LANGUAGE_NAMES[c] ?? c.toUpperCase();
	const KIND_LABEL: Record<ReviewKind, string> = {
		book: 'Book',
		sermon: 'Sermon',
		bio: 'Author bio'
	};

	async function load() {
		const id = ++seq;
		loading = true;
		denied = false;
		error = null;
		try {
			const result = await getReviewQueue({
				kind: fKind,
				language: fLanguage,
				flagged: fFlagged,
				outcome: fOutcome,
				sort: fSort,
				page
			});
			if (id !== seq) return;
			queue = result;
		} catch (e) {
			if (id !== seq) return;
			if (e instanceof ApiError && (e.status === 401 || e.status === 403)) denied = true;
			else error = e instanceof Error ? e.message : 'Something went wrong loading the queue.';
		} finally {
			if (id === seq) loading = false;
		}
	}

	$effect(() => {
		if (auth.enabled && !auth.initialized) return;
		void auth.user?.email;
		load();
	});

	function applyFilters() {
		page = 1;
		selected = {};
		load();
	}

	function goPage(n: number) {
		page = n;
		selected = {};
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

	async function decide(items: ReviewItem[], outcome: 'approved' | 'needs_work', note = '') {
		const keys = items.map((i) => key(i.kind, i.slug, i.language));
		keys.forEach((k) => (busy = { ...busy, [k]: true }));
		keys.forEach((k) => (rowError = { ...rowError, [k]: '' }));
		try {
			const res = await decideReview({ items: items.map(target), outcome, note });
			for (const d of res.decided) {
				const k = key(d.kind, d.slug, d.language);
				const item = items.find((i) => key(i.kind, i.slug, i.language) === k);
				settled = { ...settled, [k]: { outcome, title: item?.title ?? d.slug } };
				selected = { ...selected, [k]: false };
			}
			for (const s of res.skipped) {
				rowError = { ...rowError, [key(s.kind, s.slug, s.language)]: s.reason };
			}
			if (queue) queue.total -= res.decided.length;
		} catch (e) {
			const msg =
				e instanceof ApiError && e.body && typeof e.body === 'object' && 'detail' in e.body
					? String((e.body as { detail: unknown }).detail)
					: 'Could not record that decision.';
			keys.forEach((k) => (rowError = { ...rowError, [k]: msg }));
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

	// Only rows the server would accept in a batch are selectable: nothing
	// flagged, nothing failing a mechanical check. The API re-asserts this — the
	// checkbox just shouldn't offer what will be refused.
	const bulkEligible = (i: ReviewItem) =>
		!i.flagged && !settled[key(i.kind, i.slug, i.language)] && i.flags?.tags_match !== false;

	const visible = $derived(queue?.results ?? []);
	const selectedItems = $derived(
		visible.filter((i) => selected[key(i.kind, i.slug, i.language)] && bulkEligible(i))
	);
	const excludedCount = $derived(visible.filter((i) => !bulkEligible(i)).length);

	// Group by language: review is staffed by language, so that is the axis a
	// reviewer navigates by. Type stays a chip on the row — one level of nesting.
	const groups = $derived(
		Object.entries(
			visible.reduce<Record<string, ReviewItem[]>>((acc, i) => {
				(acc[i.language] ??= []).push(i);
				return acc;
			}, {})
		)
	);

	function toggleGroup(lang: string) {
		const all = visible.filter((i) => i.language === lang && bulkEligible(i));
		const every = all.every((i) => selected[key(i.kind, i.slug, i.language)]);
		const next = { ...selected };
		for (const i of all) next[key(i.kind, i.slug, i.language)] = !every;
		selected = next;
	}

	// Narrowed copies: `queue` is nullable, and the arrow functions in the
	// pagination handlers escape the {#if queue} narrowing.
	const curPage = $derived(queue?.page ?? 1);
	const totalPages = $derived(queue?.pages ?? 1);

	const ratioLabel = (i: ReviewItem) => {
		const f = i.flags;
		if (!f || f.ratio == null) return null;
		return f.band ? `ratio ${f.ratio}% (band ${f.band[0]}–${f.band[1]})` : `ratio ${f.ratio}%`;
	};
</script>

<svelte:head><title>Admin · Review queue — Ochorus</title><meta name="robots" content="noindex" /></svelte:head>

<div class="mx-auto max-w-6xl px-5 py-10">
	<header class="mb-6">
		<p class="text-small mb-2 font-semibold uppercase tracking-widest text-accent">Admin</p>
		<h1 class="text-display">Review queue</h1>
		<p class="text-body mt-2 text-muted">
			AI translations awaiting a native-speaker check. Approving clears the “awaiting review” badge in
			the reader — so read the text first. The checks on each row say only that the machine found
			nothing, never that the prose is good.
		</p>
	</header>

	{#if loading && !queue}
		<p class="text-body text-muted">Loading…</p>
	{:else if denied}
		<div class="rounded-2xl border border-border bg-surface p-8">
			<h2 class="text-h3 mb-2">Not authorised</h2>
			<p class="text-body text-muted">You don't have access to the admin dashboard.</p>
		</div>
	{:else if error}
		<div class="rounded-2xl border border-border bg-surface p-8">
			<h2 class="text-h3 mb-2">Couldn't load the queue</h2>
			<p class="text-body mb-5 text-muted">{error}</p>
			<button class="btn btn-ghost" onclick={load}>Try again</button>
		</div>
	{:else if queue}
		<div class="mb-5 flex flex-wrap items-end gap-3 rounded-xl border border-border bg-surface p-4">
			<label class="text-small flex flex-col gap-1">
				<span class="text-muted">Language</span>
				<select
					class="rounded-lg border border-border bg-bg px-2 py-1.5"
					bind:value={fLanguage}
					onchange={applyFilters}
				>
					<option value="">All languages</option>
					{#each Object.entries(queue.facets.language) as [code, n] (code)}
						<option value={code}>{languageName(code)} ({n})</option>
					{/each}
				</select>
			</label>
			<label class="text-small flex flex-col gap-1">
				<span class="text-muted">Type</span>
				<select
					class="rounded-lg border border-border bg-bg px-2 py-1.5"
					bind:value={fKind}
					onchange={applyFilters}
				>
					<option value="">All types</option>
					{#each Object.entries(queue.facets.kind) as [k, n] (k)}
						<option value={k}>{KIND_LABEL[k as ReviewKind]} ({n})</option>
					{/each}
				</select>
			</label>
			<label class="text-small flex flex-col gap-1">
				<span class="text-muted">Sort</span>
				<select
					class="rounded-lg border border-border bg-bg px-2 py-1.5"
					bind:value={fSort}
					onchange={applyFilters}
				>
					<option value="oldest">Oldest first</option>
					<option value="flagged">Most unverified verses</option>
					<option value="largest">Largest first</option>
				</select>
			</label>
			<label class="text-small flex items-center gap-2 pb-1.5">
				<input type="checkbox" bind:checked={fFlagged} onchange={applyFilters} />
				<span>Needs attention only ({queue.flagged_total})</span>
			</label>
			<label class="text-small flex items-center gap-2 pb-1.5">
				<input
					type="checkbox"
					checked={fOutcome === 'needs_work'}
					onchange={(e) => {
						fOutcome = (e.currentTarget as HTMLInputElement).checked ? 'needs_work' : '';
						applyFilters();
					}}
				/>
				<span>Needs work ({queue.needs_work_total})</span>
			</label>
			<p class="text-small ml-auto pb-1.5 text-muted">
				Showing {queue.filtered} of {queue.total} awaiting review
			</p>
		</div>

		{#if selectedItems.length}
			<div
				class="mb-4 flex flex-wrap items-center gap-3 rounded-xl border border-accent-soft-border bg-accent-soft p-3"
			>
				<span class="text-small font-semibold">{selectedItems.length} selected</span>
				{#if excludedCount}
					<span class="text-small text-muted">
						{excludedCount} row{excludedCount === 1 ? '' : 's'} on this page can't be bulk-approved —
						flagged, or failing a check.
					</span>
				{/if}
				<button
					class="btn btn-primary !text-small ml-auto !py-1.5"
					onclick={() => decide(selectedItems, 'approved')}
				>
					Approve {selectedItems.length} selected
				</button>
				<button class="btn btn-ghost !text-small !py-1.5" onclick={() => (selected = {})}>
					Clear
				</button>
			</div>
		{/if}

		{#if queue.total === 0 && queue.filtered === 0}
			<div class="rounded-2xl border border-border bg-surface p-8 text-center">
				<p class="text-h3">All clear 🎉</p>
				<p class="text-body mt-1 text-muted">Nothing is awaiting review.</p>
			</div>
		{:else if !visible.length}
			<div class="rounded-2xl border border-border bg-surface p-8 text-center">
				<p class="text-body text-muted">Nothing matches those filters.</p>
			</div>
		{/if}

		{#each groups as [lang, items] (lang)}
			<section class="mb-8">
				<div class="mb-3 flex items-center gap-3">
					<h2 class="text-h3">
						{languageName(lang)}
						<span class="text-muted">({items.length})</span>
					</h2>
					<button class="btn btn-ghost !text-small !py-1" onclick={() => toggleGroup(lang)}>
						Select eligible
					</button>
				</div>

				<ul class="space-y-2">
					{#each items as i (key(i.kind, i.slug, i.language))}
						{@const k = key(i.kind, i.slug, i.language)}
						<li class="rounded-xl border border-border bg-surface">
							{#if settled[k]}
								<div class="flex items-center gap-3 p-4">
									<span class="text-small font-semibold">
										{settled[k].outcome === 'approved' ? 'Approved' : 'Marked needs work'}
									</span>
									<span class="text-small truncate text-muted">{settled[k].title}</span>
									<button
										class="btn btn-ghost !text-small ml-auto !py-1"
										disabled={busy[k]}
										onclick={() => undo(i)}
									>
										{busy[k] ? 'Undoing…' : 'Undo'}
									</button>
								</div>
							{:else}
								<div class="flex items-start gap-3 p-4">
									<input
										class="mt-1.5"
										type="checkbox"
										disabled={!bulkEligible(i)}
										checked={!!selected[k]}
										onchange={(e) =>
											(selected = {
												...selected,
												[k]: (e.currentTarget as HTMLInputElement).checked
											})}
										aria-label="Select {i.title} for bulk approval"
									/>
									<div class="min-w-0 flex-1">
										<div class="flex flex-wrap items-baseline gap-x-2">
											<span class="truncate font-semibold text-text">{i.title}</span>
											<span class="text-small rounded border border-border px-1.5 text-muted">
												{KIND_LABEL[i.kind]}
											</span>
											{#if i.flagged}
												<span class="text-small font-semibold text-gold">
													{i.notes.self_rendered} verse{i.notes.self_rendered === 1 ? '' : 's'}
													unverified
												</span>
											{/if}
										</div>
										<div class="text-small text-muted">
											{i.author}
											{#if i.chapters}· {i.chapters} ch{/if}
											{#if i.words}· {i.words.toLocaleString()} words{/if}
											{#if i.scripture_ref}· {i.scripture_ref}{/if}
										</div>

										{#if i.flags}
											<div class="text-small mt-1 text-muted">
												<span class={i.flags.tags_match ? '' : 'font-semibold text-gold'}>
													tags {i.flags.tag_counts[1]}/{i.flags.tag_counts[0]}{i.flags.tags_match
														? ''
														: ' — sequence differs'}
												</span>
												{#if ratioLabel(i)}<span> · {ratioLabel(i)}</span>{/if}
												{#if !i.flags.quote_style_consistent}
													<span class="font-semibold text-gold"> · mixed quote styles</span>
												{/if}
											</div>
										{/if}

										{#if i.provenance}
											<div class="text-small mt-1 text-muted">
												{#if i.provenance.job_issue}job #{i.provenance.job_issue}{/if}
												{#if i.provenance.pull_request}· PR #{i.provenance.pull_request}{/if}
												{#if i.notes.mined}· {i.notes.mined} verses mined from corpus{/if}
											</div>
										{/if}

										{#if i.outcome?.outcome === 'needs_work'}
											<p class="text-small mt-1 text-gold">
												Needs work{i.outcome.note ? `: ${i.outcome.note}` : ''}
											</p>
										{/if}
										{#if rowError[k]}<p class="text-small mt-2 text-gold">{rowError[k]}</p>{/if}
									</div>

									<button
										class="btn btn-ghost !text-small shrink-0 !py-1.5"
										onclick={() => openDetail(i)}
										aria-expanded={openKey === k}
									>
										{openKey === k ? 'Close' : 'Review'}
									</button>
								</div>

								{#if openKey === k}
									<div class="border-t border-border p-4">
										{#if detailLoading}
											<p class="text-body text-muted">Loading the text…</p>
										{:else if detailError}
											<p class="text-body text-gold">{detailError}</p>
										{:else if detail}
											{#if detail.chapters.length}
												<div class="mb-3 flex flex-wrap gap-1">
													{#each detail.chapters as c (c.order)}
														<button
															class="btn btn-ghost !text-small !px-2 !py-0.5"
															onclick={() => openDetail(i, c.order)}
														>
															{c.order}
														</button>
													{/each}
												</div>
											{/if}

											{#if !detail.aligned}
												<p class="text-small mb-3 font-semibold text-gold">
													Blocks don't line up — {detail.block_counts[0]} in English, {detail
														.block_counts[1]} in {languageName(detail.language)}. Shown unpaired;
													read them side by side rather than trusting the rows to correspond.
												</p>
											{/if}

											{#if detail.notes.length}
												<div class="mb-3 rounded-lg border border-border bg-bg p-3">
													<p class="text-small mb-1 font-semibold">Verses to check</p>
													<ul class="text-small space-y-0.5 text-muted">
														{#each detail.notes as n (n.reference + n.status)}
															<li>
																<span class={n.status === 'self_rendered' ? 'text-gold' : ''}>
																	{n.reference}
																</span>
																{#if n.status === 'mined'}
																	— mined{n.source_file ? ` from ${n.source_file}` : ''}
																{:else}
																	— rendered by the translator, unverified
																{/if}
															</li>
														{/each}
													</ul>
												</div>
											{/if}

											<div
												class="max-h-[28rem] overflow-y-auto rounded-lg border border-border"
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
														class="w-full rounded-lg border border-border bg-bg p-2"
														rows="2"
														bind:value={noteText}
														placeholder="e.g. Ezekiel 36:32 doesn't match the Union wording"
													></textarea>
													<div class="mt-2 flex gap-2">
														<button
															class="btn btn-primary !text-small !py-1.5"
															onclick={() => decide([i], 'needs_work', noteText)}
														>
															Save
														</button>
														<button
															class="btn btn-ghost !text-small !py-1.5"
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
														class="btn btn-primary !text-small !py-1.5"
														disabled={busy[k] || !scrolledEnough}
														onclick={() => decide([i], 'approved')}
													>
														{busy[k] ? 'Saving…' : 'Approve'}
													</button>
													<button
														class="btn btn-ghost !text-small !py-1.5"
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
			</section>
		{/each}

		{#if queue.pages > 1}
			<nav class="flex items-center gap-3" aria-label="Pagination">
				<button
					class="btn btn-ghost !text-small !py-1.5"
					disabled={curPage <= 1}
					onclick={() => goPage(curPage - 1)}
				>
					Previous
				</button>
				<span class="text-small text-muted">Page {curPage} of {totalPages}</span>
				<button
					class="btn btn-ghost !text-small !py-1.5"
					disabled={curPage >= totalPages}
					onclick={() => goPage(curPage + 1)}
				>
					Next
				</button>
			</nav>
		{/if}
	{/if}
</div>
