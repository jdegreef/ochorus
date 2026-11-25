<script lang="ts">
	import { ApiError } from '$lib/api';
	import { adminResource } from '$lib/adminResource.svelte';
	import AdminGate from '$lib/components/AdminGate.svelte';
	import PublishToggle from '$lib/components/PublishToggle.svelte';
	import UntranslatedPanel from '$lib/components/admin/UntranslatedPanel.svelte';
	import { SOURCE_LABELS } from '$lib/adminCatalog';
	import { adminReviewHref } from '$lib/adminLinks';
	import { hrefInLocale } from '$lib/editionHref';
	import { lang } from '$lib/lang.svelte';
	import {
		fileFieldEditJob,
		getAdminSermon,
		setSermonPublished,
		type AdminSermonLang
	} from '$lib/library-admin';
	import QueueFixButton from '$lib/components/QueueFixButton.svelte';

	let { data } = $props();

	const detail = adminResource(
		() =>
			getAdminSermon(data.slug).catch((e) => {
				if (e instanceof ApiError && e.status === 404) throw new Error('No such sermon.');
				throw e;
			}),
		'Something went wrong loading this sermon.',
		() => data.slug
	);
	const sermon = $derived(detail.data);

	const nf = new Intl.NumberFormat('en');
	const fmt = (n: number | null | undefined) => nf.format(n ?? 0);
	const dayFmt = (iso: string | null) =>
		iso
			? new Date(iso).toLocaleDateString('en', { year: 'numeric', month: 'short', day: 'numeric' })
			: '—';

	// The publish state the toggle acts on, keyed by language code (one edition
	// per code); updated on a successful toggle.
	let override = $state<Record<string, boolean>>({});
	const published = (l: { code: string; is_published: boolean }) =>
		override[l.code] ?? l.is_published;

	// An edition's own page: /es/sermons/… for the Spanish one. A language the
	// reader UI doesn't route yet has no pages to open, so no link.
	const siteHref = (code: string, slug: string) =>
		lang.isAvailable(code) ? hrefInLocale(`/sermons/${slug}`, code) : null;

	// What the review queue has to say about an AI edition, in a few words.
	const reviewLabel = (l: AdminSermonLang): string | null => {
		if (l.source_type === 'public_domain') return null;
		if (!l.review) return l.source_type === 'ai_reviewed' ? 'Reviewed' : 'Awaiting review';
		if (l.review.outcome === 'needs_work') return 'Needs work';
		return l.review.confirmed ? 'Approved' : 'Approved · awaiting approver';
	};
</script>

<svelte:head>
	<title>Admin · {sermon?.title ?? data.slug} — Ochorus</title><meta
		name="robots"
		content="noindex"
	/>
</svelte:head>

<div class="mx-auto max-w-4xl px-5 py-10">
	<a href="/admin/sermons" class="text-small text-accent hover:underline">← All sermons</a>

	<AdminGate
		resource={detail}
		errorTitle="Couldn't load this sermon"
		loadingText="Loading…"
		panelClass="mt-6"
	>
		{#snippet children(s)}
			<header class="mb-6 mt-3">
				<p class="eyebrow mb-2 text-accent">Admin · Sermon</p>
				<h1 class="text-display">{s.title}</h1>
				<p class="mt-2 flex flex-wrap items-center gap-x-3 gap-y-1 text-body text-muted">
					<span>
						by <a href="/authors/{s.author.slug}" class="text-accent hover:underline">
							{s.author.name}
						</a>
					</span>
					<span class="text-small">·</span>
					<span class="text-small">slug <code class="text-text">{s.slug}</code></span>
					<span class="text-small">·</span>
					<span class="text-small">
						{s.languages.length} language{s.languages.length === 1 ? '' : 's'}
					</span>
					<span class="text-small">·</span>
					<a
						href="/sermons/{s.slug}"
						class="text-small text-accent hover:underline"
						target="_blank"
						rel="noopener"
					>
						View on site ↗
					</a>
					<span class="text-small">·</span>
					<a
						href="/admin/activity?q={encodeURIComponent(`sermon:${s.slug}:`)}"
						class="text-small text-accent hover:underline"
					>
						History
					</a>
				</p>
				{#if s.topics.length}
					<p class="mt-3 flex flex-wrap items-center gap-2 text-small">
						<span class="text-muted">Topics</span>
						{#each s.topics as t (t.slug)}
							<a
								href="/topics/{t.slug}"
								class="rounded-full border border-border px-2.5 py-0.5 text-text hover:border-accent hover:no-underline"
								target="_blank"
								rel="noopener"
							>
								{t.title}
							</a>
						{/each}
					</p>
				{:else}
					<p class="mt-3 text-small text-muted">On no topic shelf yet.</p>
				{/if}
			</header>

			<div class="space-y-5">
				{#each s.languages as l (l.code)}
					{@const review = reviewLabel(l)}
					{@const site = siteHref(l.code, s.slug)}
					<section class="rounded-card border border-border bg-surface p-5">
						<div class="flex flex-wrap items-start justify-between gap-3">
							<div class="min-w-0">
								<h2 class="text-h3">
									{l.native_name} <span class="text-muted">· {l.name} ({l.code})</span>
								</h2>
								<p class="mt-1 text-body text-text">{l.title}</p>
								<!-- Fixture-owned text: each files a content-edit job (one fixture edit the seeds carry live). -->
								<div class="mt-1 flex flex-wrap items-start gap-x-3 gap-y-1 text-small">
									{#each [{ field: 'title', label: 'Edit title', value: l.title, multiline: false }, { field: 'scripture_ref', label: 'Edit Scripture', value: l.scripture_ref, multiline: false }, { field: 'summary', label: 'Edit summary', value: l.summary, multiline: true }] as const as f (f.field)}
										<QueueFixButton
											label={f.label}
											seed={f.value}
											multiline={f.multiline}
											allowEmpty={f.field !== 'title'}
											fieldLabel="New {f.field.replace('_', ' ')}"
											saveLabel="Suggest"
											filedLabel="edit queued"
											submit={(next) =>
												fileFieldEditJob(
													{ entity: 'sermon', field: f.field, slug: s.slug, language: l.code },
													f.value,
													next
												)}
										/>
									{/each}
								</div>
								<div class="mt-1 flex flex-wrap items-center gap-x-3 gap-y-1 text-small text-muted">
									<span>{SOURCE_LABELS[l.source_type]}</span>
									<span>· {fmt(l.word_count)} words</span>
									{#if l.scripture_ref}<span>· {l.scripture_ref}</span>{/if}
									{#if l.preached_on}<span>· preached {dayFmt(l.preached_on)}</span>{/if}
									{#if l.quotes}<span>· {fmt(l.quotes)} quote{l.quotes === 1 ? '' : 's'}</span>{/if}
									{#if published(l)}<span class="text-accent">· live on site</span>{:else}<span
											class="text-warning"
										>
											· unpublished
										</span>{/if}
								</div>
								<div class="mt-1 text-micro text-muted">
									Added {dayFmt(l.created_at)}{#if l.updated_at}{' '}· changed {dayFmt(
											l.updated_at
										)}{/if}
								</div>
							</div>
							<div class="flex shrink-0 flex-col items-end gap-1.5 text-small">
								<PublishToggle
									published={published(l)}
									onToggle={async (next) => {
										const res = await setSermonPublished(s.slug, l.code, next);
										override[l.code] = res.is_published;
									}}
								/>
								{#if site}<a
										href={site}
										class="text-muted hover:text-accent"
										target="_blank"
										rel="noopener"
									>
										view on site ↗
									</a>{/if}
								{#if l.source_url}<a
										href={l.source_url}
										class="text-muted hover:text-accent"
										target="_blank"
										rel="noopener"
									>
										source ↗
									</a>{/if}
							</div>
						</div>

						{#if review}
							<div
								class="mt-3 flex flex-wrap items-center gap-x-3 gap-y-1 rounded-sm bg-surface-2 px-3 py-2 text-small"
							>
								<span
									class="font-semibold {review === 'Needs work' || review === 'Awaiting review'
										? 'text-warning'
										: 'text-text'}"
								>
									{review}
								</span>
								{#if l.review?.note}<span class="min-w-0 text-muted">“{l.review.note}”</span>{/if}
								<a
									href={adminReviewHref('sermon', s.slug, l.code)}
									class="ms-auto font-semibold text-accent hover:underline"
								>
									Compare with English →
								</a>
							</div>
						{/if}

						{#if l.summary}
							<p class="mt-4 text-body text-text">{l.summary}</p>
						{:else}
							<p class="mt-4 text-small text-warning">No summary.</p>
						{/if}

						{#if l.main_points.length}
							<div class="mt-4">
								<h3 class="text-small font-semibold text-text">Main points</h3>
								<ol class="mt-1 list-decimal space-y-1 ps-5 text-small text-text">
									{#each l.main_points as point, i (i)}<li>{point}</li>{/each}
								</ol>
							</div>
						{/if}

						{#if l.study_questions.length}
							<details class="mt-4">
								<summary class="cursor-pointer text-small font-semibold text-text">
									Questions &amp; answers · {l.study_questions.length}
								</summary>
								<dl class="mt-2 space-y-3 text-small">
									{#each l.study_questions as qa, i (i)}
										<div>
											<dt class="font-semibold text-text">{qa.question}</dt>
											<dd class="mt-0.5 text-muted">{qa.answer}</dd>
										</div>
									{/each}
								</dl>
							</details>
						{:else}
							<p class="mt-4 text-small text-muted">No questions &amp; answers yet.</p>
						{/if}

						{#if l.excerpt}
							<details class="mt-4">
								<summary class="cursor-pointer text-small font-semibold text-text">Opening</summary>
								<p class="mt-2 text-small leading-relaxed text-muted">{l.excerpt}</p>
							</details>
						{/if}
						{#if l.attribution}<p class="mt-3 text-micro text-muted">{l.attribution}</p>{/if}
					</section>
				{/each}
			</div>

			<UntranslatedPanel kind="sermon" slug={s.slug} untranslated={s.untranslated} />
		{/snippet}
	</AdminGate>
</div>
