<script lang="ts">
	import type { Quote, QuotePage } from '$lib/library-public';
	import { groupQuotes, quoteHref, workHref } from '$lib/library-public';
	import { SITE_URL } from '$lib/config';
	import { hueForBirthYear } from '$lib/eras';
	import { jsonLd, breadcrumb, hreflangFor, absUrl } from '$lib/seo';
	import Seo from '$lib/components/Seo.svelte';
	import Breadcrumb from '$lib/components/Breadcrumb.svelte';

	// English-only, and written in English literals for the same reason the
	// scripture pages are: these quotations are lifted from the English works and
	// every citation names an English chapter, so there is no translated version
	// to serve.
	let { data } = $props();
	const page = $derived<QuotePage>(data.page);

	// Grouped by work, which is what earns the colour: the house rule is that a
	// list's hue tracks whatever it is grouped by (STYLE_GUIDE §5), so the
	// ungrouped list this replaced had no claim to one. The API sends the
	// quotations in reading order, so grouping is a scan, not a sort.
	const eraHue = $derived(hueForBirthYear(page.author.birth_year));
	const groups = $derived(groupQuotes(page, eraHue));

	const path = $derived(`/quotes/${page.author.slug}/`);
	const canonical = $derived(`${SITE_URL}${path}`);
	const hreflang = $derived(hreflangFor(path, ['en']));

	const title = $derived(`${page.author.name} — quotes, with sources — Ochorus`);
	const description = $derived(
		`${page.quotes.length} quotations from ${page.author.name}, each one traced to the ` +
			'book, chapter and paragraph it comes from — and linked to the full text, free to read.'
	);

	// Home › Quotes › Author: the page is a child of the quotes index, not of the
	// author's bio. This also gives the index an inbound link from every author
	// page, which is what makes /quotes a hub rather than a dead end.
	const crumbs = $derived([
		{ name: 'Home', href: '/' },
		{ name: 'Quotes', href: '/quotes/' },
		{ name: page.author.name, href: path }
	]);
	const crumbsLd = $derived(
		jsonLd(breadcrumb(crumbs.map((c) => ({ name: c.name, url: c.href }))))
	);

	// Share card: the author's own portrait when we have one, so a shared quote
	// page wears the face it is about; otherwise the branded /quotes section card
	// (the sixteen image-less pages the topic/plan detail pages already fall back
	// on). Both go through absUrl so the og:image is an absolute URL.
	const ogImage = $derived(
		page.author.photo_url ? absUrl(page.author.photo_url) : absUrl('/og/quotes.png')
	);

	// One @id per author, shared with the /authors bio page's Person node (which
	// carries the same url): that is what lets a crawler fuse "the person quoted
	// here" with "the person whose life is here" into one entity. `creator`, not
	// `spokenByCharacter` — the latter is for a fictional character speaking a
	// line, whereas these are the writer's own words.
	const authorUrl = $derived(`${SITE_URL}/authors/${page.author.slug}/`);
	const person = $derived({
		'@type': 'Person',
		'@id': authorUrl,
		name: page.author.name,
		url: authorUrl
	});
	// An ItemList, not CollectionPage.hasPart: the quotations arrive in reading
	// order and the ListItem positions preserve it, where hasPart is an unordered
	// set. `about` names the whole collection's subject as the author entity.
	const quotesLd = $derived(
		jsonLd({
			'@context': 'https://schema.org',
			'@type': 'CollectionPage',
			name: `Quotations from ${page.author.name}`,
			description,
			url: canonical,
			about: person,
			mainEntity: {
				'@type': 'ItemList',
				numberOfItems: page.quotes.length,
				itemListElement: page.quotes.map((q, i) => ({
					'@type': 'ListItem',
					position: i + 1,
					item: {
						'@type': 'Quotation',
						text: q.text,
						creator: { '@id': authorUrl },
						isPartOf: {
							'@type': q.source.kind === 'sermon' ? 'CreativeWork' : 'Book',
							name: q.source.work,
							url: absUrl(workHref(q))
						},
						url: `${SITE_URL}${quoteHref(q)}`
					}
				}))
			}
		})
	);

	/** Inside a book group the work is the heading, so the card need not repeat
	 *  it. The sermons group is mixed, so there the sermon names itself. */
	const cite = (q: Quote) =>
		q.source.kind === 'sermon'
			? `${q.source.work} ¶${q.paragraph}`
			: `Chapter ${q.source.order} ¶${q.paragraph}`;

	// Copy the quotation WITH its citation. The attribution travelling with the
	// text is the whole point of this page — stripping it is how the aggregators
	// ended up publishing Spurgeon's words under nobody's name.
	let copied = $state('');
	let timer: ReturnType<typeof setTimeout>;
	async function copy(q: Quote) {
		const cited = `"${q.text}"\n— ${page.author.name}, ${q.source.work}` +
			(q.source.order === null ? '' : `, chapter ${q.source.order}`) +
			`\n${SITE_URL}${quoteHref(q)}`;
		try {
			await navigator.clipboard.writeText(cited);
			copied = q.slug;
			clearTimeout(timer);
			timer = setTimeout(() => (copied = ''), 2000);
		} catch {
			// A denied clipboard permission is not worth an error state; the text
			// is on the page and selectable either way.
		}
	}
</script>

<Seo {title} {description} {canonical} {hreflang} {ogImage} structuredData={[crumbsLd, quotesLd]} />

<!-- max-w-2xl is 42rem — the measure STYLE_GUIDE §2 calls normal, and the
     reason is on this page: at 48rem a quotation ran about 95 characters to
     the line, well past the 45-75 an eye tracks comfortably. Narrowing it and
     setting the quotation a step larger (below) lands at roughly 67. -->
<div class="page-col px-5 py-10">
	<Breadcrumb items={crumbs} />

	<header class="mb-6">
		<h1 class="text-h1">{page.author.name} — in their own words</h1>
		<p class="mt-2 max-w-2xl text-small text-muted">
			{page.quotes.length} quotations, each traced to the exact paragraph it comes from. Follow
			any of them into the full text — free, and without an account.
		</p>
	</header>

	<!-- Jump row: sixty cards is a long scroll, and the works are the one
	     structure a reader can predict. Same pattern as /scripture. -->
	{#if groups.length > 1}
		<nav class="jump" aria-label="Jump to a work">
			{#each groups as g (g.id)}
				<a href={`#${g.id}`} style={`--hue: ${g.hue}`}>{g.work}</a>
			{/each}
		</nav>
	{/if}

	{#each groups as g (g.id)}
		<section class="group" id={g.id} style={`--hue: ${g.hue}`}>
			<h2 class="work">
				{#if g.slug}
					<a href={`/books/${g.slug}/`}>{g.work}</a>
				{:else}
					{g.work}
				{/if}
				<span class="count">{g.quotes.length}</span>
			</h2>

			<ol class="quotes">
				{#each g.quotes as q (q.slug)}
					<li class="quote">
						<blockquote>{q.text}</blockquote>
						<div class="foot">
							<!-- The citation IS the product: an unsourced card is what the
							     aggregators already publish. It links to the paragraph, not
							     just the chapter, using the reader's own `?p=` jump. -->
							<a class="cite eyebrow" href={quoteHref(q)}>{cite(q)}</a>
							<!-- Text, not a glyph: the icon set has no copy mark, and
							     extending a curated set for a minor affordance is not
							     worth it when the word says it exactly. -->
							<button class="copy" onclick={() => copy(q)}>
								{copied === q.slug ? 'Copied' : 'Copy'}
							</button>
						</div>
					</li>
				{/each}
			</ol>
		</section>
	{/each}
</div>

<style>
	/* Every use of --hue goes through color-mix(), never as body text, so
	   contrast holds in both themes (STYLE_GUIDE §5). */
	.jump {
		display: flex;
		flex-wrap: wrap;
		gap: 0.4rem;
		margin-bottom: 2rem;
	}
	.jump a {
		padding: 0.25rem 0.7rem;
		border-radius: 999px;
		border: 1px solid color-mix(in srgb, var(--hue) 30%, var(--color-border));
		background: color-mix(in srgb, var(--hue) 8%, var(--color-surface));
		font-size: var(--fs-small);
		color: var(--color-text);
		text-decoration: none;
	}
	.jump a:hover {
		background: color-mix(in srgb, var(--hue) 16%, var(--color-surface));
	}

	.group {
		margin-bottom: 2.5rem;
		scroll-margin-top: 5rem;
	}
	.work {
		display: flex;
		align-items: baseline;
		gap: 0.6rem;
		margin: 0 0 0.9rem;
		padding-inline-start: 0.7rem;
		border-inline-start: 3px solid color-mix(in srgb, var(--hue) 55%, var(--color-border));
		font-size: var(--fs-h3);
		font-weight: 600;
	}
	.work a {
		color: inherit;
		text-decoration: none;
	}
	.work a:hover {
		text-decoration: underline;
	}
	.count {
		font-size: var(--fs-small);
		font-weight: 400;
		font-variant-numeric: tabular-nums;
		color: var(--color-muted);
	}

	.quotes {
		list-style: none;
		margin: 0;
		padding: 0;
		display: grid;
		gap: 0.75rem;
	}
	.quote {
		padding: 1.1rem 1.3rem;
		border: 1px solid var(--color-border);
		border-radius: var(--radius-card);
		/* No hue wash. At 4% it was invisible against the surface, and the
		   heading's rule (55%) and the jump chip (8%) already carry the group's
		   colour — a tint nobody can see is dead CSS, not design. */
		background: var(--color-surface);
	}
	.quote blockquote {
		margin: 0;
		font-family: var(--font-display, Georgia, serif);
		/* A step up from body: this is the content of the card, and at body size
		   it was the smallest type on a page whose h1 is 1.953rem. A token from
		   the scale, not an invented size (STYLE_GUIDE §2). */
		font-size: var(--fs-h3);
		/* Looser than the 1.3 the scale gives --fs-h3, because that leading is
		   for headings and this is reading prose. */
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
		border-radius: var(--radius-chip, 0.4rem);
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
