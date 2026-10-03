<script lang="ts">
	import { ApiError } from '$lib/api';
	import { adminResource } from '$lib/adminResource.svelte';
	import AdminGate from '$lib/components/AdminGate.svelte';
	import QueueFixButton from '$lib/components/QueueFixButton.svelte';
	import ReachCurve from '$lib/components/ReachCurve.svelte';
	import PublishToggle from '$lib/components/PublishToggle.svelte';
	import { type SourceType } from '$lib/library-public';
	import {
		adminChapterId,
		adminEditionId,
		chapterFlagLabel,
		getAdminBook,
		setBookPublished,
		fileRetitleJob,
		fileBodyFixJob
	} from '$lib/library-admin';
	import { tick } from 'svelte';
	import { page } from '$app/state';

	let { data } = $props();

	const detail = adminResource(
		() =>
			getAdminBook(data.slug).catch((e) => {
				// A slug that isn't in the library is a legible sentence, not the
				// API's own wording for a missing row.
				if (e instanceof ApiError && e.status === 404) throw new Error('No such work.');
				throw e;
			}),
		'Something went wrong loading this book.',
		() => data.slug
	);
	const book = $derived(detail.data);

	// "Open chapter" links (here and from the content audit) land on a row
	// that only exists once the book has loaded, after the browser has
	// already given up on the hash: scroll to it then, once per hash, so a
	// reload of the book doesn't yank the page back. The row is highlighted
	// from the hash too, since client-side navigation never sets :target.
	const targetId = $derived(page.url.hash.slice(1));
	let scrolledTo = '';
	$effect(() => {
		if (!book || !targetId || targetId === scrolledTo) return;
		scrolledTo = targetId;
		tick().then(() => document.getElementById(targetId)?.scrollIntoView());
	});

	const nf = new Intl.NumberFormat('en');
	const fmt = (n: number | null | undefined) => nf.format(n ?? 0);

	// The publish state the toggle acts on, keyed by language code (one edition
	// per code). Starts from the loaded row and is updated on a successful
	// toggle; PublishToggle owns the transient pending/confirm/error UI.
	let override = $state<Record<string, boolean>>({});
	const published = (l: { code: string; is_published: boolean }) =>
		override[l.code] ?? l.is_published;

	const SOURCE_LABEL: Record<SourceType, string> = {
		public_domain: 'Public domain',
		ai_reviewed: 'AI · reviewed',
		ai_unreviewed: 'AI · unreviewed'
	};
</script>

<svelte:head><title>Admin · {book?.title ?? data.slug} — Ochorus</title><meta name="robots" content="noindex" /></svelte:head>

<div class="mx-auto max-w-4xl px-5 py-10">
	<a href="/admin" class="text-small text-accent hover:underline">← Back to dashboard</a>

	<AdminGate resource={detail} errorTitle="Couldn't load this work" loadingText="Loading…" panelClass="mt-6">
		{#snippet children(b)}
			<header class="mb-6 mt-3">
				<p class="eyebrow mb-2 text-accent">Admin · Work</p>
				<h1 class="text-display">{b.title}</h1>
				<p class="mt-2 flex flex-wrap items-center gap-x-3 gap-y-1 text-body text-muted">
					<span>by <a href="/authors/{b.author.slug}" class="text-accent hover:underline">{b.author.name}</a></span>
					<span class="text-small">·</span>
					<span class="text-small">slug <code class="text-text">{b.slug}</code></span>
					<span class="text-small">·</span>
					<span class="text-small">{b.languages.length} language{b.languages.length === 1 ? '' : 's'}</span>
				</p>
			</header>

			<div class="space-y-5">
				{#each b.languages as l (l.code)}
					<section
						id={adminEditionId(l.code)}
						class="scroll-mt-[calc(var(--appnav-h,0px)+1rem)] rounded-card border border-border bg-surface p-5"
					>
						<div class="mb-3 flex flex-wrap items-start justify-between gap-3">
							<div>
								<h2 class="text-h3">{l.native_name} <span class="text-muted">· {l.name} ({l.code})</span></h2>
								<p class="mt-1 text-body text-text">{l.title}{#if l.subtitle}<span class="text-muted"> — {l.subtitle}</span>{/if}</p>
								<div class="mt-1 flex flex-wrap items-center gap-x-3 gap-y-1 text-small text-muted">
									<span>{SOURCE_LABEL[l.source_type]}</span>
									<span>· {fmt(l.chapters.length)} ch · {fmt(l.word_count)} words</span>
									{#if published(l)}<span class="text-accent">· live on site</span>{:else}<span class="text-warning">· unpublished</span>{/if}
								</div>
							</div>
							<div class="flex shrink-0 flex-col items-end gap-1.5 text-small">
								<PublishToggle
									published={published(l)}
									onToggle={async (next) => {
										const res = await setBookPublished(b.slug, l.code, next);
										override[l.code] = res.is_published;
									}}
								/>
								{#if l.source_url}<a href={l.source_url} class="text-muted hover:text-accent" target="_blank" rel="noopener">source ↗</a>{/if}
								{#if l.pdf_url}<a href={l.pdf_url} class="text-muted hover:text-accent" target="_blank" rel="noopener">PDF ↗</a>{/if}
							</div>
						</div>

						{#if l.chapters.length}
							<ReachCurve
								reach={l.reach}
								chapters={l.chapters}
								steepest={l.steepest}
								stallDays={b.stall_days}
								chapterHref={(order) => `#${adminChapterId(l.code, order)}`}
							/>
							<ul class="divide-y divide-border rounded-card border border-border">
								{#each l.chapters as c (c.order)}
									<!-- The id is what "Open chapter" (here and on the content
									     audit's drop-off list) lands on: the row with the fix buttons. -->
									<li
										id={adminChapterId(l.code, c.order)}
										class="flex scroll-mt-[calc(var(--appnav-h,0px)+4rem)] items-baseline justify-between gap-3 px-3 py-2"
										class:bg-accent-soft={targetId === adminChapterId(l.code, c.order)}
									>
										<a href="/books/{b.slug}/{c.order}" class="min-w-0 truncate text-body text-text hover:text-accent">
											<span class="text-muted tabular-nums">{c.order}.</span> {c.title || '(untitled)'}
										</a>
										<span class="flex shrink-0 items-center gap-2">
											{#each c.flags as f (f)}
												<span class="rounded-full border border-warning/40 px-2 py-0.5 text-micro text-warning">{chapterFlagLabel(f)}</span>
											{/each}
											<QueueFixButton
												label="Fix title"
												seed={c.title}
												fieldLabel="New chapter title"
												saveLabel="Queue fix"
												filedLabel="fix queued"
												submit={(next) =>
													next === (c.title ?? '').trim()
														? Promise.resolve(null)
														: fileRetitleJob(b.slug, l.code, c.order, next)}
											/>
											<QueueFixButton
												label="Flag text"
												multiline
												placeholder="What's wrong with this chapter's text?"
												fieldLabel="What's wrong with the text"
												saveLabel="Queue fix"
												filedLabel="text flagged"
												submit={(note) => fileBodyFixJob(b.slug, l.code, c.order, note)}
											/>
											<span class="text-small tabular-nums text-muted">{fmt(c.word_count)}</span>
										</span>
									</li>
								{/each}
							</ul>
						{:else}
							<p class="text-body text-warning">No chapters.</p>
						{/if}
					</section>
				{/each}
			</div>
		{/snippet}
	</AdminGate>
</div>
