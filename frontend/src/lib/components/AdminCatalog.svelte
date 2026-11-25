<!--
	One admin inventory list — books, sermons, authors, plans, topics, articles,
	quotes or series — over `GET /api/admin/catalog/<kind>/`. Each route under
	/admin/<kind> is this component with its kind; the columns, labels and links
	are `$lib/adminCatalog`'s.

	The filters live in the URL (`?q=&language=&status=&source=&sort=&page=`), so
	a filtered list is a link: bookmark it, send it, come back to it with Back.
-->
<script lang="ts">
	import { goto } from '$app/navigation';
	import { page } from '$app/stores';
	import { adminResource } from '$lib/adminResource.svelte';
	import AdminGate from '$lib/components/AdminGate.svelte';
	import {
		CATALOG,
		SOURCE_LABELS,
		countLabel,
		queryFromUrl,
		urlSearch,
		type CatalogKind,
		type CatalogQuery,
		type CatalogRow
	} from '$lib/adminCatalog';
	import { getAdminCatalog } from '$lib/library-admin';
	import { hrefInLocale } from '$lib/editionHref';
	import { nameOfLanguage } from '$lib/languageNames';

	let { kind }: { kind: CatalogKind } = $props();

	const cfg = $derived(CATALOG[kind]);
	const query = $derived(queryFromUrl($page.url.searchParams));

	const res = adminResource(
		() => getAdminCatalog(kind, query),
		'Something went wrong loading this list.',
		() => `${kind}${$page.url.search}`
	);

	// The search box is debounced into the URL, so typing doesn't fire a request
	// (or a history entry) per keystroke. It follows the URL when that changes
	// some other way (Back, a link), but not while the person is mid-typing.
	let search = $state('');
	let typing = false;
	$effect(() => {
		const q = query.q ?? '';
		if (!typing) search = q;
	});
	let timer: ReturnType<typeof setTimeout> | undefined;
	function onSearch(v: string) {
		search = v;
		typing = true;
		clearTimeout(timer);
		timer = setTimeout(() => {
			typing = false;
			// Replace, not push: a history entry per pause in typing makes Back useless.
			setQuery({ q: v.trim() }, true);
		}, 300);
	}

	/** Change some filters; any change but paging goes back to page 1. */
	function setQuery(patch: CatalogQuery, replace = false) {
		const next = { ...query, ...patch };
		if (!('page' in patch)) next.page = 1;
		void goto(`${$page.url.pathname}${urlSearch(next)}`, {
			replaceState: replace,
			keepFocus: true,
			noScroll: !('page' in patch)
		});
	}

	const filtered = $derived(!!(query.q || query.language || query.status || query.source));

	const nf = new Intl.NumberFormat('en');
	const fmt = (n: unknown) => (typeof n === 'number' ? nf.format(n) : '—');
	const langName = (code: string) => nameOfLanguage(code, 'en') ?? code;
	const dayFmt = (iso: string | null | undefined) =>
		iso
			? new Date(iso).toLocaleDateString('en', { year: 'numeric', month: 'short', day: 'numeric' })
			: '—';
	// A row with a language opens in that language's pages; a language-agnostic
	// kind (authors, topics, series) on the English ones.
	const siteHref = (r: CatalogRow) => hrefInLocale(cfg.siteHref(r), r.language || 'en');
	const pill = (on: boolean) =>
		`rounded-full px-3 py-1 text-small ${on ? 'bg-accent-soft text-text' : 'text-muted hover:text-text'}`;
</script>

<svelte:head>
	<title>Admin · {cfg.label} — Ochorus</title><meta name="robots" content="noindex" />
</svelte:head>

<div class="mx-auto max-w-6xl px-5 py-10">
	<header class="mb-6">
		<p class="eyebrow mb-2 text-accent">Admin · Library</p>
		<h1 class="text-display">{cfg.label}</h1>
		<p class="mt-2 text-body text-muted">{cfg.blurb}</p>
	</header>

	<AdminGate resource={res} errorTitle="Couldn't load {kind}" keepDataOnError>
		{#snippet children(d)}
			<section class="rounded-card border border-border bg-surface p-5">
				<div class="mb-4 flex flex-wrap items-center justify-between gap-3">
					<h2 class="text-h3" aria-live="polite">
						{countLabel(d.total, cfg.noun)}{#if filtered}{" "}<span class="text-muted">match</span>{/if}
						{#if res.loading}<span class="btn-spinner ms-2 align-middle" aria-label="Updating"
							></span>{/if}
					</h2>
					<div class="flex flex-wrap items-center gap-2">
						<input
							type="search"
							placeholder="Search {cfg.label.toLowerCase()}…"
							aria-label="Search {cfg.label.toLowerCase()}"
							class="w-64 rounded-card border border-border bg-surface-2 px-3 py-1.5 text-body text-text"
							value={search}
							oninput={(e) => onSearch(e.currentTarget.value)}
						/>
						{#if d.facets.languages.length > 1}
							<select
								aria-label="Language"
								class="rounded-card border border-border bg-surface-2 px-3 py-1.5 text-body text-text"
								value={query.language ?? ''}
								onchange={(e) => setQuery({ language: e.currentTarget.value })}
							>
								<option value="">All languages</option>
								{#each d.facets.languages as l (l.code)}
									<option value={l.code}>{langName(l.code)} ({fmt(l.count)})</option>
								{/each}
								{#if query.language && !d.facets.languages.some((l) => l.code === query.language)}
									<option value={query.language}>{langName(query.language)} (0)</option>
								{/if}
							</select>
						{/if}
						{#if d.facets.sources.length}
							<select
								aria-label="Source"
								class="rounded-card border border-border bg-surface-2 px-3 py-1.5 text-body text-text"
								value={query.source ?? ''}
								onchange={(e) => setQuery({ source: e.currentTarget.value })}
							>
								<option value="">Any source</option>
								{#each d.facets.sources as s (s)}
									<option value={s}>{SOURCE_LABELS[s] ?? s}</option>
								{/each}
							</select>
						{/if}
					</div>
				</div>

				<div class="mb-3 flex flex-wrap items-center justify-between gap-x-4 gap-y-2">
					{#if Object.keys(cfg.statusLabels).length}
						<div class="flex flex-wrap gap-1" role="group" aria-label="Status">
							<button
								type="button"
								class={pill(!query.status)}
								aria-pressed={!query.status}
								onclick={() => setQuery({ status: '' })}
							>
								All
							</button>
							{#each Object.entries(cfg.statusLabels) as [key, label] (key)}
								<button
									type="button"
									class={pill(query.status === key)}
									aria-pressed={query.status === key}
									onclick={() => setQuery({ status: key })}
								>
									{label}
									<span class="tabular-nums text-muted">{fmt(d.facets.statuses[key] ?? 0)}</span>
								</button>
							{/each}
						</div>
					{:else}
						<span></span>
					{/if}
					<div class="flex flex-wrap items-center gap-1" role="group" aria-label="Sort">
						<span class="me-1 text-small text-muted">Sort</span>
						{#each d.sorts as key (key)}
							<button
								type="button"
								class={pill(d.sort === key)}
								aria-pressed={d.sort === key}
								onclick={() => setQuery({ sort: key })}
							>
								{cfg.sortLabels[key] ?? key}
							</button>
						{/each}
					</div>
				</div>

				{#if res.error}<p class="mb-3 text-body text-warning">{res.error}</p>{/if}

				{#if d.results.length}
					<div class="overflow-x-auto">
						<table class="w-full text-start text-small">
							<thead class="text-micro uppercase text-muted">
								<tr class="border-b border-border">
									<th class="py-2 text-start font-semibold">
										{cfg.noun === 'author' ? 'Name' : cfg.noun === 'quote' ? 'Quote' : 'Title'}
									</th>
									{#if d.facets.languages.length}<th class="py-2 text-start font-semibold">
											Lang
										</th>{/if}
									{#if d.facets.sources.length}<th
											class="hidden py-2 text-start font-semibold md:table-cell"
										>
											Source
										</th>{/if}
									{#each cfg.columns as c (c.field)}<th class="py-2 text-end font-semibold">
											{c.label}
										</th>{/each}
									<th class="hidden py-2 text-end font-semibold sm:table-cell">
										{d.sort === 'updated' ? 'Changed' : 'Added'}
									</th>
									<th class="py-2"><span class="sr-only">Links</span></th>
								</tr>
							</thead>
							<tbody class="divide-y divide-border">
								{#each d.results as r (`${r.slug}:${r.language ?? ''}`)}
									<tr class="align-top hover:bg-surface-2">
										<td class="py-2 pe-3">
											{#if cfg.adminHref}
												<a
													href={cfg.adminHref(r)}
													class="font-semibold text-text hover:text-accent hover:underline"
												>
													{r.title}
												</a>
											{:else}
												<span class="font-semibold text-text">{r.title}</span>
											{/if}
											{#if r.is_published === false}<span
													class="ms-1 text-micro font-semibold uppercase text-warning"
												>
													unpublished
												</span>{/if}
											{#if r.reviewed === false}<span
													class="ms-1 text-micro font-semibold uppercase text-warning"
												>
													not reviewed
												</span>{/if}
											{#if cfg.meta(r)}<div class="text-micro text-muted">{cfg.meta(r)}</div>{/if}
										</td>
										{#if d.facets.languages.length}<td
												class="py-2 pe-3 text-muted"
												title={r.language ? langName(r.language) : ''}
											>
												{r.language || '—'}
											</td>{/if}
										{#if d.facets.sources.length}<td
												class="hidden py-2 pe-3 text-muted md:table-cell"
											>
												{r.source_type ? SOURCE_LABELS[r.source_type] : '—'}
											</td>{/if}
										{#each cfg.columns as c (c.field)}<td
												class="py-2 ps-3 text-end tabular-nums text-text"
											>
												{fmt(r[c.field])}
											</td>{/each}
										<td class="hidden py-2 ps-3 text-end tabular-nums text-muted sm:table-cell">
											{dayFmt(d.sort === 'updated' ? r.updated_at : r.created_at)}
										</td>
										<td class="whitespace-nowrap py-2 ps-3 text-end">
											<a
												href={siteHref(r)}
												class="text-muted hover:text-accent"
												target="_blank"
												rel="noopener"
												aria-label="View {r.title} on the site"
											>
												site ↗
											</a>
										</td>
									</tr>
								{/each}
							</tbody>
						</table>
					</div>
					{#if d.pages > 1}
						<div class="mt-4 flex items-center justify-between gap-3 text-small text-muted">
							<span>Page {fmt(d.page)} of {fmt(d.pages)}</span>
							<div class="flex gap-2">
								<button
									type="button"
									class="btn btn-ghost"
									disabled={d.page <= 1 || res.loading}
									onclick={() => setQuery({ page: d.page - 1 })}
								>
									Prev
								</button>
								<button
									type="button"
									class="btn btn-ghost"
									disabled={d.page >= d.pages || res.loading}
									onclick={() => setQuery({ page: d.page + 1 })}
								>
									Next
								</button>
							</div>
						</div>
					{/if}
				{:else}
					<p class="text-body text-muted">
						No {cfg.label.toLowerCase()} match{#if query.q}
							“{query.q}”{/if}.
						{#if filtered}<button
								type="button"
								class="text-accent hover:underline"
								onclick={() => setQuery({ q: '', language: '', status: '', source: '' })}
							>
								Clear filters
							</button>{/if}
					</p>
				{/if}
			</section>
		{/snippet}
	</AdminGate>
</div>
