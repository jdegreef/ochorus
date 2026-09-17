<script lang="ts">
	import type { Quote } from '$lib/library-public';
	import { quoteHref } from '$lib/library-public';
	import { SITE_URL } from '$lib/config';
	import FavoriteButton from '$lib/components/FavoriteButton.svelte';
	import { i18n } from '$lib/i18n.svelte';

	const t = i18n.t;

	// One quotation card: the sentence, the citation that sources it (a link to
	// the exact paragraph), and a copy button that takes the attribution WITH it.
	// Shared by the author page and the theme pages so the card never drifts.
	// `cite` is passed in because it differs by context: on the author page the
	// work is the group heading, so the card need not repeat it; on a theme page
	// the works are mixed, so the citation names the work (see citeLine).
	let {
		quote,
		authorName,
		cite
	}: { quote: Quote; authorName: string; cite: string } = $props();

	// "Work" or "Work, chapter N" — the source line as prose. Shared by the copy
	// text and the shareable card so the two attributions never drift, the same
	// reason the card component itself is shared (see header). A plain function,
	// not `$derived`: it is only ever read inside a click handler, never in the
	// template, so there is nothing to react to. `clipChapter` already carries
	// its own leading ", ".
	const sourceLine = () =>
		quote.source.work +
		(quote.source.order === null
			? ''
			: t('quotes.clipChapter').replace('%n%', String(quote.source.order)));

	let copied = $state(false);
	let timer: ReturnType<typeof setTimeout>;
	async function copy() {
		// Copy the quotation WITH its citation. The attribution travelling with
		// the text is the whole point — stripping it is how the aggregators ended
		// up publishing these words under nobody's name.
		const cited = `"${quote.text}"\n— ${authorName}, ${sourceLine()}\n${SITE_URL}${quoteHref(quote)}`;
		try {
			await navigator.clipboard.writeText(cited);
			copied = true;
			clearTimeout(timer);
			timer = setTimeout(() => (copied = false), 2000);
		} catch {
			// A denied clipboard permission is not worth an error state; the text
			// is on the page and selectable either way.
		}
	}

	// The reader turns a highlighted line into a branded PNG (see SelectionBar);
	// a quotation on this page is the same shareable unit, so it gets the same
	// action. The renderer is pure canvas that also inlines the brand mark, so
	// it is imported on first tap rather than at module load — it has no place in
	// the initial bundle of a page that is mostly read. `cardBusy` guards the
	// gap while it loads and rasterizes. Quotes are English-only, so `language`
	// is left to its Latin default.
	let cardBusy = $state(false);
	async function quoteCard() {
		if (cardBusy) return;
		cardBusy = true;
		try {
			const { shareQuoteCard } = await import('$lib/quoteCard');
			await shareQuoteCard({
				quote: quote.text,
				author: authorName,
				source: sourceLine(),
				site: 'ochorus.com'
			});
		} catch {
			// Rendering or sharing failed (or the user dismissed the sheet) — the
			// quotation is still on the page, so there is nothing to surface.
		} finally {
			cardBusy = false;
		}
	}
</script>

<li class="quote">
	<blockquote>{quote.text}</blockquote>
	<div class="foot">
		<!-- The citation IS the product: an unsourced card is what the aggregators
		     already publish. It links to the paragraph, not just the chapter,
		     using the reader's own `?p=` jump. -->
		<a class="cite eyebrow" href={quoteHref(quote)}>{cite}</a>
		<div class="actions">
			<!-- Save this line to "My Library". A quote is favorited by its own
			     permanent slug, so the saved-quotes shelf can resolve it back to
			     this same card (see resolveQuotes). -->
			<FavoriteButton kind="quote" slug={quote.slug} />
			<!-- Text, not a glyph: the icon set has no copy mark, and extending a
			     curated set for a minor affordance is not worth it. -->
			<button class="act" onclick={copy}>{copied ? t('quotes.copied') : t('quotes.copy')}</button>
			<!-- The same "Quote card" the reader offers on a highlight: a branded
			     PNG with the line and its source, built to leave the site. Reuses the
			     reader's label so the one action reads the same in both places. -->
			<button class="act" onclick={quoteCard} disabled={cardBusy} aria-busy={cardBusy}
				>{t('reader.quoteCard')}</button
			>
		</div>
	</div>
</li>

<style>
	.quote {
		padding: 1.1rem 1.3rem;
		border: 1px solid var(--color-border);
		border-radius: var(--radius-card);
		background: var(--color-surface);
	}
	.quote blockquote {
		margin: 0;
		font-family: var(--font-display, Georgia, serif);
		/* A step up from body: this is the content of the card. A token from the
		   scale, not an invented size (STYLE_GUIDE §2). */
		font-size: var(--fs-h3);
		/* Looser than the 1.3 the scale gives --fs-h3, because that leading is for
		   headings and this is reading prose. */
		line-height: 1.45;
		color: var(--color-text);
	}
	.foot {
		display: flex;
		align-items: center;
		justify-content: space-between;
		gap: 1rem;
		margin-top: 0.7rem;
	}
	.actions {
		display: inline-flex;
		align-items: center;
		gap: 0.5rem;
	}
	.cite {
		color: var(--color-muted);
		text-decoration: none;
	}
	.cite:hover {
		color: var(--color-accent);
		text-decoration: underline;
	}
	/* Quiet until wanted: the quotation is the content, these are affordances.
	   Shared by Copy and Quote card so the row reads as one set of controls. */
	.act {
		display: inline-flex;
		align-items: center;
		gap: 0.3rem;
		padding: 0.2rem 0.5rem;
		border: 0;
		border-radius: var(--radius-sm);
		background: transparent;
		font-size: var(--fs-small);
		color: var(--color-muted);
		cursor: pointer;
	}
	.act:hover {
		background: var(--color-surface-2);
		color: var(--color-text);
	}
	.act:disabled {
		cursor: default;
	}
	/* A button disabled only to block a second tap while it works must still read
	   as working, not greyed-out — it marks itself `aria-busy`, so only an inertly
	   disabled button fades. Mirrors the `.btn` pattern in app.css (STYLE_GUIDE §6). */
	.act:disabled:not([aria-busy='true']) {
		opacity: 0.6;
	}
</style>
