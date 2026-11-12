<script lang="ts">
	import { toBookTile, type BookSummary, type SeriesDetail } from '$lib/library-public';
	import { SITE_URL } from '$lib/config';
	import { jsonLd, breadcrumbLd, absUrl } from '$lib/seo';
	import { localizeHref } from '$lib/href';
	import { i18n } from '$lib/i18n.svelte';
	import { BIBLE_PATH, BIBLE_SERIES } from '$lib/bible';
	import {
		OWB_FAN,
		OWB_LANGUAGES,
		OWB_LEVELS,
		OWB_PATH,
		OWB_READ_URL,
		OWB_URL
	} from '$lib/openWordBible';
	import Seo from '$lib/components/Seo.svelte';
	import CoverStrip from '$lib/components/CoverStrip.svelte';
	import Arrow from '$lib/components/Arrow.svelte';

	/**
	 * The Open Word Bible: what the translation is, how it is made, and where
	 * to find all of it (OpenWordBible.org). The page the Bible's byline links
	 * to, in place of an author page — the translation has no biography.
	 *
	 * Its prose is English on purpose, not chrome left untranslated: the page,
	 * like the Bible it describes, exists only in BIBLE_LOCALES (the loader 404s
	 * elsewhere), so it moves into a language's catalogue when that language's
	 * Bible ships. The sample verse and decision are the translation's own
	 * (John 3:16, record JHN.3.16.s1), not paraphrase.
	 */
	let { data } = $props();
	const series = $derived<SeriesDetail | null>(data.series);
	const t = i18n.t;

	const books = $derived(series?.books ?? []);
	const fan = $derived.by(() => {
		const bySlug = new Map(books.map((b) => [b.slug, b]));
		return OWB_FAN.map((s) => bySlug.get(s)).filter((b): b is BookSummary => !!b);
	});

	// John 3:16 at each level, the reader settings at their defaults.
	const SAMPLE: Record<(typeof OWB_LEVELS)[number]['code'], string> = {
		'OWB-L':
			'For in this way God loved the world, that he gave the Son, the one and only, in order that everyone who believes in him may not perish but may have eternal life.',
		'OWB-B':
			"For God's love for the world was such that he gave his one and only Son, so that everyone who believes in him may not perish but have eternal life.",
		'OWB-R':
			'God loved the people of the world, and this is how he loved them: he gave his one and only Son, so that everyone who believes in him will not be lost but will have eternal life.'
	};

	const path = `${OWB_PATH}/`;
	const canonical = `${SITE_URL}${localizeHref(path)}`;
	const title = 'The Open Word Bible — Ochorus';
	const description =
		'The Open Word Bible is a new, free translation of the Bible from Hebrew and Greek, at three levels, with every decision explained. Ochorus prints its Balanced text.';
	const crumbsLd = breadcrumbLd([
		{ name: t('common.home'), href: '/' },
		{ name: t('nav.bible'), href: `${BIBLE_PATH}/` },
		{ name: 'Open Word Bible', href: path }
	]);
	// The translation as a CreativeWork in its own right, with its home and its
	// licence; the books here are its parts.
	const workLd = $derived(
		jsonLd({
			'@context': 'https://schema.org',
			'@type': 'CreativeWork',
			name: 'Open Word Bible',
			alternateName: 'OWB',
			url: OWB_URL,
			sameAs: OWB_URL,
			license: 'https://creativecommons.org/publicdomain/zero/1.0/',
			inLanguage: 'en',
			description,
			mainEntityOfPage: canonical,
			hasPart: books.map((b) => ({
				'@type': 'Book',
				name: b.title,
				url: absUrl(localizeHref(`/books/${b.slug}`))
			}))
		})
	);
</script>

<Seo
	{title}
	{description}
	{canonical}
	hreflang={null}
	ogImage={`${SITE_URL}/og/bible.png`}
	structuredData={[crumbsLd, workLd]}
/>

<div class="page-col px-5 py-10">
	<!-- Hero: the name, what it is in a sentence, the two ways in. -->
	<section class="hero">
		<div>
			<p class="eyebrow text-gold">The translation</p>
			<h1 class="mt-2 text-balance font-display text-h1 font-semibold leading-tight">
				The Open Word Bible
			</h1>
			<p class="lede mt-4 text-muted">
				A new translation of the Bible from the Hebrew and Greek, in today's English. Every
				sentence is translated three ways, from word-for-word to plain, and every choice the
				translators made is written down with its reason, so you can see why it reads as it does.
				It is free for anyone to read, copy and share.
			</p>
			<p class="facts mt-5 text-small text-muted">
				{#if books.length}
					<span>{books.length} {books.length === 1 ? t('common.bookOne') : t('common.bookMany')} on Ochorus</span>
					<span class="sep" aria-hidden="true">·</span>
				{/if}
				<span>Hebrew &amp; Greek</span>
				<span class="sep" aria-hidden="true">·</span>
				<span>Public domain (CC0)</span>
			</p>
			<div class="mt-6 flex flex-wrap gap-3">
				<a class="btn btn-primary" href={localizeHref(`${BIBLE_PATH}/`)}>Read the Bible <Arrow /></a>
				<a class="btn btn-ghost" href={OWB_URL} rel="external noopener">
					Visit OpenWordBible.org <span aria-hidden="true">↗</span>
				</a>
			</div>
		</div>
		{#if fan.length >= 3}
			<div class="fan">
				<CoverStrip covers={fan.map(toBookTile)} size="fan" priority />
			</div>
		{/if}
	</section>

	<!-- Three levels: one verse, side by side, the Ochorus one marked. -->
	<section class="mt-12" aria-labelledby="levels-heading">
		<p class="eyebrow text-gold">Three levels</p>
		<h2 id="levels-heading" class="mt-1 text-h2 font-display font-semibold">
			One verse, translated three ways
		</h2>
		<p class="mt-2 max-w-prose text-small text-muted">
			Translations usually pick one point between word-for-word and thought-for-thought. The Open
			Word Bible gives you three, side by side. Here is John 3:16.
		</p>
		<ol class="levels mt-6">
			{#each OWB_LEVELS as level (level.code)}
				{@const ours = level.code === 'OWB-B'}
				<li class="level" class:ours>
					<div class="flex items-baseline justify-between gap-3">
						<h3 class="font-display text-h3 font-semibold">{level.name}</h3>
						<span class="code">{level.code}</span>
					</div>
					<blockquote class="verse mt-3 font-display">{SAMPLE[level.code]}</blockquote>
					<p class="mt-3 text-small text-muted">{level.aim}</p>
					{#if ours}
						<p class="badge mt-3">On Ochorus</p>
					{/if}
				</li>
			{/each}
		</ol>
	</section>

	<!-- The reasoning record: one real decision, as the translation keeps it. -->
	<section class="working mt-14" aria-labelledby="working-heading">
		<div>
			<p class="eyebrow text-gold">Open reasoning</p>
			<h2 id="working-heading" class="mt-1 text-h2 font-display font-semibold">
				Every sentence shows its working
			</h2>
			<p class="mt-3 text-small text-muted">
				Behind each sentence is a record: the original words, a literal gloss, the three
				translations, and every decision the translators made, with the options they set aside
				and the reason for their choice. Where a reading is uncertain, the record says so.
			</p>
			<p class="mt-3 text-small text-muted">
				On OpenWordBible.org you can open any verse and read its record, compare the three
				levels, and follow the cross-references in the margin.
			</p>
			<a class="mt-4 inline-block text-small font-semibold text-accent" href={OWB_READ_URL} rel="external noopener">
				Read with the reasoning on OpenWordBible.org <span aria-hidden="true">↗</span>
			</a>
		</div>
		<figure class="record">
			<figcaption class="eyebrow text-muted">John 3:16 · a decision</figcaption>
			<p class="mt-3">
				<span class="greek" lang="grc">Οὕτως</span>
				<span class="text-small text-muted">houtōs</span>
			</p>
			<dl class="mt-3 text-small">
				<div>
					<dt>Chosen</dt>
					<dd>“in this way”: God’s love took the form of giving the Son</dd>
				</div>
				<div>
					<dt>Set aside</dt>
					<dd>“so much”: God loved the world to such a degree</dd>
				</div>
				<div>
					<dt>Why</dt>
					<dd>
						In John the word normally means “thus, in this way”, and it has just been used in
						3:14: “so must the Son of Man be lifted up”. This is how God loved the world: by
						giving the Son.
					</dd>
				</div>
			</dl>
		</figure>
	</section>

	<!-- Sources and freedom, as two quiet panels. -->
	<section class="facts-grid mt-14">
		<div class="panel">
			<p class="eyebrow text-gold">From the original languages</p>
			<h2 class="mt-1 text-h3 font-display font-semibold">Translated from the source texts</h2>
			<ul class="mt-3 space-y-2 text-small text-muted">
				<li>
					<strong class="text-text">Old Testament:</strong> the Westminster Leningrad Codex, with
					the MACULA Hebrew word data, numbered as in the Hebrew.
				</li>
				<li>
					<strong class="text-text">New Testament:</strong> the SBL Greek New Testament, whose
					sentences and paragraphs the translation follows.
				</li>
				<li>
					No Hebrew or Greek is typed by hand: every original word is loaded from the source
					data, and checked against it.
				</li>
			</ul>
		</div>
		<div class="panel">
			<p class="eyebrow text-gold">Free for everyone</p>
			<h2 class="mt-1 text-h3 font-display font-semibold">Given to the public domain</h2>
			<p class="mt-3 text-small text-muted">
				The translation is released under CC0: no permission to ask, no fee, no limit on
				copies. Print it, quote it at length, put it in an app or a church bulletin. That is
				why it can sit in a free library like this one.
			</p>
			<p class="mt-4 text-small text-muted">English comes first, and these languages follow:</p>
			<ul class="mt-2 flex flex-wrap gap-2" aria-label="Languages">
				{#each OWB_LANGUAGES.slice(1) as l (l)}
					<li class="tag">{l}</li>
				{/each}
			</ul>
		</div>
	</section>

	<!-- What Ochorus adds around the text, each a door into the library. -->
	<section class="mt-14" aria-labelledby="here-heading">
		<p class="eyebrow text-gold">On Ochorus</p>
		<h2 id="here-heading" class="mt-1 text-h2 font-display font-semibold">
			Read it here like any book in the library
		</h2>
		<ul class="here mt-6">
			<li>
				<a class="here-card card-lift" href={localizeHref(`${BIBLE_PATH}/`)}>
					<span class="font-display text-body font-semibold text-text">Every book, in order</span>
					<span class="mt-1 block text-small text-muted">
						Genesis to Revelation, grouped by testament and division, each with its own cover in its
						Hebrew or Greek name.
					</span>
					<span class="mt-2 block text-small font-semibold text-accent">The Bible <Arrow /></span>
				</a>
			</li>
			<li>
				<a class="here-card card-lift" href={localizeHref(`/series/${BIBLE_SERIES}/`)}>
					<span class="font-display text-body font-semibold text-text">Straight through</span>
					<span class="mt-1 block text-small text-muted">
						Genesis to Revelation as one reading, with your place kept from book to book.
					</span>
					<span class="mt-2 block text-small font-semibold text-accent">{t('bible.inOrder')} <Arrow /></span>
				</a>
			</li>
			<li>
				<a class="here-card card-lift" href={localizeHref('/plans/')}>
					<span class="font-display text-body font-semibold text-text">A chapter a day</span>
					<span class="mt-1 block text-small text-muted">
						Reading plans such as John in 21 days, Proverbs in a month and Psalms in 150 days.
					</span>
					<span class="mt-2 block text-small font-semibold text-accent">Reading plans <Arrow /></span>
				</a>
			</li>
			<li>
				<div class="here-card">
					<span class="font-display text-body font-semibold text-text">An introduction to each book</span>
					<span class="mt-1 block text-small text-muted">
						Who wrote it, when and why, before you begin; and a closing note on what to carry
						away. Poetry is set line by line, as the Hebrew divides it.
					</span>
				</div>
			</li>
		</ul>
	</section>

	<!-- The way out: everything else lives at the translation's home. -->
	<section class="cta mt-16">
		<div>
			<h2 class="text-h2 font-display font-semibold">See the whole translation</h2>
			<p class="mt-2 text-small text-muted">
				All three levels, every reasoning record, the interlinear view and the other languages
				as they are drafted live at OpenWordBible.org.
			</p>
		</div>
		<a class="btn btn-primary" href={OWB_URL} rel="external noopener">
			OpenWordBible.org <span aria-hidden="true">↗</span>
		</a>
	</section>
</div>

<style>
	.hero {
		display: grid;
		grid-template-columns: minmax(0, 1.15fr) minmax(0, 0.85fr);
		gap: 2.5rem;
		align-items: center;
		padding-block: 1rem 2.5rem;
	}
	.lede {
		max-width: 56ch;
		font-size: var(--fs-body);
		line-height: 1.65;
	}
	.facts {
		display: flex;
		flex-wrap: wrap;
		gap: 0.25rem 0.6rem;
	}
	.levels {
		display: grid;
		grid-template-columns: repeat(3, minmax(0, 1fr));
		gap: 1rem;
	}
	.level {
		display: flex;
		flex-direction: column;
		padding: 1.25rem;
		border: 1px solid var(--border);
		border-radius: var(--radius-card);
		background: var(--surface);
	}
	.level.ours {
		border-color: var(--accent);
		box-shadow: 0 0 0 1px var(--accent);
	}
	.code {
		font-size: var(--fs-eyebrow);
		letter-spacing: 0.06em;
		color: var(--muted);
		font-variant-numeric: tabular-nums;
	}
	.verse {
		flex: 1;
		font-size: var(--fs-body);
		line-height: 1.6;
		color: var(--text);
	}
	.badge {
		align-self: flex-start;
		padding: 0.15rem 0.6rem;
		border-radius: var(--radius-pill);
		font-size: var(--fs-eyebrow);
		font-weight: 600;
		color: var(--accent);
		background: var(--surface-2);
	}
	.working {
		display: grid;
		grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
		gap: 2.5rem;
		align-items: start;
	}
	.working p {
		max-width: 56ch;
	}
	.record {
		padding: 1.5rem;
		border: 1px solid var(--border);
		border-inline-start: 3px solid var(--gold);
		border-radius: var(--radius-card);
		background: var(--surface);
	}
	.greek {
		font-family: var(--font-display);
		font-size: var(--fs-h2);
		font-weight: 600;
		margin-inline-end: 0.5rem;
	}
	.record dl > div {
		display: grid;
		grid-template-columns: 5.5rem minmax(0, 1fr);
		gap: 0.75rem;
		padding-block: 0.6rem;
		border-top: 1px solid var(--border);
	}
	.record dt {
		font-weight: 600;
		color: var(--muted);
	}
	.record dd {
		color: var(--text);
	}
	.facts-grid {
		display: grid;
		grid-template-columns: repeat(2, minmax(0, 1fr));
		gap: 1rem;
	}
	.panel {
		padding: 1.5rem;
		border: 1px solid var(--border);
		border-radius: var(--radius-card);
		background: var(--surface);
	}
	.here {
		display: grid;
		grid-template-columns: repeat(4, minmax(0, 1fr));
		gap: 0.875rem;
	}
	.here-card {
		display: block;
		height: 100%;
		padding: 1.1rem;
		border: 1px solid var(--border);
		border-radius: var(--radius-card);
		background: var(--surface);
	}
	.cta {
		display: flex;
		flex-wrap: wrap;
		align-items: center;
		justify-content: space-between;
		gap: 1.25rem;
		padding: 1.75rem;
		border-radius: var(--radius-card);
		background: var(--surface-2);
	}
	.cta p {
		max-width: 56ch;
	}
	@media (max-width: 900px) {
		.levels,
		.working,
		.facts-grid {
			grid-template-columns: minmax(0, 1fr);
		}
		.here {
			grid-template-columns: repeat(2, minmax(0, 1fr));
		}
	}
	@media (max-width: 639.98px) {
		.hero {
			grid-template-columns: minmax(0, 1fr);
			gap: 0.5rem;
			padding-block: 0 1.5rem;
		}
		.fan {
			order: -1;
			margin-bottom: 0.75rem;
		}
		.here {
			grid-template-columns: minmax(0, 1fr);
		}
		.cta {
			padding: 1.25rem;
		}
	}
</style>
