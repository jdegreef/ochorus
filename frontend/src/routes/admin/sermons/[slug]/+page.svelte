<script lang="ts">
	import { ApiError } from '$lib/api';
	import { adminResource } from '$lib/adminResource.svelte';
	import AdminGate from '$lib/components/AdminGate.svelte';
	import PublishToggle from '$lib/components/PublishToggle.svelte';
	import { type SourceType } from '$lib/library-public';
	import { getAdminSermon, setSermonPublished } from '$lib/library-admin';

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

	// The publish state the toggle acts on, keyed by language code (one edition
	// per code); updated on a successful toggle.
	let override = $state<Record<string, boolean>>({});
	const published = (l: { code: string; is_published: boolean }) =>
		override[l.code] ?? l.is_published;

	const SOURCE_LABEL: Record<SourceType, string> = {
		public_domain: 'Public domain',
		ai_reviewed: 'AI · reviewed',
		ai_unreviewed: 'AI · unreviewed'
	};
</script>

<svelte:head><title>Admin · {sermon?.title ?? data.slug} — Ochorus</title><meta name="robots" content="noindex" /></svelte:head>

<div class="mx-auto max-w-4xl px-5 py-10">
	<a href="/admin" class="text-small text-accent hover:underline">← Back to dashboard</a>

	<AdminGate resource={detail} errorTitle="Couldn't load this sermon" loadingText="Loading…" panelClass="mt-6">
		{#snippet children(s)}
			<header class="mb-6 mt-3">
				<p class="eyebrow mb-2 text-accent">Admin · Sermon</p>
				<h1 class="text-display">{s.title}</h1>
				<p class="mt-2 flex flex-wrap items-center gap-x-3 gap-y-1 text-body text-muted">
					<span>by <a href="/authors/{s.author.slug}" class="text-accent hover:underline">{s.author.name}</a></span>
					<span class="text-small">·</span>
					<span class="text-small">slug <code class="text-text">{s.slug}</code></span>
					<span class="text-small">·</span>
					<span class="text-small">{s.languages.length} language{s.languages.length === 1 ? '' : 's'}</span>
				</p>
			</header>

			<div class="space-y-5">
				{#each s.languages as l (l.code)}
					<section class="rounded-card border border-border bg-surface p-5">
						<div class="flex flex-wrap items-start justify-between gap-3">
							<div>
								<h2 class="text-h3">{l.native_name} <span class="text-muted">· {l.name} ({l.code})</span></h2>
								<p class="mt-1 text-body text-text">{l.title}</p>
								<div class="mt-1 flex flex-wrap items-center gap-x-3 gap-y-1 text-small text-muted">
									<span>{SOURCE_LABEL[l.source_type]}</span>
									<span>· {fmt(l.word_count)} words</span>
									{#if l.scripture_ref}<span>· {l.scripture_ref}</span>{/if}
									{#if published(l)}<span class="text-accent">· live on site</span>{:else}<span class="text-warning">· unpublished</span>{/if}
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
								{#if l.source_url}<a href={l.source_url} class="text-muted hover:text-accent" target="_blank" rel="noopener">source ↗</a>{/if}
							</div>
						</div>
					</section>
				{/each}
			</div>
		{/snippet}
	</AdminGate>
</div>
