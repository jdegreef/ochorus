<script lang="ts">
	import { search, scripturePageHref, type SearchHit } from '$lib/library-public';
	import { authorPath } from '$lib/originals';
	import { PRIMARY_NAV, ENGLISH_HUBS, ORIGINALS_DEST } from '$lib/contentNav';
	import { getLang } from '$lib/lang.svelte';
	import { i18n } from '$lib/i18n.svelte';
	import { localizeHref } from '$lib/href';
	import { focusTrap } from '$lib/actions/focusTrap';
	import { goto } from '$app/navigation';
	import { paletteUi } from '$lib/paletteUi.svelte';

	const t = i18n.t;

	let q = $state('');
	let hits = $state<SearchHit[]>([]);
	let loading = $state(false);
	let activeIndex = $state(0);
	let inputEl = $state<HTMLInputElement>();
	let timer: ReturnType<typeof setTimeout> | undefined;
	/** Monotonic token so only the newest in-flight search may write `hits`. */
	let searchSeq = 0;

	// Quick-nav destinations — the app's primary pages, jumpable by name.
	// Home, then the content types in PRIMARY_NAV order (shared with the top nav
	// and footer so the three can't drift — F2), then the English-only hubs on
	// the same gate as the footer (in another locale they would jump to a page
	// with nothing on it; ungate when translated), then the utility pages.
	const COMMANDS = $derived([
		{ href: '/', label: t('nav.home') },
		...PRIMARY_NAV.map((d) => ({ href: d.href, label: t(d.labelKey) })),
		...(getLang() === 'en'
			? ENGLISH_HUBS.map((d) => ({ href: d.href, label: t(d.labelKey) }))
			: []),
		{ href: ORIGINALS_DEST.href, label: t(ORIGINALS_DEST.labelKey) },
		{ href: '/notebook', label: t('notebook.title') },
		{ href: '/settings', label: t('settings.title') },
		{ href: '/about', label: t('nav.about') },
		{ href: '/contact', label: t('nav.contact') }
	]);

	type Item = { key: string; kind: 'cmd' | 'hit'; label: string; title: string; meta: string; href: string };

	function hitItem(h: SearchHit): Item {
		switch (h.type) {
			case 'author':
				return { key: 'author:' + h.author_slug, kind: 'hit', label: t('search.typeAuthor'), title: h.author_name, meta: '', href: authorPath(h.author_slug) };
			case 'book':
				return { key: 'book:' + h.book_slug, kind: 'hit', label: t('search.typeBook'), title: h.book_title, meta: h.author_name, href: `/books/${h.book_slug}` };
			case 'topic':
				return { key: 'topic:' + h.topic_slug, kind: 'hit', label: t('search.typeTopic'), title: h.topic_title, meta: '', href: `/topics/${h.topic_slug}` };
			case 'plan':
				return { key: 'plan:' + h.plan_slug, kind: 'hit', label: t('search.typePlan'), title: h.plan_title, meta: '', href: `/plans/${h.plan_slug}` };
			case 'article':
				return { key: 'article:' + h.article_slug, kind: 'hit', label: t('search.typeArticle'), title: h.article_title, meta: '', href: `/articles/${h.article_slug}` };
			case 'scripture':
				return { key: `scripture:${h.book_slug}:${h.chapter}:${h.verse ?? ''}`, kind: 'hit', label: t('search.typeScripture'), title: h.reference, meta: '', href: scripturePageHref(h.book_slug, h.chapter, h.verse) };
			case 'sermon':
				return { key: 'sermon:' + h.sermon_slug, kind: 'hit', label: t('search.typeSermon'), title: h.sermon_title, meta: h.author_name, href: `/sermons/${h.sermon_slug}` };
			default:
				return { key: `chapter:${h.book_slug}:${h.chapter_order}`, kind: 'hit', label: t('search.typeChapter'), title: h.chapter_title || h.book_title, meta: h.book_title, href: `/books/${h.book_slug}/${h.chapter_order}` };
		}
	}

	const cmdItems = $derived.by<Item[]>(() => {
		const term = q.trim().toLowerCase();
		const list = term ? COMMANDS.filter((c) => c.label.toLowerCase().includes(term)) : COMMANDS;
		return list.map((c) => ({ key: 'cmd:' + c.href, kind: 'cmd', label: t('search.palettePages'), title: c.label, meta: '', href: c.href }));
	});
	const hitItems = $derived<Item[]>(hits.map(hitItem));

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

	const items = $derived<Item[]>([...searchItem, ...cmdItems, ...hitItems]);
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
		const term = q.trim();
		if (term.length < 2) {
			// Bump the token too. `clearTimeout` only helps while the debounce
			// hasn't fired; a request already in flight still matches `searchSeq`
			// when it lands and repaints the results we just cleared — "prayer"'s
			// hits under a query of "p", which is the exact failure the token
			// exists to prevent.
			searchSeq++;
			hits = [];
			return;
		}
		// A sequence token, as the full /search page uses. Without it a slow older
		// request can land after a faster newer one and overwrite it: type
		// "pray" (a cold FTS scan), then "prayer" (cached and quick), and the
		// results for "pray" arrive last and win. The 200 ms debounce narrows
		// that window but does not close it.
		const token = ++searchSeq;
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
			searchSeq++;
			q = '';
			hits = [];
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

	function onWindowKeydown(e: KeyboardEvent) {
		if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'k') {
			e.preventDefault();
			paletteUi.toggle();
		} else if (e.key === 'Escape' && paletteUi.open) {
			close();
		}
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
			if (it) go(it.href);
		}
	}
</script>

<svelte:window onkeydown={onWindowKeydown} />

{#if paletteUi.open}
	<!-- Backdrop. Click closes; keyboard dismissal is the global Escape handler. -->
	<!-- svelte-ignore a11y_click_events_have_key_events a11y_no_static_element_interactions -->
	<div
		class="fixed inset-0 z-50 flex items-start justify-center bg-black/40 px-4 pt-[12vh]"
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

			<div class="max-h-[52vh] overflow-y-auto py-2">
				{#if items.length === 0}
					<p class="px-4 py-6 text-center text-small text-muted">
						{loading ? '…' : t('search.noResultsShort')}
					</p>
				{:else}
					<ul>
						{#each items as it (it.key)}
							<li>
								<a
									id="cmd-{it.key}"
									href={localizeHref(it.href)}
									onclick={(e) => {
										e.preventDefault();
										go(it.href);
									}}
									class="flex items-center gap-3 px-4 py-2.5 hover:no-underline"
									class:bg-surface-2={it.key === activeKey}
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
							</li>
						{/each}
					</ul>
				{/if}
			</div>

			<div class="flex items-center gap-3 border-t border-border px-4 py-2 text-micro text-muted">
				<span>↑↓ {t('search.paletteNavigate')}</span>
				<span>↵ {t('search.paletteOpen')}</span>
				<span>esc {t('search.paletteClose')}</span>
			</div>
		</div>
	</div>
{/if}
