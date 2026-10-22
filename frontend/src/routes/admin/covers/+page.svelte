<script lang="ts">
	import { assetUrl } from '$lib/assetUrl';
	import { adminResource } from '$lib/adminResource.svelte';
	import AdminGate from '$lib/components/AdminGate.svelte';
	import { shareImage } from '$lib/coverArt';
	import { hydrateSrc } from '$lib/hydrateSrc';
	import {
		FLAG_LABEL,
		PAINTER_CAP,
		coverFlags,
		editionKey,
		groupCovers,
		hueOf,
		painterWorks,
		type CoverFlag,
		type WallGroup
	} from '$lib/coverWall';
	import { getAdminCovers, type AdminCover } from '$lib/library-admin';

	const res = adminResource(getAdminCovers, 'Something went wrong loading the covers.');

	// What is shown. English by default: it is the shelf most readers meet, and
	// every other language's paintings are the same files.
	let lang = $state('en');
	let tier = $state('all');
	let flaggedOnly = $state(false);
	let group = $state<WallGroup>('author');
	let size = $state<'s' | 'm'>('s');

	// Mean hue per edition, measured from each thumbnail as it loads — what the
	// `colour` order sorts by. Measured, not stored: it follows the pictures.
	let hues = $state(new Map<string, number>());

	function measure(e: Event, c: AdminCover) {
		const img = e.currentTarget as HTMLImageElement;
		try {
			const canvas = document.createElement('canvas');
			canvas.width = canvas.height = 8;
			const ctx = canvas.getContext('2d', { willReadFrequently: true });
			if (!ctx) return;
			ctx.drawImage(img, 0, 0, 8, 8);
			const px = ctx.getImageData(0, 0, 8, 8).data;
			let r = 0, g = 0, b = 0;
			for (let i = 0; i < px.length; i += 4) {
				r += px[i];
				g += px[i + 1];
				b += px[i + 2];
			}
			const n = px.length / 4;
			const next = new Map(hues);
			next.set(editionKey(c), hueOf(r / n, g / n, b / n));
			hues = next;
		} catch {
			// A tainted canvas (a cross-origin cover) just isn't measured.
		}
	}

	const TIERS = ['painting', 'original', 'derived', 'designed', 'plate', 'none', 'other'];
	const GROUPS: [WallGroup, string][] = [
		['author', 'By author'],
		['painter', 'By painter'],
		['tier', 'By kind of cover'],
		['colour', 'By colour'],
		['none', 'No grouping']
	];

	const nf = new Intl.NumberFormat('en');
	const plural = (n: number, one: string, many = `${one}s`) => `${nf.format(n)} ${n === 1 ? one : many}`;
</script>

<svelte:head><title>Admin · Cover wall — Ochorus</title><meta name="robots" content="noindex" /></svelte:head>

<div class="px-5 py-10">
	<a href="/admin" class="text-small text-accent hover:underline">← Back to dashboard</a>

	<AdminGate resource={res} errorTitle="Couldn't load the covers" loadingText="Loading covers…" panelClass="mt-6">
		{#snippet children(all)}
			{@const painters = painterWorks(all)}
			{@const languages = [...new Set(all.map((c) => c.language))].sort()}
			{@const inLang = lang === 'all' ? all : all.filter((c) => c.language === lang)}
			{@const flagged = new Map(inLang.map((c) => [editionKey(c), coverFlags(c, painters)]))}
			{@const shown = inLang.filter(
				(c) => (tier === 'all' || c.tier === tier) && (!flaggedOnly || flagged.get(editionKey(c))!.length)
			)}
			<!-- Only the colour order reads `hues`, so thumbnails loading don't regroup the other views. -->
			{@const sections = group === 'colour' ? groupCovers(shown, group, hues) : groupCovers(shown, group)}
			{@const tierCounts = TIERS.map((t) => [t, inLang.filter((c) => c.tier === t).length] as const).filter(([, n]) => n)}
			{@const flagCounts = (Object.keys(FLAG_LABEL) as CoverFlag[]).map(
				(f) => [f, [...flagged.values()].filter((fs) => fs.includes(f)).length] as const
			)}
			{@const repeated = [...painters].filter(([, w]) => w.size > 1).sort((a, b) => b[1].size - a[1].size || a[0].localeCompare(b[0]))}

			<header class="mb-6 mt-3 max-w-3xl">
				<p class="eyebrow mb-2 text-accent">Admin · Covers</p>
				<h1 class="text-display">Cover wall</h1>
				<p class="mt-2 text-body text-muted">
					Every published cover at the size a reader meets it, so the shelf can be judged as a shelf. Flags mark
					what to look at again: a book still on a plate, a painter on more than {PAINTER_CAP} works, and a framed
					cover whose scrim has all but hidden its picture.
				</p>
			</header>

			<!-- Totals for the language in view: what the covers are made of, and what is flagged. -->
			<div class="mb-5 flex flex-wrap gap-x-5 gap-y-1 text-small text-muted">
				<span class="font-semibold text-text">{plural(inLang.length, 'edition')}</span>
				{#each tierCounts as [t, n] (t)}<span>{nf.format(n)} {t}</span>{/each}
				<span aria-hidden="true">·</span>
				{#each flagCounts as [f, n] (f)}
					<span class={n ? 'font-semibold text-text' : ''}>{nf.format(n)} {FLAG_LABEL[f].toLowerCase()}</span>
				{/each}
			</div>

			<div class="mb-6 flex flex-wrap items-center gap-3">
				<select bind:value={lang} aria-label="Language" class="field text-small">
					<option value="all">All languages</option>
					{#each languages as l (l)}<option value={l}>{l}</option>{/each}
				</select>
				<select bind:value={tier} aria-label="Kind of cover" class="field text-small">
					<option value="all">Every kind of cover</option>
					{#each TIERS as t (t)}<option value={t}>{t}</option>{/each}
				</select>
				<select bind:value={group} aria-label="Group the wall" class="field text-small">
					{#each GROUPS as [g, label] (g)}<option value={g}>{label}</option>{/each}
				</select>
				<label class="flex items-center gap-2 text-small text-text">
					<input type="checkbox" bind:checked={flaggedOnly} /> Flagged only
				</label>
				<div class="seg" role="group" aria-label="Thumbnail size">
					<button type="button" aria-pressed={size === 's'} class:active={size === 's'} onclick={() => (size = 's')}>Shelf</button>
					<button type="button" aria-pressed={size === 'm'} class:active={size === 'm'} onclick={() => (size = 'm')}>Larger</button>
				</div>
			</div>

			{#if group === 'colour'}
				<p class="mb-4 text-small text-muted">
					Sorted by each cover's mean hue as its thumbnail loads, so a run of one colour shows as one band. Greys
					and covers still loading sit at the end.
				</p>
			{/if}

			<div class="lg:flex lg:items-start lg:gap-8">
				<div class="min-w-0 flex-1">
					{#if !shown.length}
						<p class="rounded-card border border-border bg-surface p-5 text-body text-muted">
							{flaggedOnly ? 'Nothing flagged here.' : 'No covers match.'}
						</p>
					{/if}
					{#each sections as s (s.key)}
						<section class="mb-8">
							{#if s.label}
								<h2 class="mb-3 flex items-baseline gap-2.5 text-h3 text-muted">
									{s.label}
									<span class="tabular-nums text-small opacity-70">{s.covers.length}</span>
								</h2>
							{/if}
							<ul class="wall" class:wall-m={size === 'm'}>
								{#each s.covers as c (editionKey(c))}
									{@const img = shareImage(c)}
									{@const fs = flagged.get(editionKey(c)) ?? []}
									<li>
										<a
											href="/admin/books/{c.slug}"
											class="tile"
											title="{c.title} — {c.author.name} · {c.language} · {c.tier}{c.artwork
												? ` · ${c.artwork.artist}, ${c.artwork.title}`
												: ''}{fs.length ? ` · ${fs.map((f) => FLAG_LABEL[f]).join(', ')}` : ''}"
										>
											{#if img}
												{@const src = assetUrl(img.url)}
												<img {src} use:hydrateSrc={{ src }} alt="{c.title} — {c.author.name}" loading="lazy" decoding="async" width="600" height="800" onload={(e) => measure(e, c)} />
											{:else}
												<span class="tile-empty">{c.title}</span>
											{/if}
											{#if fs.length}
												<span class="tile-flags">
													{#each fs as f (f)}<span class="flag flag-{f}">{f}</span>{/each}
												</span>
											{/if}
										</a>
										{#if size === 'm'}
											<p class="mt-1 truncate text-small text-muted">{c.artwork?.artist ?? c.tier}</p>
										{/if}
									</li>
								{/each}
							</ul>
						</section>
					{/each}
				</div>

				<!-- The repeats the cap is about: painters by distinct works, across every language. -->
				<aside class="mt-8 shrink-0 rounded-card border border-border bg-surface p-4 lg:sticky lg:top-[calc(var(--appnav-h,0px)+1rem)] lg:mt-0 lg:w-72">
					<h2 class="section-label mb-2">Painters on more than one work</h2>
					{#if repeated.length}
						<ol class="space-y-1 text-small">
							{#each repeated as [artist, works] (artist)}
								<li class="flex items-baseline justify-between gap-3">
									<span class="truncate {works.size > PAINTER_CAP ? 'font-semibold text-text' : 'text-muted'}">{artist}</span>
									<span class="tabular-nums {works.size > PAINTER_CAP ? 'font-semibold text-danger' : 'text-muted'}">{works.size}</span>
								</li>
							{/each}
						</ol>
					{:else}
						<p class="text-small text-muted">No painter is on more than one work.</p>
					{/if}
				</aside>
			</div>
		{/snippet}
	</AdminGate>
</div>

<style>
	.wall {
		display: grid;
		grid-template-columns: repeat(auto-fill, minmax(4.5rem, 1fr));
		gap: 0.5rem;
	}
	.wall-m {
		grid-template-columns: repeat(auto-fill, minmax(8.5rem, 1fr));
		gap: 0.9rem;
	}
	.tile {
		position: relative;
		display: block;
		aspect-ratio: 3 / 4;
		overflow: hidden;
		border-radius: var(--radius-sm);
		background: var(--surface-2);
		box-shadow: 0 1px 2px rgb(0 0 0 / 0.18);
	}
	.tile img {
		display: block;
		width: 100%;
		height: 100%;
		object-fit: cover;
	}
	.tile:hover,
	.tile:focus-visible {
		outline: 2px solid var(--accent);
		outline-offset: 2px;
	}
	.tile-empty {
		display: grid;
		height: 100%;
		place-items: center;
		padding: 0.25rem;
		text-align: center;
		font-size: var(--fs-micro);
		color: var(--muted);
	}
	.tile-flags {
		position: absolute;
		inset-inline: 0.2rem;
		bottom: 0.2rem;
		display: flex;
		flex-wrap: wrap;
		gap: 0.15rem;
	}
	.flag {
		border-radius: var(--radius-sm);
		padding: 0 0.25rem;
		font-size: var(--fs-micro);
		font-weight: 600;
		line-height: 1.4;
	}
	.flag-plate {
		background: var(--danger);
		color: white;
	}
	.flag-painter {
		background: var(--gold);
		color: black;
	}
	.flag-scrim {
		background: black;
		color: white;
	}
</style>
