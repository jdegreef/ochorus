<script lang="ts">
	import { onMount } from 'svelte';
	import { i18n } from '$lib/i18n.svelte';
	import { localizeHref } from '$lib/href';
	import { SITE_URL } from '$lib/config';
	import { isLocale } from '$lib/paraglide/runtime';
	import { bookChapterPath } from '$lib/reading-schema';
	import { authorPath } from '$lib/originals';
	import { favorites } from '$lib/favorites.svelte';
	import { track } from '$lib/analytics';
	import { getBook, type BookDetail } from '$lib/library-public';
	import { GIFT_OPENED_EVENT, giftFromHash, type Gift } from '$lib/gift';
	import BookCover from '$lib/components/BookCover.svelte';

	/**
	 * A gift link's landing page: "A gift from <name>", the book, the giver's
	 * note and one button — "Open your gift" — which saves the book to the
	 * reader's device-local library (favorites: no account needed) and starts
	 * chapter 1. Modelled on the welcome page's start card.
	 *
	 * Everything in the link is untrusted ($lib/gift): the name and note are
	 * re-cleaned on decode and rendered as text only (never as raw HTML), framed as
	 * the sender's words rather than Ochorus's, and kept out of <title> and
	 * every meta tag. The book is checked against the API in the link's own
	 * language — no English fallback (CLAUDE.md) — and a link that doesn't
	 * resolve gets a quiet "couldn't be opened" with the way into the library.
	 */
	const t = i18n.t;

	let gift = $state<Gift | null>(null);
	let book = $state<BookDetail | null>(null);
	let loaded = $state(false);

	// The fragment is taken off the address bar once read: Plausible's script
	// reports `location.href`, fragment included, with every pageview and
	// event, and the note must not leave the device that way. The tab keeps
	// it (sessionStorage) so a reload still opens the gift.
	const KEPT = 'ochorus:gift';
	let request = 0;

	function readGift(): Gift | null {
		const fromHash = giftFromHash(window.location.hash);
		if (fromHash) {
			try {
				sessionStorage.setItem(KEPT, window.location.hash);
			} catch {
				// Storage blocked: a reload just won't find the gift again.
			}
			history.replaceState(history.state, '', window.location.pathname + window.location.search);
			return fromHash;
		}
		try {
			return giftFromHash(sessionStorage.getItem(KEPT) ?? '');
		} catch {
			return null;
		}
	}

	function load() {
		// A gift opened over this one (hashchange) wins, whichever fetch lands last.
		const mine = ++request;
		const g = readGift();
		gift = g;
		book = null;
		loaded = false;
		if (!g) {
			loaded = true;
			return;
		}
		getBook(g.slug, g.lang)
			// getBook falls back to English on a 404: only the gift's own edition counts.
			.then((b) => (b.language === g.lang && b.chapters.length ? b : null))
			.catch(() => null)
			.then((b) => {
				if (mine !== request) return;
				book = b;
				loaded = true;
				if (b) track(GIFT_OPENED_EVENT, { language: g.lang, step: 'viewed' });
			});
	}

	onMount(() => {
		load();
		window.addEventListener('hashchange', load);
		return () => window.removeEventListener('hashchange', load);
	});

	/** In the gift's language, whatever the reader's interface language. */
	const inLang = (path: string) =>
		gift && isLocale(gift.lang) ? localizeHref(path, { locale: gift.lang }) : localizeHref(path);
	const firstChapter = $derived(
		book ? inLang(bookChapterPath(book.slug, book.chapters[0].order, false)) : null
	);
	// The book page is the one indexable address for this book.
	const canonical = $derived(book ? `${SITE_URL}${inLang(`/books/${book.slug}`)}` : null);
	/** A message around the giver's name, split so the name can sit in its
	 *  own <bdi>: an Arabic name in a Japanese line (or a name ending in
	 *  digits in an Arabic one) can't reorder the words around it. */
	const around = (key: string): [string, string] => {
		const [before, after = ''] = t(key).split('%name%');
		return [before, after];
	};
	const fromLine = $derived(gift?.name ? around('gift.from') : null);
	const noteHeading = $derived(gift?.name ? around('gift.noteHeading') : null);

	function openGift() {
		if (!book || !gift) return;
		if (!favorites.has('book', book.slug)) favorites.toggle('book', book.slug);
		track(GIFT_OPENED_EVENT, { language: gift.lang, step: 'opened' });
	}
</script>

<svelte:head>
	<!-- The book's title only: never the giver's name or note, which anyone
	     could have written into the link. -->
	<title>{book ? `${t('gift.pageTitle')}: ${book.title}` : t('gift.pageTitle')} — Ochorus</title>
	<meta name="robots" content="noindex" />
	{#if canonical}<link rel="canonical" href={canonical} />{/if}
</svelte:head>

<div class="page-col px-5 py-10">
	<section class="gift rounded-card border border-border bg-surface" aria-labelledby="gift-title">
		{#if book && gift && firstChapter}
			<div class="gift-cover" aria-hidden="true"><BookCover {book} /></div>
			<div class="min-w-0">
				<p class="eyebrow text-gold">
					{#if fromLine}{fromLine[0]}<bdi>{gift.name}</bdi>{fromLine[1]}{:else}{t('gift.forYou')}{/if}
				</p>
				<h1 id="gift-title" class="font-display mt-1 text-h2" lang={book.language}>{book.title}</h1>
				<p class="text-small text-muted">
					<a href={inLang(authorPath(book.author.slug))}>{book.author.name}</a>
					· {t('gift.chapters').replace('%n%', String(book.chapters.length))}
				</p>
			</div>
			{#if gift.note}
				<figure class="gift-note">
					<figcaption class="text-small text-muted">
						{#if noteHeading}{noteHeading[0]}<bdi>{gift.name}</bdi>{noteHeading[1]}{:else}{t(
								'gift.noteHeadingAnon'
							)}{/if}
					</figcaption>
					<!-- Plain text only: untrusted, from the link ($lib/gift). -->
					<blockquote class="note font-display text-body" dir="auto">{gift.note}</blockquote>
					<p class="text-small text-muted">{t('gift.noteDisclaimer')}</p>
				</figure>
			{/if}
			<div class="gift-cta">
				<span class="text-small text-muted">{t('gift.free')}</span>
				<a class="btn btn-primary hover:no-underline" href={firstChapter} onclick={openGift}>
					{t('gift.open')}
				</a>
				<p class="w-full text-small text-muted">{t('gift.saves')}</p>
			</div>
		{:else if loaded}
			<div class="gift-wide min-w-0">
				<h1 id="gift-title" class="font-display text-h2">{t('gift.missingTitle')}</h1>
				<p class="mt-1 text-body text-muted">{t('gift.missingBody')}</p>
				<a class="btn btn-primary mt-4 hover:no-underline" href={localizeHref('/books')}>
					{t('home.browseLibrary')}
				</a>
			</div>
		{:else}
			<div class="gift-cover skeleton" aria-hidden="true"></div>
			<h1 id="gift-title" class="sr-only">{t('gift.pageTitle')}</h1>
		{/if}
	</section>
</div>

<style>
	.gift {
		display: grid;
		grid-template-columns: 5.5rem minmax(0, 1fr);
		gap: 1.25rem;
		align-items: start;
		max-width: 40rem;
		margin-inline: auto;
		padding: 1.25rem;
	}
	@media (min-width: 640px) {
		.gift {
			grid-template-columns: 9rem minmax(0, 1fr);
			gap: 1.5rem;
			padding: 1.5rem;
		}
	}
	.gift-wide,
	.gift-note,
	.gift-cta {
		grid-column: 1 / -1;
	}
	.gift-cover.skeleton {
		aspect-ratio: 2 / 3;
		border-radius: var(--radius-card);
	}
	.gift-note {
		margin: 0;
	}
	/* The giver's words, set apart as a handwritten-feeling letter: italic
	   display face on a gold rule, line breaks kept, long words wrapped. */
	.note {
		margin: 0.35rem 0 0.5rem;
		padding-inline-start: 0.9rem;
		border-inline-start: 2px solid var(--gold);
		font-style: italic;
		white-space: pre-line;
		overflow-wrap: anywhere;
	}
	.gift-cta {
		display: flex;
		flex-wrap: wrap;
		align-items: center;
		justify-content: space-between;
		gap: 0.5rem 1rem;
		padding-top: 1rem;
		border-top: 1px solid var(--border);
	}
</style>
