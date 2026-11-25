<script lang="ts">
	import { bookChapterPath } from '$lib/reading-schema';
	import { search, searchComplete, scripturePageHref, quoteHitHref, type SearchHit } from '$lib/library-public';
	import { authorPath } from '$lib/originals';
	import { answerHref } from '$lib/searchResults';
	import {
		primaryNav,
		SERIES_DEST,
		AUDIENCE_DESTS,
		ORIGINALS_DEST,
		AZ_INDEX_DEST,
		hubDests
	} from '$lib/contentNav';
	import { getLang, lang } from '$lib/lang.svelte';
	import { nameOfLanguage } from '$lib/languageNames';
	import { minQueryLength } from '$lib/searchHits';
	import { FOR_EYEBROW, FOR_LINKS, forInline } from '$lib/forLinks';
	import { promoLocale } from '$lib/forPromos';
	import { i18n } from '$lib/i18n.svelte';
	import { localizeHref } from '$lib/href';
	import { focusTrap } from '$lib/actions/focusTrap';
	import { portal } from '$lib/actions/portal';
	import { goto } from '$app/navigation';
	import { paletteUi } from '$lib/paletteUi.svelte';
	import { auth } from '$lib/auth.svelte';
	import { ADMIN_SECTIONS, opensSection } from '$lib/adminSections';
	import { adminListHref, adminWorkHref, type AdminListKind } from '$lib/adminLinks';

	const t = i18n.t;

	let q = $state('');
	let hits = $state<SearchHit[]>([]);
	/** Suggestions as you type: what the letters so far already name. */
	let suggested = $state<SearchHit[]>([]);
	let loading = $state(false);
	let activeIndex = $state(0);
	let inputEl = $state<HTMLInputElement>();
	let timer: ReturnType<typeof setTimeout> | undefined;
	let suggestTimer: ReturnType<typeof setTimeout> | undefined;
	/** Monotonic token so only the newest in-flight search may write `hits`. */
	let searchSeq = 0;

	// Quick-nav destinations — the app's primary pages, jumpable by name.
	// Home, then the content types in `primaryNav` order (shared with the top nav
	// and footer so the three can't drift — F2; the Bible among them where its
	// books have shipped), then the English-only hubs on
	// the same gate as the footer (in another locale they would jump to a page
	// with nothing on it; ungate when translated), then the utility pages.
	const COMMANDS = $derived([
		{ href: '/', label: t('nav.home') },
		...primaryNav(getLang()).map((d) => ({ href: d.href, label: t(d.labelKey) })),
		{ href: SERIES_DEST.href, label: t(SERIES_DEST.labelKey) },
		...AUDIENCE_DESTS.map((d) => ({ href: d.href, label: t(d.labelKey) })),
		{ href: AZ_INDEX_DEST.href, label: t(AZ_INDEX_DEST.labelKey) },
		// The English-only hubs.
		...hubDests(getLang()).map((d) => ({ href: d.href, label: t(d.labelKey) })),
		...(getLang() === 'en'
			? [
					// The seasonal hub (English-only, $lib/advent): "advent" typed here
					// finds it in any month.
					{ href: '/advent/', label: t('liturgical.advent') }
				]
			: []),
		{ href: ORIGINALS_DEST.href, label: t(ORIGINALS_DEST.labelKey) },
		{ href: '/notebook', label: t('notebook.title') },
		{ href: '/settings', label: t('settings.title') },
		{ href: '/about', label: t('nav.about') },
		{ href: '/contact', label: t('nav.contact') },
		// The "Ochorus for …" pages, where they are written (English, French):
		// "homeschool" or "chaplains" typed here finds the page for them.
		...forCommands(promoLocale(getLang()))
	]);

	function forCommands(loc: ReturnType<typeof promoLocale>) {
		if (!loc) return [];
		return [
			{ href: '/for', label: `${FOR_EYEBROW[loc]}…` },
			...FOR_LINKS.map((l) => ({ href: `/for/${l.slug}`, label: `${FOR_EYEBROW[loc]} ${forInline(l, loc)}` }))
		];
	}

	/** `admin`: the hit's admin page (a book or sermon) or admin list (any other
	 *  kind that has one), for a viewer who can open it. */
	type Item = {
		key: string;
		kind: 'cmd' | 'hit';
		label: string;
		title: string;
		meta: string;
		href: string;
		admin?: string;
	};

	// ---- admin shortcuts (English-only, like the admin itself) ----
	// The admin pages a viewer can open — the rail's own list and rule
	// (`$lib/adminSections`), so the palette can't offer a section the rail
	// hides. UX only: every admin page and API call is gated server-side.
	const adminCommands = $derived(
		auth.hasAdminAccess ? ADMIN_SECTIONS.filter((s) => opensSection(s, auth)) : []
	);
	// A work's admin page is a reporting view (AdminBookDetailView /
	// AdminSermonDetailView require reporting:view).
	const canOpenWork = $derived(auth.can('reporting'));
	const adminHref = (kind: 'book' | 'sermon', slug: string) =>
		canOpenWork ? adminWorkHref(kind, slug) : undefined;
	// A kind with no admin page of its own opens its admin list, searched for
	// the hit — the same reporting gate as the work pages.
	const adminList = (kind: AdminListKind, q: string) =>
		canOpenWork ? adminListHref(kind, q) : undefined;

	function hitItem(h: SearchHit): Item {
		switch (h.type) {
			case 'author':
				return { key: 'author:' + h.author_slug, kind: 'hit', label: t('search.typeAuthor'), title: h.author_name, meta: '', href: authorPath(h.author_slug), admin: adminList('authors', h.author_name) };
			case 'book':
				return { key: 'book:' + h.book_slug, kind: 'hit', label: t('search.typeBook'), title: h.book_title, meta: h.author_name, href: `/books/${h.book_slug}`, admin: adminHref('book', h.book_slug) };
			case 'topic':
				return { key: 'topic:' + h.topic_slug, kind: 'hit', label: t('search.typeTopic'), title: h.topic_title, meta: '', href: `/topics/${h.topic_slug}`, admin: adminList('topics', h.topic_slug) };
			case 'plan':
				return { key: 'plan:' + h.plan_slug, kind: 'hit', label: t('search.typePlan'), title: h.plan_title, meta: '', href: `/plans/${h.plan_slug}`, admin: adminList('plans', h.plan_slug) };
			case 'article':
				return { key: 'article:' + h.article_slug, kind: 'hit', label: t('search.typeArticle'), title: h.article_title, meta: '', href: `/articles/${h.article_slug}`, admin: adminList('articles', h.article_slug) };
			case 'scripture':
				return { key: `scripture:${h.book_slug}:${h.chapter}:${h.verse ?? ''}`, kind: 'hit', label: t('search.typeScripture'), title: h.reference, meta: '', href: scripturePageHref(h.book_slug, h.chapter, h.verse) };
			case 'answer':
				return { key: `answer:${h.work_kind}-${h.work_slug}`, kind: 'hit', label: t('search.typeAnswer'), title: h.question, meta: h.work_title, href: answerHref(h) };
			case 'quote':
				return { key: 'quote:' + h.quote_slug, kind: 'hit', label: t('nav.quotes'), title: h.text, meta: h.author_name, href: quoteHitHref(h), admin: adminList('quotes', h.text.slice(0, 60)) };
			case 'sermon':
				return { key: 'sermon:' + h.sermon_slug, kind: 'hit', label: t('search.typeSermon'), title: h.sermon_title, meta: h.author_name, href: `/sermons/${h.sermon_slug}`, admin: adminHref('sermon', h.sermon_slug) };
			default:
				return { key: `chapter:${h.book_slug}:${h.chapter_order}`, kind: 'hit', label: t('search.typeChapter'), title: h.chapter_title || h.book_title, meta: h.book_title, href: bookChapterPath(h.book_slug, h.chapter_order, false) };
		}
	}

	const cmdItems = $derived.by<Item[]>(() => {
		const term = q.trim().toLowerCase();
		const list = term ? COMMANDS.filter((c) => c.label.toLowerCase().includes(term)) : COMMANDS;
		return list.map((c) => ({ key: 'cmd:' + c.href, kind: 'cmd', label: t('search.palettePages'), title: c.label, meta: '', href: c.href }));
	});
	// Only once something is typed: the empty palette is the reader's page list,
	// and nineteen admin rows under it would bury it. "admin" lists them all.
	const adminItems = $derived.by<Item[]>(() => {
		const term = q.trim().toLowerCase();
		if (!term || !adminCommands.length) return [];
		const all = 'admin'.startsWith(term) || term.startsWith('admin');
		const list = all ? adminCommands : adminCommands.filter((c) => c.label.toLowerCase().includes(term));
		const sections: Item[] = list.map((c) => ({ key: 'admin:' + c.href, kind: 'cmd', label: 'Admin', title: c.label, meta: '', href: c.href }));
		// A language by name or code opens its admin drill-down ("spanish", "sw").
		const languages: Item[] =
			canOpenWork && term.length >= 2
				? lang.available
						.map((l) => ({ code: l.code, names: [nameOfLanguage(l.code, 'en') ?? l.name, l.name] }))
						.filter((l) => l.code === term || l.names.some((n) => n.toLowerCase().includes(term)))
						.map((l) => ({ key: 'admin:lang:' + l.code, kind: 'cmd', label: 'Admin', title: `Language: ${l.names[0]}`, meta: l.code, href: `/admin/languages/${l.code}` }))
				: [];
		return [...sections, ...languages];
	});
	// Suggestions lead the instant hits: after two letters of "moody" the full
	// search (whole words only) has nothing yet, but the person is already clear.
	const suggestItems = $derived<Item[]>(suggested.map(hitItem));
	const hitItems = $derived.by<Item[]>(() => {
		const seen = new Set(suggestItems.map((i) => i.key));
		return hits.map(hitItem).filter((i) => !seen.has(i.key));
	});

	/**
	 * The FIRST row, which always hands the query to the full search page.
	 *
	 * The palette searches as you type but only shows a handful of instant hits,
	 * and its command list has no /search entry — so a query it missed ended at
	 * "No results" with nowhere to go, even though the real search page stems,
	 * filters and sorts. This is that way out, and it is present whether or not
	 * there were hits: "not in the first five" and "not in the library" look
	 * identical from here.
	 *
	 * It leads rather than trails. Last, it sat under however many instant hits
	 * the query drew — nine passages from one book, in the reported case — so the
	 * one row that reaches the whole library was the one you had to scroll to
	 * find. First, it is also what Enter runs by default, which is the right
	 * default for a query with no obvious single answer.
	 */
	const searchItem = $derived.by<Item[]>(() => {
		const term = q.trim();
		if (!term) return [];
		return [
			{
				key: 'search:all',
				kind: 'cmd',
				label: t('nav.search'),
				title: t('search.showAll'),
				meta: term,
				href: `/search?q=${encodeURIComponent(term)}`
			}
		];
	});

	const items = $derived<Item[]>([
		...searchItem,
		...suggestItems,
		...cmdItems,
		...adminItems,
		...hitItems
	]);
	const activeKey = $derived(items[activeIndex]?.key ?? '');

	// Keep the selection valid as the list changes; keep the active row in view.
	$effect(() => {
		if (activeIndex >= items.length) activeIndex = 0;
	});
	$effect(() => {
		if (paletteUi.open && activeKey)
			document.getElementById(`cmd-${activeKey}`)?.scrollIntoView({ block: 'nearest' });
	});
	$effect(() => {
		if (paletteUi.open) inputEl?.focus();
	});

	function runSearch() {
		clearTimeout(timer);
		clearTimeout(suggestTimer);
		const term = q.trim();
		if (term.length < minQueryLength(getLang())) {
			// Bump the token too. `clearTimeout` only helps while the debounce
			// hasn't fired; a request already in flight still matches `searchSeq`
			// when it lands and repaints the results we just cleared — "prayer"'s
			// hits under a query of "p", which is the exact failure the token
			// exists to prevent.
			searchSeq++;
			hits = [];
			suggested = [];
			return;
		}
		// A sequence token, as the full /search page uses. Without it a slow older
		// request can land after a faster newer one and overwrite it: type
		// "pray" (a cold FTS scan), then "prayer" (cached and quick), and the
		// results for "pray" arrive last and win. The 200 ms debounce narrows
		// that window but does not close it.
		const token = ++searchSeq;
		// Suggestions first, on a shorter fuse: a prefix match over a few hundred
		// names is quick, and it is what answers "where am I heading".
		clearTimeout(suggestTimer);
		suggestTimer = setTimeout(async () => {
			try {
				const res = await searchComplete(term, getLang());
				if (token === searchSeq) suggested = res.results;
			} catch {
				if (token === searchSeq) suggested = [];
			}
		}, 80);
		timer = setTimeout(async () => {
			loading = true;
			try {
				const res = await search(term, getLang());
				if (token === searchSeq) hits = res.results;
			} catch {
				// try/finally with no catch made a failed search an UNHANDLED
				// rejection — nothing awaits this callback — while leaving the
				// previous query's hits on screen under the new term. Clearing
				// says "no results for what you typed", which is at least true.
				if (token === searchSeq) hits = [];
			} finally {
				if (token === searchSeq) loading = false;
			}
		}, 200);
	}

	function onInput() {
		activeIndex = 0;
		runSearch();
	}

	// The reset reacts to the palette OPENING rather than living in one caller's
	// handler: the flag is shared state now, so ⌘K is no longer the only way in
	// — the nav's search button flips it too, and reopening from there used to
	// show the previous query and its (possibly other-locale) hits.
	$effect(() => {
		if (paletteUi.open) {
			// An in-flight debounce from the previous session would land on the
			// fresh palette and repopulate it with the old query's hits — and so
			// would an in-flight FETCH, which `clearTimeout` can't reach. Retire
			// its token as well, or Esc-then-⌘K reopens blank and then fills with
			// the previous query's results, which Enter will happily navigate to.
			clearTimeout(timer);
			clearTimeout(suggestTimer);
			searchSeq++;
			q = '';
			hits = [];
			suggested = [];
			activeIndex = 0;
		}
	});

	function close() {
		paletteUi.close();
	}
	function go(href: string) {
		goto(localizeHref(href));
		close();
	}

	// ⌘K itself is the root layout's: it has to work before this component's
	// code has loaded (the layout mounts it on first open).
	function onWindowKeydown(e: KeyboardEvent) {
		if (e.key === 'Escape' && paletteUi.open) close();
	}

	function onFieldKeydown(e: KeyboardEvent) {
		const n = items.length;
		if (e.key === 'ArrowDown') {
			e.preventDefault();
			if (n) activeIndex = (activeIndex + 1) % n;
		} else if (e.key === 'ArrowUp') {
			e.preventDefault();
			if (n) activeIndex = activeIndex <= 0 ? n - 1 : activeIndex - 1;
		} else if (e.key === 'Enter') {
			e.preventDefault();
			const it = items[activeIndex];
			// ⌘/Ctrl+Enter on a book or sermon opens its admin page instead.
			if (it) go((e.metaKey || e.ctrlKey) && it.admin ? it.admin : it.href);
		}
	}
</script>

<svelte:window onkeydown={onWindowKeydown} />

{#if paletteUi.open}
	<!-- Backdrop. Click closes; keyboard dismissal is the global Escape handler. -->
	<!-- svelte-ignore a11y_click_events_have_key_events a11y_no_static_element_interactions -->
	<div
		class="palette-overlay fixed inset-0 z-(--z-modal) flex items-start justify-center bg-black/40 px-4 pt-[12dvh]"
		use:portal
		role="presentation"
		onclick={close}
	>
		<!-- Panel. focusTrap keeps Tab inside the dialog and returns focus to
		     whatever opened it on close; the field self-focuses (autoFocus:false). -->
		<div
			class="w-full max-w-xl overflow-hidden rounded-card border border-border bg-surface shadow-xl"
			role="dialog"
			aria-modal="true"
			aria-label={t('search.title')}
			tabindex="-1"
			use:focusTrap={{ onEscape: close, autoFocus: false }}
			onclick={(e) => e.stopPropagation()}
		>
			<input
				bind:this={inputEl}
				bind:value={q}
				oninput={onInput}
				onkeydown={onFieldKeydown}
				type="text"
				autocomplete="off"
				spellcheck="false"
				placeholder={t('search.palettePlaceholder')}
				aria-label={t('search.palettePlaceholder')}
				class="w-full border-b border-border bg-transparent px-4 py-4 text-body text-text focus-visible:-outline-offset-2"
			/>

			<div class="max-h-[52dvh] overflow-y-auto py-2">
				{#if items.length === 0}
					<p class="px-4 py-6 text-center text-small text-muted">
						{loading ? '…' : t('search.noResultsShort')}
					</p>
				{:else}
					<ul>
						{#each items as it (it.key)}
							<li class="flex items-stretch" class:bg-surface-2={it.key === activeKey}>
								<a
									id="cmd-{it.key}"
									href={localizeHref(it.href)}
									onclick={(e) => {
										e.preventDefault();
										go(it.href);
									}}
									class="flex min-w-0 flex-1 items-center gap-3 px-4 py-2.5 hover:no-underline"
								>
									<span
										class="eyebrow w-16 shrink-0 text-muted"
									>
										{it.label}
									</span>
									<span class="min-w-0 flex-1">
										<span class="block truncate text-body text-text">{it.title}</span>
										{#if it.meta}<span class="block truncate text-small text-muted">{it.meta}</span>{/if}
									</span>
								</a>
								{#if it.admin}
									<!-- A sibling, not nested: an <a> can't hold another. -->
									<a
										href={localizeHref(it.admin)}
										onclick={(e) => {
											e.preventDefault();
											go(it.admin!);
										}}
										class="flex shrink-0 items-center pe-4 ps-2 text-small text-muted hover:text-accent hover:no-underline"
										aria-label="Open {it.title} in admin"
										title="Open in admin (⌘/Ctrl+Enter)">Admin</a
									>
								{/if}
							</li>
						{/each}
					</ul>
				{/if}
			</div>

			<div class="flex items-center gap-3 border-t border-border px-4 py-2 text-micro text-muted">
				<span>↑↓ {t('search.paletteNavigate')}</span>
				<span>↵ {t('search.paletteOpen')}</span>
				<span>esc {t('search.paletteClose')}</span>
				{#if hitItems.some((i) => i.admin)}<span>⌘↵ admin</span>{/if}
			</div>
		</div>
	</div>
{/if}
