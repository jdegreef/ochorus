<script lang="ts">
	import { onMount, tick } from 'svelte';
	import { listSermons, type Sermon, type SermonSummary } from '$lib/library';
	import { SITE_URL } from '$lib/config';
	import { readerPrefs } from '$lib/readerPrefs.svelte';
	import { readerUi } from '$lib/readerUi.svelte';
	import { i18n } from '$lib/i18n.svelte';
	import { readingTime, readingMinutes } from '$lib/reading';
	import { getScrollAnchor, saveScrollAnchor, saveProgress, getProgressRecord } from '$lib/progress';
	import { SERMON_CHAPTER_ORDER } from '$lib/reading-schema';
	import { getLang } from '$lib/lang.svelte';
	import { listen } from '$lib/listen.svelte';
	import { scripture, type ScriptureResult } from '$lib/scripture.svelte';
	import { define } from '$lib/define.svelte';
	import { apiFetch } from '$lib/api';
	import { page } from '$app/stores';
	import { buildOutline, type OutlineEntry } from '$lib/sermonOutline';
	import { absUrl, jsonLd, breadcrumb } from '$lib/seo';

	import { renderMarks } from '$lib/rangeMarks';
	import { HIGHLIGHT_COLORS, DEFAULT_HIGHLIGHT } from '$lib/reading-schema';
	import { marks, type Segment } from '$lib/marks.svelte';
	import { focusTrap } from '$lib/actions/focusTrap';
	import { localizeHref, locales } from '$lib/paraglide/runtime';
	import ReaderControls from '$lib/components/ReaderControls.svelte';
	import ScripturePopover from '$lib/components/ScripturePopover.svelte';
	import SelectionBar from '$lib/components/SelectionBar.svelte';
	import DefinePopover from '$lib/components/DefinePopover.svelte';
	import Icon from '$lib/components/Icon.svelte';
	import ListenBar from '$lib/components/ListenBar.svelte';

	let { data } = $props();
	const sermon = $derived(data.sermon as Sermon);
	const t = i18n.t;

	let body = $state<HTMLElement | undefined>();
	// Other sermons on the same Bible book, fetched client-side (page is
	// prerendered; the list is small and cached by the browser).
	let related = $state<SermonSummary[]>([]);

	// --- Reading progress ------------------------------------------------------
	// Long sermons need orientation: a scroll-progress bar, an estimate of the
	// time remaining, and a resume point. Anchored to the top-visible paragraph
	// so it survives text-size / width changes (mirrors the chapter reader).
	const HEADER_OFFSET = 64;
	let frac = $state(0);
	let saveTimer: ReturnType<typeof setTimeout> | undefined;
	const minutesLeft = $derived(
		Math.max(1, Math.ceil(readingMinutes(sermon.word_count) * (1 - frac)))
	);

	function topVisibleIndex(): number {
		if (!body) return 0;
		const kids = body.children;
		for (let i = 0; i < kids.length; i++) {
			if (kids[i].getBoundingClientRect().bottom > HEADER_OFFSET) return i;
		}
		return Math.max(0, kids.length - 1);
	}

	function updateFraction() {
		if (!body) return;
		const rect = body.getBoundingClientRect();
		if (rect.height <= 0) return;
		const seen = Math.min(Math.max(window.innerHeight - rect.top, 0), rect.height);
		frac = Math.min(1, Math.max(0, seen / rect.height));
	}

	function onScroll() {
		updateActiveSection(); // cheap; keep the outline rail responsive
		clearTimeout(saveTimer);
		saveTimer = setTimeout(() => {
			updateFraction();
			saveScrollAnchor(sermon.slug, SERMON_CHAPTER_ORDER, topVisibleIndex(), 'sermon');
		}, 250);
	}

	// --- Jump-to-section outline ----------------------------------------------
	// Built from the rendered body once it's in the page (headings + the classic
	// "I. / II. / III." homiletic points). Shown only when there's real
	// structure to navigate.
	let outline = $state<OutlineEntry[]>([]);
	let outlineOpen = $state(false);
	// The section the reader is currently in — for the desktop rail's highlight.
	let activeSection = $state('');
	$effect(() => {
		void sermon.slug; // rebuild when navigating between sermons
		outline = body ? buildOutline(body) : [];
		// Off the reactive graph: reading `outline` here would re-trigger this
		// effect (which writes it) — an update-depth loop.
		if (typeof requestAnimationFrame !== 'undefined') requestAnimationFrame(updateActiveSection);
	});

	/** The last outline section whose heading has scrolled up past the top bar. */
	function updateActiveSection() {
		let current = '';
		for (const s of outline) {
			const el = document.getElementById(s.id);
			if (!el) continue;
			if (el.getBoundingClientRect().top <= HEADER_OFFSET + 40) current = s.id;
			else break; // outline is in document order — nothing below can be active
		}
		activeSection = current;
	}

	function scrollToSection(id: string) {
		const el = document.getElementById(id);
		if (el) {
			const y = el.getBoundingClientRect().top + window.scrollY - HEADER_OFFSET - 8;
			window.scrollTo({ top: y, behavior: 'smooth' });
		}
		outlineOpen = false;
	}

	// Record the visit (so the sermon lands in "Continue reading") and restore
	// the saved spot — a `?p=` deep link (notebook highlights) wins over the
	// device anchor. Effect, not onMount: client-side nav between sermons
	// reuses this component.
	let restoredFor = '';
	$effect(() => {
		const slug = sermon.slug;
		if (!body || restoredFor === slug) return;
		restoredFor = slug;
		// A pending scroll-save from the PREVIOUS sermon must not fire against
		// this one's body (it would record a bogus synced resume point).
		clearTimeout(saveTimer);
		// Seed a ?p= deep link into the anchor FIRST so the progress record
		// (and the resume point that syncs to the account) starts at the
		// jumped-to paragraph — the chapter reader's documented ordering.
		const fromUrl = Number($page.url.searchParams.get('p'));
		if (Number.isFinite(fromUrl) && fromUrl > 0) {
			saveScrollAnchor(slug, SERMON_CHAPTER_ORDER, fromUrl, 'sermon');
		}
		saveProgress(slug, SERMON_CHAPTER_ORDER, sermon.language, 'sermon');
		(async () => {
			await tick();
			// Deep link > device anchor > synced resume point (fresh device).
			const idx =
				Number.isFinite(fromUrl) && fromUrl > 0
					? fromUrl
					: (getScrollAnchor(slug, SERMON_CHAPTER_ORDER, 'sermon') ??
						getProgressRecord(slug, 'sermon')?.paragraph_index ??
						0);
			if (idx > 0 && body?.children[idx]) {
				body.children[idx].scrollIntoView({ block: 'start' });
				window.scrollBy(0, -HEADER_OFFSET);
			}
			updateFraction();
		})();
	});

	// Marks can be replaced underneath us (sign-in merge / sign-out wipe),
	// and a scroll-save timer must not outlive the page.
	onMount(() => {
		const onSync = () => marks.refresh();
		window.addEventListener('ochorus:sync', onSync);
		return () => {
			clearTimeout(saveTimer);
			window.removeEventListener('ochorus:sync', onSync);
		};
	});

	const initials = (name: string) =>
		name.split(' ').filter(Boolean).map((w) => w[0]).slice(0, 2).join('').toUpperCase();

	// The sermon's preaching text — the verse(s) it's built on — for the header
	// card. Fetched client-side (the page is prerendered); absent = card shows
	// just the reference.
	let preachingText = $state<ScriptureResult | null>(null);
	$effect(() => {
		const ref = sermon.scripture_ref;
		preachingText = null;
		if (!ref) return;
		apiFetch<ScriptureResult>(`/api/library/scripture/?ref=${encodeURIComponent(ref)}`)
			.then((v) => (preachingText = v))
			.catch(() => (preachingText = null));
	});

	/** "1 Peter 2:7" -> "1 Peter"; "Matthew 11:28" -> "Matthew". */
	const refBook = (ref: string) => ref.match(/^(\d?\s?[A-Za-z]+)/)?.[1]?.trim() ?? '';
	const book = $derived(refBook(sermon.scripture_ref || ''));

	onMount(() => {
		readerPrefs.init();
		listen.init();
		if (book) {
			listSermons(getLang())
				.then((all) => {
					related = all.filter(
						(s) => s.slug !== sermon.slug && refBook(s.scripture_ref || '') === book
					);
				})
				.catch(() => (related = []));
		}
	});

	/** Tap a server-wrapped Bible reference → open the scripture popover. */
	function onBodyClick(e: MouseEvent) {
		const a = (e.target as HTMLElement).closest?.('a.scripture-ref') as HTMLElement | null;
		if (!a?.dataset.ref) return;
		e.preventDefault();
		const r = a.getBoundingClientRect();
		scripture.show(a.dataset.ref, r.bottom + window.scrollY, r.left + window.scrollX + r.width / 2);
	}

	/** Read the sermon aloud, starting from the paragraph you're reading. */
	function startListening() {
		if (!body) return;
		const paragraphs = [...body.children].map((el) => (el as HTMLElement).innerText);
		listen.start(paragraphs, topVisibleIndex(), getLang(), {
			title: sermon.title,
			artist: sermon.author_name
		});
	}

	// Follow-along: highlight the paragraph being spoken and keep it in view.
	$effect(() => {
		const current = listen.current;
		if (!body) return;
		const kids = body.children;
		for (let i = 0; i < kids.length; i++) {
			kids[i].classList.toggle('tts-current', i === current);
		}
		if (current >= 0 && kids[current]) {
			kids[current].scrollIntoView({ block: 'center', behavior: 'smooth' });
		}
	});

	// Stop speech when navigating to another sermon or leaving the page.
	$effect(() => {
		void sermon.slug;
		return () => listen.stop();
	});

	// Self-referential canonical + hreflang per locale (mirrors authors/[slug]) —
	// an English canonical here would deindex the translated sermon pages.
	const path = $derived(`/sermons/${sermon.slug}/`);
	const canonical = $derived(`${SITE_URL}${localizeHref(path)}`);
	const alternates = $derived(
		locales.map((loc) => ({ loc, href: `${SITE_URL}${localizeHref(path, { locale: loc })}` }))
	);
	const preachedYear = $derived(sermon.preached_on ? sermon.preached_on.slice(0, 4) : '');

	// --- SEO -------------------------------------------------------------------
	// A real description from the opening prose (beats the generic template) and
	// structured data: an Article for the sermon (its preaching text as `about`)
	// plus a breadcrumb. og:image is the author portrait when present (raster).
	const metaDescription = $derived(
		(sermon.body_html || '').replace(/<[^>]+>/g, ' ').replace(/\s+/g, ' ').trim().slice(0, 155) ||
			`${sermon.title} — a sermon by ${sermon.author_name}.`
	);
	const ogImage = $derived(sermon.author_photo ? absUrl(sermon.author_photo) : '');
	const sermonLd = $derived(
		jsonLd({
			'@context': 'https://schema.org',
			'@type': 'Article',
			headline: sermon.title,
			author: {
				'@type': 'Person',
				name: sermon.author_name,
				url: absUrl(`/authors/${sermon.author_slug}`)
			},
			inLanguage: sermon.language,
			url: canonical,
			isAccessibleForFree: true,
			datePublished: sermon.preached_on || undefined,
			image: ogImage || undefined,
			about: sermon.scripture_ref ? { '@type': 'Thing', name: sermon.scripture_ref } : undefined,
			publisher: { '@type': 'Organization', name: 'Ochorus' }
		})
	);
	const crumbsLd = $derived(
		jsonLd(
			breadcrumb([
				{ name: t('common.home'), url: '/' },
				{ name: t('nav.sermons'), url: '/sermons' },
				{ name: sermon.title, url: `/sermons/${sermon.slug}` }
			])
		)
	);

	// Selecting text offers copy-quote / share (with attribution), highlight and
	// note; a single word opens the dictionary — same as the chapter reader.
	const cite = $derived({
		author: sermon.author_name,
		book: sermon.title,
		chapter: '',
		url: $page.url.href
	});

	// --- Highlights & notes ----------------------------------------------------
	// Device-local text-range marks over the sermon body (shared range model with
	// the book reader; see marks.svelte.ts). A note editor opens on tap of a
	// marked span or via the selection bar's "Note".
	let noteOpen = $state(false);
	let noteId = $state<string | null>(null);
	let notePending = $state<Segment[]>([]);
	let noteDraft = $state('');
	let noteColor = $state<string>(DEFAULT_HIGHLIGHT);

	$effect(() => {
		// Reload when navigating between sermons.
		marks.load(sermon.slug, SERMON_CHAPTER_ORDER, sermon.language, 'sermon');
	});

	// Paint marks as <mark> spans; clicking one opens its note editor.
	$effect(() => {
		const list = marks.list;
		if (!body) return;
		renderMarks(body, list, (id) => {
			noteId = id;
			notePending = [];
			noteDraft = marks.getNote(id);
			noteColor = marks.getColor(id);
			noteOpen = true;
		});
	});

	/** Note on a fresh selection: highlight it first, then attach the note. */
	function openNoteForSelection(segments: Segment[]) {
		const existing = marks.groupCovering(segments);
		noteId = existing;
		notePending = existing ? [] : segments;
		noteDraft = existing ? marks.getNote(existing) : '';
		noteColor = existing ? marks.getColor(existing) : DEFAULT_HIGHLIGHT;
		noteOpen = true;
	}
	function saveNote() {
		if (noteId) {
			marks.setNote(noteId, noteDraft);
			marks.setColor(noteId, noteColor);
		} else if (notePending.length && noteDraft.trim()) {
			marks.add(notePending, noteDraft, noteColor);
		}
		noteOpen = false;
	}
	function removeMark() {
		if (noteId) marks.remove(noteId);
		noteOpen = false;
	}
</script>

<svelte:head>
	<title>{sermon.title} — {sermon.author_name} — Ochorus</title>
	<meta name="description" content={metaDescription} />
	<link rel="canonical" href={canonical} />
	{#each alternates as a (a.loc)}
		<link rel="alternate" hreflang={a.loc} href={a.href} />
	{/each}
	<link rel="alternate" hreflang="x-default" href="{SITE_URL}{localizeHref(path, { locale: 'en' })}" />
	<meta property="og:type" content="article" />
	<meta property="og:title" content="{sermon.title} — {sermon.author_name}" />
	<meta property="og:description" content={metaDescription} />
	<meta property="og:url" content={canonical} />
	{#if ogImage}<meta property="og:image" content={ogImage} />{/if}
	<meta name="twitter:card" content={ogImage ? 'summary_large_image' : 'summary'} />
	{@html sermonLd}
	{@html crumbsLd}
</svelte:head>

<svelte:window onscroll={onScroll} />

<!-- Scroll-progress bar, pinned to the very top of the viewport. -->
<div class="read-progress" style="transform: scaleX({frac})" aria-hidden="true"></div>

<!-- Reader top bar -->
{#if !readerUi.focus}
	<div class="sticky top-0 z-10 border-b border-border bg-bg/90 backdrop-blur">
		<div class="mx-auto flex max-w-3xl items-center justify-between gap-3 px-5 py-2.5">
			<a href={localizeHref('/sermons')} class="text-small text-muted hover:text-text">← {t('nav.sermons')}</a>
			<div class="flex shrink-0 items-center gap-1">
				{#if outline.length >= 2}
					<button
						class="outline-toggle-btn btn btn-ghost !px-2 !py-1.5"
						class:!text-accent={outlineOpen}
						onclick={() => (outlineOpen = !outlineOpen)}
						aria-label={t('sermon.outline')}
						title={t('sermon.outline')}
						aria-expanded={outlineOpen}><Icon name="list" size={18} /></button
					>
				{/if}
				{#if listen.supported}
					<button
						class="btn btn-ghost !px-2.5 !py-1"
						class:!text-accent={listen.status !== 'idle'}
						onclick={() => (listen.status === 'idle' ? startListening() : listen.stop())}
						aria-label={t('reader.listen')}
						title={t('reader.listen')}>▶</button
					>
				{/if}
				<ReaderControls />
				<button
					class="btn btn-ghost !px-3 !py-1"
					onclick={() => readerUi.toggleFocus()}
					aria-label={t('reader.focus')}
					title={t('reader.focus')}>☾</button
				>
			</div>
		</div>
	</div>
{/if}

{#if readerUi.focus}
	<button
		class="fixed right-4 top-4 z-30 rounded-full border border-border bg-surface/90 px-3 py-1.5 text-small text-muted shadow-md backdrop-blur hover:text-text"
		onclick={() => readerUi.exitFocus()}>✕ {t('reader.exitFocus')}</button
	>
{/if}

<!-- Jump-to-section outline panel (opened from the top bar). -->
{#if outlineOpen}
	<!-- svelte-ignore a11y_click_events_have_key_events, a11y_no_static_element_interactions -->
	<div class="outline-backdrop" onclick={() => (outlineOpen = false)}></div>
	<nav
		class="outline-panel"
		aria-label={t('sermon.outline')}
		use:focusTrap={{ onEscape: () => (outlineOpen = false) }}
	>
		<p class="outline-title">{t('sermon.outline')}</p>
		<ul>
			{#each outline as s (s.id)}
				<li>
					<button class="outline-item" class:point={s.kind === 'point'} onclick={() => scrollToSection(s.id)}>
						{s.label}
					</button>
				</li>
			{/each}
		</ul>
	</nav>
{/if}

<!-- Persistent outline rail (wide screens): mirrors the popover, highlighting
     the section you're reading. The top-bar toggle takes over below 1200px. -->
{#if outline.length >= 2 && !readerUi.focus}
	<nav class="outline-rail" aria-label={t('sermon.outline')}>
		<p class="outline-rail-title">{t('sermon.outline')}</p>
		<ul>
			{#each outline as s (s.id)}
				<li>
					<button
						class="outline-rail-item"
						class:point={s.kind === 'point'}
						class:active={activeSection === s.id}
						onclick={() => scrollToSection(s.id)}
					>
						{s.label}
					</button>
				</li>
			{/each}
		</ul>
	</nav>
{/if}

<article class="mx-auto px-5 py-10" style="{readerPrefs.style}; max-width: var(--reading-measure)" dir="auto">
	<!-- Breadcrumb -->
	<nav class="mb-5 flex flex-wrap items-center gap-1.5 text-small text-muted" aria-label={t('a11y.breadcrumb')}>
		<a href={localizeHref('/sermons')} class="hover:text-text">{t('nav.sermons')}</a>
		<span>›</span>
		<a href={localizeHref(`/authors/${sermon.author_slug}`)} class="hover:text-text">{sermon.author_name}</a>
	</nav>

	<p class="mb-1 text-small uppercase tracking-wider text-muted">
		{t('search.typeSermon')} · {readingTime(sermon.word_count)}{#if preachedYear} · {preachedYear}{/if}
	</p>
	<h1 class="text-h1 mb-3">{sermon.title}</h1>

	<!-- Author row: portrait + name -->
	<a
		href={localizeHref(`/authors/${sermon.author_slug}`)}
		class="group mb-5 inline-flex items-center gap-2.5 hover:no-underline"
	>
		{#if sermon.author_photo}
			<img
				src={sermon.author_photo}
				alt="{t('a11y.portraitOf')} {sermon.author_name}"
				class="h-9 w-9 shrink-0 rounded-full border border-border object-cover"
				style="filter: grayscale(1)"
				loading="lazy"
			/>
		{:else}
			<span
				class="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-accent-soft text-small font-semibold text-accent"
			>
				{initials(sermon.author_name)}
			</span>
		{/if}
		<span class="text-body font-medium text-text group-hover:text-accent">{sermon.author_name}</span>
	</a>

	<!-- Preaching text: the reference, and its verse(s) when available -->
	{#if sermon.scripture_ref}
		<div class="text-card">
			<p class="text-card-eyebrow">{t('sermon.text')}</p>
			<p class="text-card-ref">{sermon.scripture_ref}</p>
			{#if preachingText?.verses?.length}
				<p class="text-card-verse">
					{#each preachingText.verses as v (v.number)}{v.text}{' '}{/each}
				</p>
				<p class="text-card-version">{preachingText.version}</p>
			{/if}
		</div>
	{/if}

	{#if sermon.source_type === 'ai_unreviewed'}
		<p
			class="mb-8 inline-flex items-center gap-1.5 rounded-full border border-gold/40 bg-gold/10 px-3 py-1 text-small text-gold"
		>
			{t('book.aiUnreviewed')}
		</p>
	{:else if sermon.source_type === 'ai_reviewed'}
		<p
			class="mb-8 inline-flex items-center gap-1.5 rounded-full border border-border bg-surface-2 px-3 py-1 text-small text-muted"
		>
			{t('book.aiReviewed')}
		</p>
	{:else}
		<div class="mb-8"></div>
	{/if}

	<!-- Body HTML is cleaned server-side to a safe tag subset on ingest;
	     Bible references are wrapped as tappable spans (scripture popover). -->
	<!-- svelte-ignore a11y_no_noninteractive_element_interactions, a11y_click_events_have_key_events, a11y_no_static_element_interactions -->
	<div class="reading" bind:this={body} onclick={onBodyClick}>{@html sermon.body_html}</div>

	<!-- Scripture index: the passages this sermon engages, each a jump into
	     scripture search — so scripture is a navigation surface, not just text. -->
	{#if sermon.scripture_refs?.length}
		<div class="mt-10 flex flex-wrap items-center gap-2 border-t border-border pt-5">
			<span class="text-small font-semibold uppercase tracking-wide text-muted">
				{t('sermon.scriptureIndex')}
			</span>
			{#each sermon.scripture_refs as ref (ref)}
				<a
					href={localizeHref(`/search?q=${encodeURIComponent(ref)}`)}
					class="rounded-full border border-border px-3 py-1 text-small text-text hover:border-accent hover:text-accent hover:no-underline"
				>
					{ref}
				</a>
			{/each}
		</div>
	{/if}

	<!-- Sequential prev/next through this author's sermons, so a reader who
	     finishes one keeps going instead of dead-ending at the bottom. -->
	{#if sermon.prev || sermon.next}
		<nav class="mt-12 flex gap-3 border-t border-border pt-6" aria-label={t('sermon.sequentialNav')}>
			{#if sermon.prev}
				<a
					href={localizeHref(`/sermons/${sermon.prev.slug}`)}
					class="group flex-1 rounded-card border border-border p-3 hover:border-accent hover:no-underline"
				>
					<div class="text-[0.72rem] uppercase tracking-wide text-muted">← {t('reader.previous')}</div>
					<div class="mt-0.5 text-small font-semibold text-text group-hover:text-accent">{sermon.prev.title}</div>
				</a>
			{/if}
			{#if sermon.next}
				<a
					href={localizeHref(`/sermons/${sermon.next.slug}`)}
					class="group flex-1 rounded-card border border-border p-3 text-right hover:border-accent hover:no-underline"
				>
					<div class="text-[0.72rem] uppercase tracking-wide text-muted">{t('reader.next')} →</div>
					<div class="mt-0.5 text-small font-semibold text-text group-hover:text-accent">{sermon.next.title}</div>
				</a>
			{/if}
		</nav>
	{/if}

	{#if related.length}
		<section class="mt-12 border-t border-border pt-6">
			<h2 class="text-h3 mb-3">{t('sermon.moreOn')} {book}</h2>
			<ul class="space-y-2">
				{#each related as r (r.slug)}
					<li>
						<a href={localizeHref(`/sermons/${r.slug}`)} class="text-body font-medium">{r.title}</a>
						<span class="text-small text-muted"> · {r.scripture_ref} · {r.author.name}</span>
					</li>
				{/each}
			</ul>
		</section>
	{/if}

	{#if sermon.source_url}
		<p class="mt-12 border-t border-border pt-5 text-[0.8rem] text-muted">
			{t('book.publicDomain')}
			<a href={sermon.source_url} target="_blank" rel="noreferrer">{t('book.originalEdition')}</a>.
		</p>
	{/if}

	<nav class="mt-8">
		<a href={localizeHref(`/authors/${sermon.author_slug}`)} class="btn btn-ghost">← {t('sermon.moreFrom')} {sermon.author_name}</a>
	</nav>
</article>

<!-- Time-remaining pill; hidden in focus and while listening. -->
{#if !readerUi.focus && listen.status === 'idle' && frac < 0.99}
	<div class="min-left" aria-hidden="true">{minutesLeft} {t('sermon.minLeft')}</div>
{/if}

<SelectionBar
	container={body}
	{cite}
	onHighlight={(segments, color) => {
		const existing = marks.groupCovering(segments);
		if (!existing) marks.add(segments, undefined, color);
		else if (marks.getColor(existing) === color) marks.remove(existing);
		else marks.setColor(existing, color);
	}}
	onNote={openNoteForSelection}
	highlightColor={(segments) => {
		const id = marks.groupCovering(segments);
		return id ? marks.getColor(id) : null;
	}}
	onDefine={(word, top, left) => define.show(word, top, left)}
/>

<ScripturePopover />
<DefinePopover />
<ListenBar />

{#if noteOpen}
	<div
		class="note-overlay"
		role="dialog"
		aria-modal="true"
		aria-label={t('reader.note')}
		use:focusTrap={{ onEscape: () => (noteOpen = false) }}
	>
		<div class="note-card">
			<h2 class="mb-2 text-h3">{t('reader.note')}</h2>
			<div class="mb-3 flex items-center gap-2.5" role="group" aria-label={t('reader.highlight')}>
				{#each HIGHLIGHT_COLORS as color (color)}
					<button
						type="button"
						class="hl-swatch"
						data-color={color}
						class:active={noteColor === color}
						aria-pressed={noteColor === color}
						aria-label="{t('reader.highlight')}: {t(`reader.hl_${color}`)}"
						title={t(`reader.hl_${color}`)}
						onclick={() => (noteColor = color)}
					></button>
				{/each}
			</div>
			<textarea
				bind:value={noteDraft}
				rows="5"
				class="w-full rounded-sm border border-border bg-bg p-3 text-body text-text"
				aria-label={t('reader.note')}
				placeholder="…"
			></textarea>
			<div class="mt-3 flex items-center gap-2">
				{#if noteId}
					<button class="btn btn-ghost !text-red-700 dark:!text-red-400" onclick={removeMark}>
						{t('reader.removeHighlight')}
					</button>
				{/if}
				<span class="flex-1"></span>
				<button class="btn btn-ghost" onclick={() => (noteOpen = false)}>{t('common.cancel')}</button>
				<button class="btn btn-primary" onclick={saveNote}>{t('common.save')}</button>
			</div>
		</div>
	</div>
{/if}

<style>
	/* Scroll-progress bar: a thin accent line scaled by reading fraction. */
	.read-progress {
		position: fixed;
		top: 0;
		left: 0;
		right: 0;
		height: 2px;
		z-index: 40;
		background: var(--accent);
		transform-origin: left center;
		transition: transform 0.1s linear;
		pointer-events: none;
	}
	.min-left {
		position: fixed;
		bottom: 1rem;
		left: 50%;
		transform: translateX(-50%);
		z-index: 30;
		border-radius: 9999px;
		border: 1px solid var(--border);
		background: color-mix(in srgb, var(--bg) 85%, transparent);
		backdrop-filter: blur(6px);
		padding: 0.25rem 0.8rem;
		font-size: 0.72rem;
		color: var(--muted);
		pointer-events: none;
	}

	/* Preaching-text card: the sermon's reference + verse(s) as an epigraph. */
	.text-card {
		margin: 0 0 2rem;
		padding: 0.85rem 1.1rem;
		border-left: 3px solid var(--accent);
		border-radius: 0 var(--radius-card) var(--radius-card) 0;
		background: var(--accent-soft);
	}
	.text-card-eyebrow {
		font-size: 0.66rem;
		font-weight: 700;
		letter-spacing: 0.1em;
		text-transform: uppercase;
		color: var(--accent);
	}
	.text-card-ref {
		font-family: var(--font-display);
		font-size: var(--fs-h3);
		color: var(--accent);
		margin-top: 0.1rem;
	}
	.text-card-verse {
		margin-top: 0.5rem;
		font-family: var(--font-display);
		font-style: italic;
		line-height: 1.6;
		color: var(--text);
	}
	.text-card-version {
		margin-top: 0.45rem;
		font-size: 0.66rem;
		letter-spacing: 0.08em;
		text-transform: uppercase;
		color: var(--muted);
	}

	/* Paragraph currently being read aloud in Listen mode. */
	:global(.reading > .tts-current) {
		background: color-mix(in srgb, var(--accent) 10%, transparent);
		border-radius: 4px;
		box-shadow: 0 0 0 6px color-mix(in srgb, var(--accent) 10%, transparent);
		transition: background 0.3s ease;
	}

	/* Text-range marks (<mark> spans) are styled globally in app.css. */
	.note-overlay {
		position: fixed;
		inset: 0;
		z-index: 50;
		display: flex;
		align-items: center;
		justify-content: center;
		padding: 1rem;
		background: rgb(0 0 0 / 0.4);
	}
	.note-card {
		width: 100%;
		max-width: 32rem;
		border-radius: var(--radius-card);
		border: 1px solid var(--border);
		background: var(--surface);
		padding: 1.25rem;
		box-shadow: 0 10px 40px rgb(0 0 0 / 0.35);
	}

	/* Jump-to-section outline: a light popover under the reader bar. */
	.outline-backdrop {
		position: fixed;
		inset: 0;
		z-index: 20;
	}
	.outline-panel {
		position: fixed;
		top: 3.4rem;
		right: max(0.75rem, calc((100vw - 48rem) / 2));
		z-index: 21;
		width: min(20rem, calc(100vw - 1.5rem));
		max-height: 70vh;
		overflow-y: auto;
		border: 1px solid var(--border);
		border-radius: var(--radius-card);
		background: var(--surface);
		box-shadow: 0 10px 40px rgb(0 0 0 / 0.25);
		padding: 0.5rem;
	}
	.outline-title {
		padding: 0.35rem 0.6rem;
		font-size: 0.7rem;
		font-weight: 700;
		letter-spacing: 0.08em;
		text-transform: uppercase;
		color: var(--muted);
	}
	.outline-item {
		display: block;
		width: 100%;
		text-align: left;
		padding: 0.45rem 0.6rem;
		border-radius: var(--radius-sm, 6px);
		font-size: 0.9rem;
		color: var(--text);
		line-height: 1.35;
	}
	.outline-item:hover {
		background: var(--surface-2);
		color: var(--accent);
	}
	/* Real headings sit flush; homiletic points get a subtle indent + accent. */
	.outline-item.point {
		color: var(--muted);
	}
	.outline-item.point:hover {
		color: var(--accent);
	}

	/* Persistent outline rail — hidden until there's room beside the article. */
	.outline-rail {
		display: none;
	}
	@media (min-width: 1200px) {
		.outline-rail {
			display: block;
			position: fixed;
			top: 5rem;
			right: max(1rem, calc((100vw - var(--reading-measure, 46rem)) / 2 - 15rem));
			width: 14rem;
			max-height: calc(100vh - 7rem);
			overflow-y: auto;
			z-index: 5;
		}
		/* The top-bar toggle is redundant once the rail is visible. */
		.outline-toggle-btn {
			display: none;
		}
	}
	.outline-rail-title {
		padding: 0 0.6rem 0.4rem;
		font-size: 0.68rem;
		font-weight: 700;
		letter-spacing: 0.08em;
		text-transform: uppercase;
		color: var(--muted);
	}
	.outline-rail-item {
		display: block;
		width: 100%;
		text-align: left;
		padding: 0.3rem 0.6rem;
		border-left: 2px solid transparent;
		font-size: 0.85rem;
		line-height: 1.35;
		color: var(--muted);
		transition: color 0.15s ease;
	}
	.outline-rail-item:hover {
		color: var(--accent);
	}
	.outline-rail-item.point {
		padding-left: 1.1rem;
	}
	.outline-rail-item.active {
		color: var(--accent);
		border-left-color: var(--accent);
		font-weight: 600;
	}
</style>
