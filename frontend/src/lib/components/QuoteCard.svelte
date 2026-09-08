<script lang="ts">
	import type { Quote } from '$lib/library-public';
	import { quoteHref } from '$lib/library-public';
	import { SITE_URL } from '$lib/config';
	import FavoriteButton from '$lib/components/FavoriteButton.svelte';

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

	let copied = $state(false);
	let timer: ReturnType<typeof setTimeout>;
	async function copy() {
		// Copy the quotation WITH its citation. The attribution travelling with
		// the text is the whole point — stripping it is how the aggregators ended
		// up publishing these words under nobody's name.
		const cited =
			`"${quote.text}"\n— ${authorName}, ${quote.source.work}` +
			(quote.source.order === null ? '' : `, chapter ${quote.source.order}`) +
			`\n${SITE_URL}${quoteHref(quote)}`;
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
			<button class="copy" onclick={copy}>{copied ? 'Copied' : 'Copy'}</button>
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
	/* Quiet until wanted: the quotation is the content, this is an affordance. */
	.copy {
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
	.copy:hover {
		background: var(--color-surface-2);
		color: var(--color-text);
	}
</style>
