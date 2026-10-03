<script lang="ts">
	/**
	 * The campaign designer's block list for one language: add, reorder, edit and
	 * remove blocks. Library blocks (book / sermon / plan) are picked from a search
	 * that shows every language a work is published in, so it's clear before
	 * sending whether this language's readers will see the block — a work with no
	 * edition in the email's language is left out of it (there is no English
	 * fallback).
	 */
	import {
		searchEmailLibrary,
		type EmailBlock,
		type EmailBlockType,
		type EmailLibraryItem
	} from '$lib/library-admin';

	let {
		blocks = $bindable(),
		locale,
		localeName = locale,
		disabled = false
	}: { blocks: EmailBlock[]; locale: string; localeName?: string; disabled?: boolean } = $props();

	const TYPES: { type: EmailBlockType; label: string }[] = [
		{ type: 'heading', label: 'Heading' },
		{ type: 'text', label: 'Text' },
		{ type: 'button', label: 'Button' },
		{ type: 'quote', label: 'Quote' },
		{ type: 'divider', label: 'Divider' },
		{ type: 'book', label: 'Book' },
		{ type: 'sermon', label: 'Sermon' },
		{ type: 'plan', label: 'Reading plan' }
	];
	const typeLabel = (t: EmailBlockType) => TYPES.find((x) => x.type === t)?.label ?? t;
	const LIBRARY = new Set<EmailBlockType>(['book', 'sermon', 'plan']);
	type LibraryBlock = Extract<EmailBlock, { slug: string }>;
	const isLibrary = (b: EmailBlock): b is LibraryBlock => LIBRARY.has(b.type);
	const keyOf = (b: LibraryBlock) => `${b.type}:${b.slug}`;

	function blank(type: EmailBlockType): EmailBlock {
		switch (type) {
			case 'heading':
			case 'text':
				return { type, text: '' };
			case 'button':
				return { type, label: '', path: '' };
			case 'quote':
				return { type, text: '', attribution: '' };
			case 'divider':
				return { type };
			default:
				return { type, slug: '', label: '' };
		}
	}

	function add(type: EmailBlockType) {
		blocks = [...blocks, blank(type)];
		if (LIBRARY.has(type)) openPicker(blocks.length - 1);
	}
	function move(i: number, by: number) {
		const j = i + by;
		if (j < 0 || j >= blocks.length) return;
		const next = [...blocks];
		[next[i], next[j]] = [next[j], next[i]];
		blocks = next;
	}
	function remove(i: number) {
		blocks = blocks.filter((_, k) => k !== i);
		if (picking === i) picking = null;
	}

	// --- Library picker (one open at a time) ---------------------------------
	let picking = $state<number | null>(null);
	let query = $state('');
	let results = $state<EmailLibraryItem[]>([]);
	let searching = $state(false);
	// What each chosen slug is, so a block shows its title and editions.
	let known = $state<Record<string, EmailLibraryItem>>({});
	let timer: ReturnType<typeof setTimeout> | undefined;

	function openPicker(i: number) {
		picking = i;
		query = '';
		search();
	}

	let inflight: AbortController | undefined;

	function search() {
		clearTimeout(timer);
		const i = picking;
		if (i === null) return;
		const b = blocks[i];
		if (!isLibrary(b)) return;
		timer = setTimeout(async () => {
			inflight?.abort(); // a newer query supersedes an older one
			const controller = (inflight = new AbortController());
			searching = true;
			try {
				results = (await searchEmailLibrary(b.type, query, { signal: controller.signal })).results;
			} catch {
				if (!controller.signal.aborted) results = [];
			} finally {
				if (!controller.signal.aborted) searching = false;
			}
		}, 250);
	}

	function choose(item: EmailLibraryItem) {
		if (picking === null) return;
		const b = blocks[picking];
		if (!isLibrary(b)) return;
		const chosen = { ...b, slug: item.slug };
		known = { ...known, [keyOf(chosen)]: item };
		blocks[picking] = chosen;
		picking = null;
	}

	// Name the works a saved design already points at: one exact lookup per
	// library type, for whichever slugs aren't known yet.
	$effect(() => {
		const missing = new Map<LibraryBlock['type'], string[]>();
		for (const b of blocks) {
			if (!isLibrary(b) || !b.slug || known[keyOf(b)]) continue;
			missing.set(b.type, [...(missing.get(b.type) ?? []), b.slug]);
		}
		for (const [type, slugs] of missing) {
			// Mark them as asked-for first, so this effect doesn't ask twice.
			const pending = Object.fromEntries(
				slugs.map((slug) => [`${type}:${slug}`, { slug, title: slug, author: '', languages: [] }])
			);
			known = { ...known, ...pending };
			searchEmailLibrary(type, '', { slugs })
				.then((r) => {
					known = { ...known, ...Object.fromEntries(r.results.map((x) => [`${type}:${x.slug}`, x])) };
				})
				.catch(() => {});
		}
	});
</script>

<div class="space-y-3">
	{#each blocks as b, i (i)}
		<div class="rounded-md border border-border bg-surface p-3">
			<div class="mb-2 flex items-center justify-between gap-2">
				<span class="text-micro font-semibold uppercase tracking-wide text-muted">{typeLabel(b.type)}</span>
				{#if !disabled}
					<span class="flex gap-1">
						<button class="btn btn-ghost btn-sm" aria-label="Move up" onclick={() => move(i, -1)} disabled={i === 0}>↑</button>
						<button class="btn btn-ghost btn-sm" aria-label="Move down" onclick={() => move(i, 1)} disabled={i === blocks.length - 1}>↓</button>
						<button class="btn btn-ghost btn-sm text-danger" aria-label="Remove block" onclick={() => remove(i)}>✕</button>
					</span>
				{/if}
			</div>

			{#if b.type === 'heading'}
				<input class="w-full rounded-md border border-border bg-surface p-2 text-body font-semibold" aria-label="Heading" bind:value={b.text} {disabled} placeholder="A heading" />
			{:else if b.type === 'text'}
				<textarea class="h-28 w-full rounded-md border border-border bg-surface p-2 text-body" aria-label="Text" bind:value={b.text} {disabled} placeholder="Write here. A blank line starts a new paragraph. {'{name}'} becomes the reader's first name."></textarea>
			{:else if b.type === 'button'}
				<div class="grid grid-cols-1 gap-2 sm:grid-cols-2">
					<input class="rounded-md border border-border bg-surface p-2 text-small" aria-label="Button label" bind:value={b.label} {disabled} placeholder="Button label" />
					<input class="rounded-md border border-border bg-surface p-2 text-small" aria-label="Button link path" bind:value={b.path} {disabled} placeholder="Link path, e.g. plans/humility-12-days" />
				</div>
			{:else if b.type === 'quote'}
				<textarea class="mb-2 h-20 w-full rounded-md border border-border bg-surface p-2 text-body italic" aria-label="Quote" bind:value={b.text} {disabled} placeholder="The quotation"></textarea>
				<input class="w-full rounded-md border border-border bg-surface p-2 text-small" aria-label="Attribution" bind:value={b.attribution} {disabled} placeholder="Who said it, and where" />
			{:else if b.type === 'divider'}
				<hr class="border-border" />
			{:else if isLibrary(b)}
				{@const item = b.slug ? known[keyOf(b)] : undefined}
				{#if b.slug}
					<div class="mb-2 flex flex-wrap items-baseline justify-between gap-2">
						<span class="text-body text-text">
							<span class="font-semibold">{item?.title ?? b.slug}</span>
							{#if item?.author}<span class="text-small text-muted"> · {item.author}</span>{/if}
						</span>
						{#if item && item.languages.length}
							{#if item.languages.includes(locale)}
								<span class="text-micro text-accent">Has a {localeName} edition</span>
							{:else}
								<span class="text-micro text-warning">No {localeName} edition — left out of this email</span>
							{/if}
						{/if}
					</div>
				{/if}
				{#if !disabled}
					{#if picking === i}
						<input class="mb-2 w-full rounded-md border border-border bg-surface p-2 text-small" aria-label="Search the library" bind:value={query} oninput={search} placeholder="Search by title" />
						{#if searching}<p class="text-small text-muted">Searching…</p>{/if}
						<ul class="max-h-56 divide-y divide-border/60 overflow-y-auto">
							{#each results as r (r.slug)}
								<li>
									<button class="w-full p-2 text-start hover:bg-surface-2" onclick={() => choose(r)}>
										<span class="text-small font-semibold text-text">{r.title}</span>
										{#if r.author}<span class="text-micro text-muted"> · {r.author}</span>{/if}
										<span class="block text-micro {r.languages.includes(locale) ? 'text-muted' : 'text-warning'}">{r.languages.join(' · ')}</span>
									</button>
								</li>
							{/each}
						</ul>
						{#if !searching && !results.length}<p class="text-small text-muted">Nothing found.</p>{/if}
					{:else}
						<button class="btn btn-ghost btn-sm" onclick={() => openPicker(i)}>{b.slug ? 'Change' : `Choose a ${typeLabel(b.type).toLowerCase()}`}</button>
					{/if}
					<input class="mt-2 w-full rounded-md border border-border bg-surface p-2 text-small" aria-label="Link label" bind:value={b.label} {disabled} placeholder="Link label under the card (optional), e.g. Start reading" />
				{/if}
			{/if}
		</div>
	{/each}

	{#if !disabled}
		<div class="flex flex-wrap gap-1.5">
			<span class="me-1 self-center text-micro text-muted">Add</span>
			{#each TYPES as t (t.type)}
				<button class="rounded-full border border-border px-2.5 py-1 text-micro text-text hover:border-accent hover:text-accent" onclick={() => add(t.type)}>+ {t.label}</button>
			{/each}
		</div>
	{/if}
</div>
