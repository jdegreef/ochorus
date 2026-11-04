<script lang="ts">
	import { assetUrl } from '$lib/assetUrl';
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
		fileBodyFixJob,
		createAdminTranslationJob,
		type AdminUntranslated
	} from '$lib/library-admin';
	import { JOB_TONE_CLASS, jobStatusMeta } from '$lib/adminActivity';
	import { hrefInLocale } from '$lib/editionHref';
	import { lang } from '$lib/lang.svelte';
	import { auth } from '$lib/auth.svelte';
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

	// An edition's own pages: /es/books/… for the Spanish one. A language the
	// reader UI doesn't route yet has no pages to open, so no link.
	const siteHref = (code: string, path: string) => (lang.isAvailable(code) ? hrefInLocale(path, code) : null);

	// ---- not yet translated ----
	type Missing = AdminUntranslated['languages'][number];
	// A job filed from this page, by language: the stage it now holds, or the
	// error the POST answered. The list itself is the load's; this overlays it.
	let filed = $state<Record<string, { stage?: 'queued'; error?: string }>>({});
	let filing = $state<Record<string, boolean>>({});
	const stageOf = (m: Missing) => filed[m.code]?.stage ?? m.job_status;
	// A job can be filed when nothing is in flight: never filed, or one that
	// closed without shipping. The backend's duplicate guard is the real check.
	const canFile = (m: Missing) => {
		const st = stageOf(m);
		return (st === 'none' || st === 'closed' || st === 'unknown') && auth.can('translate', 'suggest', m.code);
	};
	async function translate(slug: string, m: Missing) {
		filing[m.code] = true;
		try {
			await createAdminTranslationJob({ type: 'book', slug, language: m.code });
			filed[m.code] = { stage: 'queued' };
		} catch (e) {
			filed[m.code] = { error: e instanceof Error ? e.message : 'Could not file the job.' };
		} finally {
			filing[m.code] = false;
		}
	}

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
				<p class="mt-2 flex flex-wrap gap-x-4 gap-y-1 text-small">
					<a href="/books/{b.slug}" class="text-accent hover:underline" target="_blank" rel="noopener">View on site ↗</a>
					<!-- Every language's rows of this work: the targets are book:<slug>:<lang>. -->
					<a href="/admin/activity?q={encodeURIComponent(`book:${b.slug}:`)}" class="text-accent hover:underline">History</a>
					{#if b.untranslated?.languages.length}
						<a href="#untranslated" class="text-accent hover:underline">
							Not yet in {b.untranslated.languages.length} language{b.untranslated.languages.length === 1 ? '' : 's'}
						</a>
					{/if}
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
								{#if siteHref(l.code, `/books/${b.slug}`)}
									<a href={siteHref(l.code, `/books/${b.slug}`)} class="text-muted hover:text-accent" target="_blank" rel="noopener">view on site ↗</a>
								{/if}
								{#if l.source_url}<a href={l.source_url} class="text-muted hover:text-accent" target="_blank" rel="noopener">source ↗</a>{/if}
								{#if l.pdf_url}<a href={assetUrl(l.pdf_url)} class="text-muted hover:text-accent" target="_blank" rel="noopener">PDF ↗</a>{/if}
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
										<!-- This edition's chapter, not the English one. -->
										<a href={siteHref(l.code, `/books/${b.slug}/${c.order}`) ?? `/books/${b.slug}/${c.order}`} class="min-w-0 truncate text-body text-text hover:text-accent">
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

			{#if b.untranslated?.languages.length}
				<section id="untranslated" class="mt-8 scroll-mt-[calc(var(--appnav-h,0px)+1rem)] rounded-card border border-border bg-surface p-5">
					<h2 class="text-h3">Not yet translated</h2>
					{#if b.untranslated.blocked}
						<p class="mt-1 text-small text-muted">
							This book is under copyright, so no translation may be made of it.
						</p>
					{:else}
						<p class="mt-1 text-small text-muted">
							Where each language's translation job stands. Filing one opens a GitHub issue a worker picks up.
						</p>
					{/if}
					<ul class="mt-3 divide-y divide-border rounded-card border border-border">
						{#each b.untranslated.languages as m (m.code)}
							{@const st = stageOf(m)}
							<li class="flex flex-wrap items-center justify-between gap-3 px-3 py-2">
								<span class="text-body text-text">{m.native_name} <span class="text-small text-muted">· {m.name} ({m.code})</span></span>
								<span class="flex flex-wrap items-center gap-2 text-small">
									{#if st === 'none'}
										<span class="text-muted">Not filed</span>
									{:else}
										{@const js = jobStatusMeta(st, `book:${b.slug}:${m.code}`)}
										<span class="rounded-full border px-2 py-0.5 text-micro font-semibold {JOB_TONE_CLASS[js.tone]}" title={js.hint}>{js.label}</span>
									{/if}
									{#if m.pr_url}<a href={m.pr_url} class="text-muted hover:text-accent" target="_blank" rel="noopener">PR ↗</a>{/if}
									{#if m.issue_url}<a href={m.issue_url} class="text-muted hover:text-accent" target="_blank" rel="noopener">issue ↗</a>{/if}
									{#if filed[m.code]?.error}<span class="text-danger">{filed[m.code].error}</span>{/if}
									{#if !b.untranslated.blocked && canFile(m)}
										<button
											class="btn btn-sm btn-ghost"
											onclick={() => translate(b.slug, m)}
											disabled={filing[m.code]}
											aria-busy={filing[m.code] ? 'true' : undefined}
											>{#if filing[m.code]}<span class="btn-spinner" aria-hidden="true"></span>{/if}Translate</button
										>
									{/if}
								</span>
							</li>
						{/each}
					</ul>
				</section>
			{/if}
		{/snippet}
	</AdminGate>
</div>
