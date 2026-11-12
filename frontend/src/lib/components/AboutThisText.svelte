<script lang="ts">
	import { isTranslated, type BookDetail } from '$lib/library-public';
	import { contentLang } from '$lib/reading';
	import { i18n } from '$lib/i18n.svelte';
	import { localizeHref } from '$lib/href';
	import { getLang } from '$lib/lang.svelte';

	/**
	 * "About this text" — where this edition came from, at the book page's foot,
	 * in the place of the source line and the cover credit it replaced.
	 *
	 * Only what the API already records, and a row only where there is a value:
	 * the edition's own rights-and-source note (`attribution`) with a link to the
	 * text it was taken from, the English edition a translation was made from,
	 * the painter of the cover, the day the edition was last updated, and the
	 * rights decision `library/rights` makes for the JSON-LD (never a licence of
	 * our own invention — the Terms say what Ochorus offers its editions under).
	 * That last row always has its Terms link, so the panel is never empty.
	 *
	 * The translation row says only THAT an edition is a translation, as the
	 * old source line did. The review state stays admin-only (CLAUDE.md): both
	 * translated source types read the same here.
	 */
	let { book }: { book: BookDetail } = $props();
	const t = i18n.t;

	const host = $derived.by(() => {
		try {
			return book.source_url ? new URL(book.source_url).hostname.replace(/^www\./, '') : '';
		} catch {
			return '';
		}
	});
	const note = $derived((book.attribution ?? '').trim());
	// A translated edition (not the Modern English one, which is the original's
	// own toggle) whose English edition is published to be linked to.
	const fromEnglish = $derived(
		isTranslated(book.source_type) &&
			!book.is_modern_edition &&
			book.language !== 'en' &&
			book.available_languages.includes('en')
	);
	const updated = $derived.by(() => {
		const d = book.updated_at ? new Date(book.updated_at) : null;
		if (!d || Number.isNaN(d.getTime())) return '';
		return new Intl.DateTimeFormat(getLang(), { day: 'numeric', month: 'long', year: 'numeric' }).format(d);
	});
</script>

<section class="mt-12" aria-labelledby="about-text-heading">
	<h2 id="about-text-heading" class="section-heading no-rule">{t('book.aboutText')}</h2>
	<dl class="about-text text-small">
		{#if note || host}
			<dt>{t('book.aboutTextSource')}</dt>
			<dd>
				{#if note}<span lang={contentLang(book.language)} dir="auto">{note}</span>{/if}{#if note && host}{' '}{/if}{#if host}<a
						href={book.source_url}
						target="_blank"
						rel="noreferrer">{host}</a
					>{/if}
			</dd>
		{/if}
		{#if fromEnglish}
			<dt>{t('book.aboutTextTranslation')}</dt>
			<dd><a href="/books/{book.slug}/" hreflang="en">{t('book.aboutTextFromEnglish')}</a></dd>
		{/if}
		{#if book.artwork_credit}
			<!-- The painter, for the covers that wear a real painting. The art is
			     open access (CC0), so the credit isn't owed — it is simply right.
			     Not translated: a name, a title and a year. -->
			<dt>{t('book.aboutTextCover')}</dt>
			<dd>{book.artwork_credit}</dd>
		{/if}
		{#if updated}
			<dt>{t('book.aboutTextUpdated')}</dt>
			<dd>{updated}</dd>
		{/if}
		<dt>{t('book.aboutTextRights')}</dt>
		<dd>
			{#if book.public_domain}{t('book.aboutTextPublicDomain')}{' '}{/if}<a href="{localizeHref('/legal')}#terms"
				>{t('legal.termsHeading')}</a
			>
		</dd>
	</dl>
</section>

<style>
	/* Label beside value from sm, stacked on a phone; the muted foot register
	   the source line had, at the prose measure. */
	.about-text {
		display: grid;
		grid-template-columns: minmax(0, 1fr);
		max-width: 65ch;
		color: var(--muted);
	}
	.about-text dt {
		margin-top: 0.75rem;
		font-weight: 600;
		color: var(--text);
	}
	.about-text dd {
		margin-top: 0.125rem;
	}
	@media (min-width: 640px) {
		.about-text {
			grid-template-columns: 9rem minmax(0, 1fr);
			column-gap: 1.25rem;
		}
		.about-text dt,
		.about-text dd {
			margin-top: 0;
			padding-block: 0.5rem;
			border-top: 1px solid var(--border);
		}
	}
</style>
