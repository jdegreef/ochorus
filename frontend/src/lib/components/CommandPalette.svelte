<script lang="ts">
	import { search, type SearchHit } from '$lib/library';
	import { getLang } from '$lib/lang.svelte';
	import { i18n } from '$lib/i18n.svelte';
	import { localizeHref } from '$lib/href';
	import { focusTrap } from '$lib/actions/focusTrap';
	import { goto } from '$app/navigation';

	const t = i18n.t;

	let open = $state(false);
	let q = $state('');
	let hits = $state<SearchHit[]>([]);
	let loading = $state(false);
	let activeIndex = $state(0);
	let inputEl = $state<HTMLInputElement>();
	let timer: ReturnType<typeof setTimeout> | undefined;

	// Quick-nav destinations — the app's primary pages, jumpable by name.
	const COMMANDS = $derived([
		{ href: '/', label: t('nav.home') },
		{ href: '/books', label: t('nav.books') },
		{ href: '/topics', label: t('nav.topics') },
		{ href: '/plans', label: t('nav.plans') },
		{ href: '/sermons', label: t('nav.sermons') },
		{ href: '/biographies', label: t('nav.biographies') },
		{ href: '/notebook', label: t('notebook.title') },
		{ href: '/settings', label: t('settings.title') },
		{ href: '/about', label: t('nav.about') },
		{ href: '/contact', label: t('nav.contact') }
	]);

	type Item = { key: string; kind: 'cmd' | 'hit'; label: string; title: string; meta: string; href: string };

	function hitItem(h: SearchHit): Item {
		switch (h.type) {
			case 'author':
				return { key: 'author:' + h.author_slug, kind: 'hit', label: t('search.typeAuthor'), title: h.author_name, meta: '', href: `/authors/${h.author_slug}` };
			case 'book':
				return { key: 'book:' + h.book_slug, kind: 'hit', label: t('search.typeBook'), title: h.book_title, meta: h.author_name, href: `/books/${h.book_slug}` };
			case 'topic':
				return { key: 'topic:' + h.topic_slug, kind: 'hit', label: t('search.typeTopic'), title: h.topic_title, meta: '', href: `/topics/${h.topic_slug}` };
			case 'plan':
				return { key: 'plan:' + h.plan_slug, kind: 'hit', label: t('search.typePlan'), title: h.plan_title, meta: '', href: `/plans/${h.plan_slug}` };
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
	const items = $derived<Item[]>([...cmdItems, ...hitItems]);
	const activeKey = $derived(items[activeIndex]?.key ?? '');

	// Keep the selection valid as the list changes; keep the active row in view.
	$effect(() => {
		if (activeIndex >= items.length) activeIndex = 0;
	});
	$effect(() => {
		if (open && activeKey) document.getElementById(`cmd-${activeKey}`)?.scrollIntoView({ block: 'nearest' });
	});
	$effect(() => {
		if (open) inputEl?.focus();
	});

	function runSearch() {
		clearTimeout(timer);
		const term = q.trim();
		if (term.length < 2) {
			hits = [];
			return;
		}
		timer = setTimeout(async () => {
			loading = true;
			try {
				const res = await search(term, getLang());
				hits = res.results;
			} finally {
				loading = false;
			}
		}, 200);
	}

	function onInput() {
		activeIndex = 0;
		runSearch();
	}

	function openPalette() {
		open = true;
		q = '';
		hits = [];
		activeIndex = 0;
	}
	function close() {
		open = false;
	}
	function go(href: string) {
		goto(localizeHref(href));
		close();
	}

	function onWindowKeydown(e: KeyboardEvent) {
		if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'k') {
			e.preventDefault();
			open ? close() : openPalette();
		} else if (e.key === 'Escape' && open) {
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

{#if open}
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
				class="w-full border-b border-border bg-transparent px-4 py-3.5 text-body text-text focus-visible:-outline-offset-2"
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
										class="w-16 shrink-0 text-[0.66rem] font-semibold uppercase tracking-wide text-muted"
									>
										{it.kind === 'cmd' ? t('search.palettePages') : it.label}
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

			<div class="flex items-center gap-3 border-t border-border px-4 py-2 text-[0.7rem] text-muted">
				<span>↑↓ {t('search.paletteNavigate')}</span>
				<span>↵ {t('search.paletteOpen')}</span>
				<span>esc {t('search.paletteClose')}</span>
			</div>
		</div>
	</div>
{/if}
