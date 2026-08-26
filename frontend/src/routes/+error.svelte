<script lang="ts">
	import { onMount } from 'svelte';
	import { page } from '$app/stores';
	import { i18n } from '$lib/i18n.svelte';
	import { localizeHref } from '$lib/href';
	import { getLang } from '$lib/lang.svelte';
	import { listBooks, listSermons, type BookSummary, type SermonSummary } from '$lib/library-public';
	import { dayNumber, pickByDay } from '$lib/dailyPicks';
	import BookCover from '$lib/components/BookCover.svelte';
	import SermonCard from '$lib/components/SermonCard.svelte';

	const t = i18n.t;

	const status = $derived($page.status);
	const isNotFound = $derived(status === 404);
	const title = $derived(isNotFound ? t('error.notFoundTitle') : t('error.genericTitle'));
	const message = $derived(isNotFound ? t('error.notFoundMessage') : t('error.genericMessage'));

	// The path someone mistyped is the best guess at what they wanted, so it
	// seeds a search rather than being thrown away: "/books/the-imitaton" →
	// "the imitaton". Hyphens and slashes out, extension and locale prefix off.
	const searchSeed = $derived(
		$page.url.pathname
			.replace(/^\/[a-z]{2}(-[a-z]+)?(?=\/|$)/, '')
			.replace(/\.[a-z0-9]{1,5}$/i, '')
			.split('/')
			.filter(Boolean)
			.pop()
			?.replace(/[-_]+/g, ' ')
			.trim() ?? ''
	);

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

</script>

<svelte:head>
	<title>{title} — Ochorus</title>
	<!-- Never index error/not-found pages. The static adapter serves 200.html for
	     unknown paths, so without this a mistyped or stale URL could be indexed as
	     a soft-404 duplicate of the app shell. -->
	<meta name="robots" content="noindex" />
</svelte:head>

<div class="mx-auto max-w-5xl px-5 pb-24">
	<!-- Hero -->
	<section class="mx-auto flex max-w-xl flex-col items-center pt-20 pb-4 text-center">
		<p class="mb-2 font-display text-6xl leading-none text-muted/60">{status || 500}</p>
		<h1 class="text-h1 mb-3">{title}</h1>
		<p class="mb-6 text-body text-muted">{message}</p>
		{#if isNotFound}
			<!-- A search box, not just a way home: the page already knows what was
			     asked for, and the library it would be searched in is already
			     loaded below. -->
			<form
				method="GET"
				action={localizeHref('/search')}
				role="search"
				class="mb-4 flex w-full max-w-sm items-center gap-2"
			>
				<input
					name="q"
					type="search"
					value={searchSeed}
					enterkeyhint="search"
					placeholder={t('search.placeholder')}
					aria-label={t('nav.search')}
					class="field grow"
				/>
				<button type="submit" class="btn btn-primary shrink-0">{t('nav.search')}</button>
			</form>
		{/if}
		<!-- One primary per view (STYLE_GUIDE §5). The generic state offered two
		     solid buttons side by side, so neither read as the thing to do. -->
		<div class="flex flex-wrap items-center justify-center gap-3">
			{#if !isNotFound}
				<button class="btn btn-primary" onclick={() => location.reload()}>{t('error.tryAgain')}</button>
			{/if}
			<a class="btn btn-ghost" href={localizeHref('/')}>{t('error.goToLibrary')}</a>
		</div>
	</section>

	{#if isNotFound && hasPicks}
		<!-- "Fresh picks daily" divider -->
		<div class="mx-auto my-12 flex max-w-md items-center gap-4 text-muted">
			<span class="h-px flex-1 bg-gold/30"></span>
			<span class="eyebrow whitespace-nowrap">
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
	<!-- The shared cover: real artwork when there is any, the house
							     plate otherwise. This page used to draw its own gradient
							     fallback, so a cover-less book looked different here than
							     everywhere else. -->
							<div class="transition-transform group-hover:-translate-y-1">
								<BookCover {book} />
							</div>
							<div class="mt-2">
								<div class="text-small font-medium text-text">{book.title}</div>
								<div class="text-small text-muted">{book.author.name}</div>
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
						<div data-testid="notfound-sermon"><SermonCard {sermon} showAuthor /></div>
					{/each}
				</div>
			</section>
		{/if}
	{/if}
</div>
