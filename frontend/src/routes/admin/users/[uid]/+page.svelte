<script lang="ts">
	import { goto } from '$app/navigation';
	import { ApiError, apiErrorDetail } from '$lib/api';
	import { auth } from '$lib/auth.svelte';
	import ReaderEmailPanel from '$lib/components/ReaderEmailPanel.svelte';
	import { adminResource } from '$lib/adminResource.svelte';
	import AdminGate from '$lib/components/AdminGate.svelte';
	import { workPath } from '$lib/editionHref';
	import ReadingHeatmap from '$lib/components/ReadingHeatmap.svelte';
	import type { FavoriteKind } from '$lib/favorites.svelte';
	import { deleteAdminUser, formatDateTime, formatDuration, getAdminUser, maskEmail, type UserTimelineEvent } from '$lib/library-admin';
	import type { WorkKind } from '$lib/reading-schema';

	let { data } = $props();

	const detail = adminResource(
		() =>
			getAdminUser(data.uid).catch((e) => {
				// A uid with no account is a legible sentence, not the API's wording.
				if (e instanceof ApiError && e.status === 404) throw new Error('No such user.');
				throw e;
			}),
		'Something went wrong loading this reader.',
		() => data.uid
	);
	const u = $derived(detail.data);

	const nf = new Intl.NumberFormat('en');
	const fmt = (n: number | null | undefined) => nf.format(n ?? 0);
	const dayFmt = (iso: string | null) =>
		iso ? new Date(iso).toLocaleDateString('en', { year: 'numeric', month: 'short', day: 'numeric' }) : '—';
	// For a date-only 'YYYY-MM-DD' (no time): anchor to local midnight so it isn't
	// pulled back a day when the viewer is west of UTC (new Date('YYYY-MM-DD') is UTC).
	const dateOnlyFmt = (iso: string | null) =>
		iso
			? new Date(iso + 'T00:00:00').toLocaleDateString('en', { year: 'numeric', month: 'short', day: 'numeric' })
			: '—';

	// Email is PII: masked until revealed, like the recent-sign-ups list.
	// maskEmail is shared so both admin user pages mask identically.
	let showEmail = $state(false);
	$effect(() => {
		void u; // re-mask on (re)load
		showEmail = false;
	});

	// Deep-links into the reader. A work row carries a chapter; a favorite/plan/
	// topic/article points at the item's landing page. Quotes have no page.
	const favHref = (kind: FavoriteKind, slug: string): string | null => {
		switch (kind) {
			case 'author':
				return `/authors/${slug}`;
			case 'book':
				return `/books/${slug}`;
			case 'sermon':
				return `/sermons/${slug}`;
			case 'plan':
				return `/plans/${slug}`;
			case 'topic':
				return `/topics/${slug}`;
			case 'article':
				return `/articles/${slug}`;
			default:
				return null; // quote — no dedicated page
		}
	};

	// A timeline event's `kind` is a FavoriteKind on a favorite (an author, a
	// quote…) and a WorkKind everywhere else.
	const eventHref = (e: UserTimelineEvent): string | null =>
		e.type === 'plan_started'
			? `/plans/${e.slug}`
			: e.type === 'favorite'
				? favHref(e.kind as FavoriteKind, e.slug)
				: workPath(e.kind as WorkKind, e.slug, e.chapter_order);

	const WORK_KIND_LABEL: Record<WorkKind, string> = {
		book: 'Book',
		sermon: 'Sermon',
		bio: 'Biography',
		article: 'Article'
	};
	const FAV_KIND_LABEL: Record<FavoriteKind, string> = {
		author: 'Author',
		book: 'Book',
		sermon: 'Sermon',
		plan: 'Plan',
		topic: 'Topic',
		article: 'Article',
		quote: 'Quote'
	};
	const TIMELINE_VERB: Record<UserTimelineEvent['type'], string> = {
		read: 'Read',
		finished: 'Finished',
		favorite: 'Saved',
		bookmark: 'Bookmarked in',
		highlight: 'Highlighted in',
		plan_started: 'Started plan'
	};

	// Deleting the account (super admins only) — for test sign-ups. The admin
	// retypes the email (or "delete" when there is none) so a slip on a real reader's page can't do it.
	let deleteConfirm = $state('');
	let deleting = $state(false);
	let deleteError = $state('');
	async function deleteAccount(confirmWord: string) {
		if (deleteConfirm.trim().toLowerCase() !== confirmWord.toLowerCase()) return;
		deleting = true;
		deleteError = '';
		try {
			await deleteAdminUser(data.uid);
			await goto('/admin/users');
		} catch (e) {
			deleteError = apiErrorDetail(e, "Couldn't delete this account.");
		} finally {
			deleting = false;
		}
	}

	// `text` overrides the numeric value for a card that shows a formatted string
	// (the reading-time total).
	type Stat = { label: string; value: number; sub?: string; text?: string };
	const stats = $derived<Stat[]>(
		u
			? [
					{ label: 'Works started', value: u.stats.works_started, sub: `${u.stats.books}b · ${u.stats.sermons}s · ${u.stats.bios} bio · ${u.stats.articles ?? 0} art` },
					{ label: 'Finished', value: u.stats.works_finished },
					{
						label: 'Time reading',
						value: u.stats.reading_seconds,
						text: formatDuration(u.stats.reading_seconds),
						sub: u.stats.sessions ? `${u.stats.sessions} sittings · avg ${formatDuration(u.stats.avg_session_seconds)}` : 'no sittings yet'
					},
					{ label: 'Favorites', value: u.stats.favorites },
					{ label: 'Highlights', value: u.stats.highlights },
					{ label: 'Bookmarks', value: u.stats.bookmarks },
					{ label: 'Days read', value: u.stats.days_read },
					{ label: 'Streak', value: u.stats.streak_current, sub: `longest ${u.stats.streak_longest}` }
				]
			: []
	);

</script>

<svelte:head><title>Admin · {u?.profile.display_name || 'Reader'} — Ochorus</title><meta name="robots" content="noindex" /></svelte:head>

<div class="mx-auto max-w-4xl px-5 py-10">
	<a href="/admin/users" class="text-small text-accent hover:underline">← Back to users</a>

	<AdminGate resource={detail} errorTitle="Couldn't load this reader" loadingText="Loading…" panelClass="mt-6">
		{#snippet children(d)}
			<!-- Identity -->
			<header class="mb-6 mt-3">
				<p class="eyebrow mb-2 text-accent">Admin · Reader</p>
				<h1 class="text-display">{d.profile.display_name || 'Unnamed reader'}</h1>
				<div class="mt-2 flex flex-wrap items-center gap-x-3 gap-y-1 text-body text-muted">
					{#if d.profile.email}
						<button
							type="button"
							class="text-start hover:text-text focus-visible:text-text"
							title={showEmail ? 'Hide email' : 'Reveal email'}
							onclick={() => (showEmail = !showEmail)}
							>{showEmail ? d.profile.email : maskEmail(d.profile.email)}</button
						>
						<span class="text-small">·</span>
					{/if}
					{#if d.profile.providers.length}
						<span class="text-text">{d.profile.providers.map((p) => p.label).join(', ')}</span>
						<span class="text-small">·</span>
					{/if}
					<span class="text-small">reads in {d.profile.locale_name}</span>
					<span class="text-small">·</span>
					<span class="text-small">{d.profile.theme_label}</span>
					{#if d.profile.country}
						<span class="text-small">·</span>
						<span class="text-small">{d.profile.country.name}</span>
					{/if}
				</div>
				<p class="mt-1 text-small text-muted">
					Joined {dayFmt(d.profile.joined_at)} · last seen {dayFmt(d.profile.last_seen_at)}
					{#if d.profile.timezone}· {d.profile.timezone}{/if}
				</p>
			</header>

			<!-- Stats -->
			<section class="mb-8 grid grid-cols-2 gap-3 sm:grid-cols-4">
				{#each stats as s (s.label)}
					<div class="rounded-card border border-border bg-surface p-4">
						<div class="stat-number">{s.text ?? fmt(s.value)}</div>
						<div class="mt-2 text-small font-semibold text-text">{s.label}</div>
						{#if s.sub}<div class="text-small text-muted">{s.sub}</div>{/if}
					</div>
				{/each}
			</section>

			<!-- Activity calendar -->
			<section class="mb-8 rounded-card border border-border bg-surface p-5">
				<div class="mb-3 flex flex-wrap items-baseline justify-between gap-2">
					<h2 class="text-h3">Reading activity</h2>
					<span class="text-small text-muted">
						{fmt(d.stats.days_read)} days · current streak {fmt(d.stats.streak_current)} · longest {fmt(d.stats.streak_longest)}
					</span>
				</div>
				{#if d.activity.days.length}
					<ReadingHeatmap days={d.activity.days} today={d.activity.today} />
					<p class="mt-2 text-micro text-muted">First read {dateOnlyFmt(d.activity.first)}.</p>
				{:else}
					<p class="text-body text-muted">No reading days recorded yet.</p>
				{/if}
			</section>

			<!-- Continue reading -->
			<section class="mb-8">
				<h2 class="text-h3 mb-3">Currently reading</h2>
				{#if d.reading.in_progress.length}
					<ul class="space-y-2">
						{#each d.reading.in_progress as p (p.kind + p.slug)}
							<li class="flex items-baseline justify-between gap-3 rounded-card border border-border bg-surface px-4 py-3">
								<div class="min-w-0">
									<a href={workPath(p.kind, p.slug, p.chapter_order)} class="truncate font-semibold text-text hover:text-accent hover:underline">{p.title}</a>
									<div class="text-small text-muted">
										{WORK_KIND_LABEL[p.kind]}{#if p.author} · {p.author}{/if}
										{#if p.kind === 'book'} · chapter {p.chapter_order}{/if}
										{#if p.language !== 'en'} · {p.language}{/if}
									</div>
								</div>
								<span class="shrink-0 whitespace-nowrap text-small text-muted tabular-nums">{dayFmt(p.updated_at)}</span>
							</li>
						{/each}
					</ul>
				{:else}
					<p class="text-body text-muted">Nothing in progress.</p>
				{/if}
			</section>

			<!-- Finished + Favorites -->
			<div class="mb-8 grid gap-6 md:grid-cols-2">
				<section class="rounded-card border border-border bg-surface p-5">
					<h2 class="text-h3 mb-3">Finished <span class="text-muted">· {fmt(d.reading.finished.length)}</span></h2>
					{#if d.reading.finished.length}
						<ul class="divide-y divide-border">
							{#each d.reading.finished as p (p.kind + p.slug)}
								<li class="flex items-baseline justify-between gap-3 py-2">
									<a href={workPath(p.kind, p.slug, p.chapter_order)} class="min-w-0 truncate text-body text-text hover:text-accent">{p.title}</a>
									<span class="shrink-0 whitespace-nowrap text-small text-muted tabular-nums">{dayFmt(p.finished_at)}</span>
								</li>
							{/each}
						</ul>
					{:else}
						<p class="text-body text-muted">Nothing finished yet.</p>
					{/if}
				</section>

				<section class="rounded-card border border-border bg-surface p-5">
					<h2 class="text-h3 mb-3">Hearts <span class="text-muted">· {fmt(d.favorites.length)}</span></h2>
					{#if d.favorites.length}
						<ul class="divide-y divide-border">
							{#each d.favorites as f (f.kind + f.slug)}
								{@const href = favHref(f.kind, f.slug)}
								<li class="flex items-baseline justify-between gap-3 py-2">
									{#if href}
										<a {href} class="min-w-0 truncate text-body text-text hover:text-accent">{f.label}</a>
									{:else}
										<span class="min-w-0 truncate text-body text-text">{f.label}</span>
									{/if}
									<span class="shrink-0 whitespace-nowrap text-micro text-muted">{FAV_KIND_LABEL[f.kind]}</span>
								</li>
							{/each}
						</ul>
					{:else}
						<p class="text-body text-muted">No hearts yet.</p>
					{/if}
				</section>
			</div>

			<!-- Plans -->
			{#if d.plans.length}
				<section class="mb-8 rounded-card border border-border bg-surface p-5">
					<h2 class="text-h3 mb-3">Plans</h2>
					<ul class="space-y-3">
						{#each d.plans as pl (pl.slug)}
							<li>
								<div class="flex items-baseline justify-between gap-3">
									<a href="/plans/{pl.slug}" class="truncate font-semibold text-text hover:text-accent hover:underline">{pl.title}</a>
									<span class="shrink-0 text-small text-muted tabular-nums">
										{fmt(pl.done)}{#if pl.total_days}/{fmt(pl.total_days)}{/if} days{#if pl.pct != null} · {pl.pct}%{/if}
									</span>
								</div>
								{#if pl.pct != null}
									<div
										class="mt-1.5 h-2 overflow-hidden rounded-full bg-surface-2"
										role="progressbar"
										aria-valuenow={pl.pct}
										aria-valuemin="0"
										aria-valuemax="100"
										aria-label="{pl.title} progress"
									>
										<div class="h-full rounded-full bg-accent-soft" style="width: {pl.pct}%"></div>
									</div>
								{/if}
							</li>
						{/each}
					</ul>
				</section>
			{/if}

			<!-- Reading sittings (time on site) -->
			{#if d.sessions.length}
				<section class="mb-8 rounded-card border border-border bg-surface p-5">
					<h2 class="text-h3 mb-3">Reading sittings <span class="text-muted">· {formatDuration(d.stats.reading_seconds)} total</span></h2>
					<ul class="divide-y divide-border">
						{#each d.sessions as s, si (si)}
							<li class="flex items-baseline justify-between gap-3 py-2">
								<div class="min-w-0">
									<span class="text-body text-text">{formatDuration(s.seconds)}</span>
									{#if s.title}<span class="text-small text-muted"> · {s.title}</span>{/if}
								</div>
								<span class="shrink-0 whitespace-nowrap text-small text-muted tabular-nums">{formatDateTime(s.started_at)}</span>
							</li>
						{/each}
					</ul>
				</section>
			{/if}

			<!-- Highlights & notes -->
			{#if d.highlights.length}
				<section class="mb-8 rounded-card border border-border bg-surface p-5">
					<h2 class="text-h3 mb-3">Highlights &amp; notes</h2>
					<ul class="space-y-3">
						{#each d.highlights as h (h.kind + h.slug + h.chapter_order)}
							<li class="border-s-2 border-border ps-3">
								<div class="flex items-baseline justify-between gap-3">
									<a href={workPath(h.kind, h.slug, h.chapter_order)} class="truncate text-small font-semibold text-text hover:text-accent">
										{h.title}{#if h.kind === 'book'} · ch {h.chapter_order}{/if}
									</a>
									<span class="shrink-0 text-micro text-muted">{fmt(h.count)} mark{h.count === 1 ? '' : 's'}</span>
								</div>
								{#each h.marks.slice(0, 4) as m, mi (mi)}
									<div class="mt-1">
										{#if m.text}<p class="text-body text-text">“{m.text}”</p>{/if}
										{#if m.note}<p class="text-small text-muted">— {m.note}</p>{/if}
									</div>
								{/each}
							</li>
						{/each}
					</ul>
				</section>
			{/if}

			<!-- Bookmarks -->
			{#if d.bookmarks.length}
				<section class="mb-8 rounded-card border border-border bg-surface p-5">
					<h2 class="text-h3 mb-3">Bookmarks</h2>
					<ul class="divide-y divide-border">
						{#each d.bookmarks as b (b.kind + b.slug + b.chapter_order + b.paragraph_index)}
							<li class="py-2">
								<a href={workPath(b.kind, b.slug, b.chapter_order)} class="text-small font-semibold text-text hover:text-accent">
									{b.title}{#if b.kind === 'book'} · ch {b.chapter_order}{/if}
								</a>
								{#if b.snippet}<p class="truncate text-small text-muted">{b.snippet}</p>{/if}
							</li>
						{/each}
					</ul>
				</section>
			{/if}

			<!-- Timeline -->
			<section class="mb-8 rounded-card border border-border bg-surface p-5">
				<h2 class="text-h3 mb-3">Recent activity</h2>
				{#if d.timeline.length}
					<ul class="space-y-2.5">
						{#each d.timeline as e, ei (ei)}
							<li class="flex items-baseline justify-between gap-3">
								<span class="min-w-0 truncate text-body text-text">
									<span class="text-muted">{TIMELINE_VERB[e.type]}</span>
									{#if eventHref(e)}
										<a href={eventHref(e)} class="hover:text-accent hover:underline">{e.title}</a>
									{:else}
										{e.title}
									{/if}
									{#if e.type === 'read' && e.chapter_order}<span class="text-small text-muted"> · ch {e.chapter_order}</span>{/if}
								</span>
								<span class="shrink-0 whitespace-nowrap text-small text-muted tabular-nums">{formatDateTime(e.at)}</span>
							</li>
						{/each}
					</ul>
				{:else}
					<p class="text-body text-muted">No activity recorded yet.</p>
				{/if}
			</section>

			<!-- Email: history + write to them (super admins only, like the Emails section) -->
			{#if auth.isAdmin}
				<ReaderEmailPanel uid={data.uid} name={d.profile.display_name || 'this reader'} />
			{/if}

			<!-- Delete the account (super admins only): the Supabase sign-in and all Ochorus data -->
			{#if auth.isAdmin}
				{@const confirmWord = d.profile.email || 'delete'}
				<section class="mt-8 rounded-card border border-danger bg-surface p-5">
					<h2 class="text-h3 text-danger">Delete account</h2>
					<p class="mt-2 text-body text-muted">
						Permanently deletes this reader's sign-in and everything Ochorus holds for them — reading, highlights,
						favorites, plans, emails. The email address can then be used to sign up again. This can't be undone.
					</p>
					<form
						class="mt-4 flex flex-wrap items-center gap-3"
						onsubmit={(e) => {
							e.preventDefault();
							deleteAccount(confirmWord);
						}}
					>
						<label class="flex min-w-0 flex-1 flex-col gap-1 text-small text-muted">
							Type {d.profile.email ? "the reader's email" : '“delete”'} to confirm
							<input
								type="text"
								autocomplete="off"
								class="rounded-card border border-border bg-bg px-3 py-2 text-body text-text"
								placeholder={confirmWord}
								bind:value={deleteConfirm}
							/>
						</label>
						<button
							type="submit"
							class="self-end rounded-card border border-danger px-4 py-2 font-semibold text-danger hover:bg-danger hover:text-white disabled:opacity-50"
							disabled={deleting || deleteConfirm.trim().toLowerCase() !== confirmWord.toLowerCase()}
							>{deleting ? 'Deleting…' : 'Delete account'}</button
						>
					</form>
					{#if deleteError}<p class="mt-2 text-small text-danger">{deleteError}</p>{/if}
				</section>
			{/if}
		{/snippet}
	</AdminGate>
</div>
