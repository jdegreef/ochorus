<script lang="ts">
	import { onMount } from 'svelte';
	import { page } from '$app/stores';
	import { i18n } from '$lib/i18n.svelte';
	import { localizeHref } from '$lib/paraglide/runtime';
	import { getLang } from '$lib/lang.svelte';
	import { listBooks, listSermons, type BookSummary, type SermonSummary } from '$lib/library';
	import { readingTime } from '$lib/reading';
	import { dayNumber, pickByDay } from '$lib/dailyPicks';

	const t = i18n.t;

	const status = $derived($page.status);
	const isNotFound = $derived(status === 404);
	const title = $derived(isNotFound ? t('error.notFoundTitle') : t('error.genericTitle'));
	const message = $derived(isNotFound ? t('error.notFoundMessage') : t('error.genericMessage'));

	let books = $state<BookSummary[]>([]);
	let sermons = $state<SermonSummary[]>([]);

	// Daily-rotating picks: 3 books + 4 sermons, each from a different person.
	// The books' authors are excluded from the sermon pick so the two shelves
	// surface distinct voices. Client-side + local-date seeded — see dailyPicks.
	const day = dayNumber();
	const bookPicks = $derived(pickByDay(books, 3, day, (b) => b.author.slug));
	const sermonPicks = $derived(
		pickByDay(
			sermons,
			4,
			day ^ 0x9e3779b9,
			(s) => s.author.slug,
			bookPicks.map((b) => b.author.slug)
		)
	);
	const hasPicks = $derived(bookPicks.length > 0 || sermonPicks.length > 0);

	onMount(async () => {
		if (!isNotFound) return;
		const lang = getLang();
		const [b, s] = await Promise.allSettled([listBooks(lang), listSermons(lang)]);
		if (b.status === 'fulfilled') books = b.value;
		if (s.status === 'fulfilled') sermons = s.value;
	});

	// Cover fallback gradient (mirrors the books shelf) for books without an SVG.
	const cover = (hex: string) => `linear-gradient(150deg, ${hex} 0%, ${shade(hex, -28)} 100%)`;
	function shade(hex: string, amt: number): string {
		const n = hex.replace('#', '');
		if (n.length !== 6) return hex;
		const c = [0, 2, 4].map((i) => {
			const v = Math.round(parseInt(n.slice(i, i + 2), 16) * (1 + amt / 100));
			return Math.max(0, Math.min(255, v)).toString(16).padStart(2, '0');
		});
		return `#${c.join('')}`;
	}
</script>

<svelte:head><title>{title} — Ochorus</title></svelte:head>

<div class="mx-auto max-w-5xl px-5 pb-24">
	<!-- Hero -->
	<section class="mx-auto flex max-w-xl flex-col items-center pt-20 pb-4 text-center">
		<p class="mb-2 font-display text-6xl leading-none text-muted/60">{status || 500}</p>
		<h1 class="text-h1 mb-3">{title}</h1>
		<p class="mb-7 text-body text-muted">{message}</p>
		<div class="flex flex-wrap items-center justify-center gap-3">
			{#if !isNotFound}
				<button class="btn btn-primary" onclick={() => location.reload()}>{t('error.tryAgain')}</button
				>
			{/if}
			<a class="btn btn-primary" href={localizeHref('/')}>{t('error.goToLibrary')}</a>
		</div>
	</section>

	{#if isNotFound && hasPicks}
		<!-- "Fresh picks daily" divider -->
		<div class="mx-auto my-12 flex max-w-md items-center gap-4 text-gold">
			<span class="h-px flex-1 bg-gold/30"></span>
			<span class="text-small font-semibold whitespace-nowrap uppercase tracking-[0.2em]">
				{t('error.picksLabel')}
			</span>
			<span class="h-px flex-1 bg-gold/30"></span>
		</div>

		{#if bookPicks.length}
			<section class="mb-14">
				<h2 class="text-h2 mb-1">{t('error.picksBooksHeading')}</h2>
				<p class="mb-6 text-small text-muted">{t('error.picksBooksSub')}</p>
				<div class="grid grid-cols-3 gap-4 sm:gap-6">
					{#each bookPicks as book (book.slug)}
						<a
							href={localizeHref(`/books/${book.slug}`)}
							class="group block hover:no-underline"
							data-testid="notfound-book"
						>
							{#if book.cover_url}
								<img
									src={book.cover_url}
									alt="{t('a11y.coverOf')} {book.title}"
									loading="lazy"
									class="aspect-[3/4] w-full rounded-card object-cover shadow-sm transition-transform group-hover:-translate-y-1"
								/>
							{:else}
								<div
									class="flex aspect-[3/4] flex-col justify-between rounded-card p-3 shadow-sm transition-transform group-hover:-translate-y-1 sm:p-4"
									style="background: {cover(book.cover_color || '#3b5bdb')}"
								>
									<span class="text-[0.65rem] font-semibold uppercase tracking-wider text-white/70">
										{book.author.name.split(' ').slice(-1)}
									</span>
									<span
										style="font-family: var(--font-display)"
										class="text-[0.95rem] font-semibold leading-tight text-white sm:text-[1.15rem]"
									>
										{book.title}
									</span>
								</div>
							{/if}
							<div class="mt-2">
								<div class="text-small font-medium text-text">{book.title}</div>
								<div class="text-[0.8rem] text-muted">{book.author.name}</div>
							</div>
						</a>
					{/each}
				</div>
			</section>
		{/if}

		{#if sermonPicks.length}
			<section>
				<h2 class="text-h2 mb-1">{t('error.picksSermonsHeading')}</h2>
				<p class="mb-6 text-small text-muted">{t('error.picksSermonsSub')}</p>
				<div class="grid gap-4 sm:grid-cols-2">
					{#each sermonPicks as sermon (sermon.slug)}
						<a
							href={localizeHref(`/sermons/${sermon.slug}`)}
							class="group flex flex-col rounded-card border border-border bg-surface-2 px-5 py-4 transition-colors hover:bg-surface hover:no-underline"
							data-testid="notfound-sermon"
						>
							<h3 class="text-h3 leading-snug transition-colors group-hover:text-accent">
								{sermon.title}
							</h3>
							<p class="mt-2 text-small text-muted">
								{sermon.author.name}{#if sermon.scripture_ref}
									· {sermon.scripture_ref}{/if}
								· {readingTime(sermon.word_count)}
							</p>
						</a>
					{/each}
				</div>
			</section>
		{/if}
	{/if}
</div>
