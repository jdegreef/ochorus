<script lang="ts">
	/**
	 * The campaign designer's block list for one language: add, reorder,
	 * duplicate, edit and remove blocks. Blocks that name something in the
	 * library (a book, sermon, plan, article, author or topic — or a row of up to
	 * three books) are picked from a search that shows every language it reaches,
	 * so it's clear before sending whether this language's readers will see the
	 * block — one with nothing in the email's language is left out of it (there
	 * is no English fallback).
	 */
	import { apiErrorDetail } from '$lib/api';
	import { hydrateSrc } from '$lib/hydrateSrc';
	import {
		HERO_COLORS,
		searchEmailLibrary,
		uploadEmailImage,
		type EmailBlock,
		type EmailBlockType,
		type EmailLibraryItem,
		type LibraryBlockType
	} from '$lib/library-admin';

	let {
		blocks = $bindable(),
		locale,
		localeName = locale,
		disabled = false
	}: { blocks: EmailBlock[]; locale: string; localeName?: string; disabled?: boolean } = $props();

	const GROUPS: { label: string; types: { type: EmailBlockType; label: string }[] }[] = [
		{
			label: 'Layout',
			types: [
				{ type: 'heading', label: 'Heading' },
				{ type: 'text', label: 'Text' },
				{ type: 'button', label: 'Button' },
				{ type: 'image', label: 'Image' },
				{ type: 'hero', label: 'Hero banner' },
				{ type: 'quote', label: 'Quote' },
				{ type: 'scripture', label: 'Scripture' },
				{ type: 'divider', label: 'Divider' },
				{ type: 'spacer', label: 'Spacer' }
			]
		},
		{
			label: 'From the site',
			types: [
				{ type: 'book', label: 'Book' },
				{ type: 'book_row', label: 'Book row' },
				{ type: 'sermon', label: 'Sermon' },
				{ type: 'plan', label: 'Reading plan' },
				{ type: 'article', label: 'Article' },
				{ type: 'author', label: 'Author' },
				{ type: 'topic', label: 'Topic' },
				{ type: 'continue_reading', label: 'Continue reading' }
			]
		}
	];
	const TYPES = GROUPS.flatMap((g) => g.types);
	const typeLabel = (t: EmailBlockType) => TYPES.find((x) => x.type === t)?.label ?? t;
	const LIBRARY = new Set<EmailBlockType>(['book', 'sermon', 'plan', 'article', 'author', 'topic']);
	type LibraryBlock = Extract<EmailBlock, { slug: string }>;
	type RowBlock = Extract<EmailBlock, { type: 'book_row' }>;
	const isLibrary = (b: EmailBlock): b is LibraryBlock => LIBRARY.has(b.type);
	const keyOf = (type: LibraryBlockType, slug: string) => `${type}:${slug}`;
	const rowSlugs = (b: RowBlock) =>
		b.slugs
			.split(',')
			.map((s) => s.trim())
			.filter(Boolean);
	const ROW_MAX = 3;

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
			case 'continue_reading':
				return { type, heading: '', label: '' };
			case 'image':
				return { type, url: '', alt: '', path: '', caption: '' };
			case 'hero':
				return { type, eyebrow: '', title: '', text: '', image: '', color: 'navy', label: '', path: '' };
			case 'book_row':
				return { type, slugs: '', label: '' };
			case 'spacer':
				return { type, size: 'medium' };
			case 'scripture':
				return { type, text: '', reference: '' };
			default:
				return { type, slug: '', label: '' };
		}
	}

	function add(type: EmailBlockType) {
		blocks = [...blocks, blank(type)];
		if (LIBRARY.has(type) || type === 'book_row') openPicker(blocks.length - 1);
	}
	function move(i: number, by: number) {
		const j = i + by;
		if (j < 0 || j >= blocks.length) return;
		const next = [...blocks];
		[next[i], next[j]] = [next[j], next[i]];
		blocks = next;
		picking = null; // the picker is tied to a position; don't let it follow the wrong block
	}
	function duplicate(i: number) {
		blocks = [...blocks.slice(0, i + 1), $state.snapshot(blocks[i]) as EmailBlock, ...blocks.slice(i + 1)];
		picking = null;
	}
	function remove(i: number) {
		blocks = blocks.filter((_, k) => k !== i);
		picking = null;
	}

	// --- Library picker (one open at a time) ---------------------------------
	let picking = $state<number | null>(null);
	let query = $state('');
	let results = $state<EmailLibraryItem[]>([]);
	let searching = $state(false);
	// What each chosen slug is, so a block shows its title and languages.
	let known = $state<Record<string, EmailLibraryItem>>({});
	let timer: ReturnType<typeof setTimeout> | undefined;
	let inflight: AbortController | undefined;

	/** What a block searches: its own type, or books for a book row. */
	const pickType = (b: EmailBlock): LibraryBlockType | null =>
		isLibrary(b) ? b.type : b.type === 'book_row' ? 'book' : null;

	function openPicker(i: number) {
		inflight?.abort(); // results for another block (maybe another type) must not linger
		results = [];
		picking = i;
		query = '';
		search();
	}

	function search() {
		clearTimeout(timer);
		const i = picking;
		if (i === null) return;
		const type = pickType(blocks[i]);
		if (!type) return;
		timer = setTimeout(async () => {
			inflight?.abort(); // a newer query supersedes an older one
			const controller = (inflight = new AbortController());
			searching = true;
			try {
				results = (await searchEmailLibrary(type, query, { signal: controller.signal })).results;
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
		const type = pickType(b);
		if (!type) return;
		known = { ...known, [keyOf(type, item.slug)]: item };
		if (b.type === 'book_row') {
			const slugs = rowSlugs(b);
			if (!slugs.includes(item.slug)) slugs.push(item.slug);
			blocks[picking] = { ...b, slugs: slugs.slice(0, ROW_MAX).join(',') };
			if (slugs.length >= ROW_MAX) picking = null;
			return;
		}
		blocks[picking] = { ...(b as LibraryBlock), slug: item.slug };
		picking = null;
	}

	function dropFromRow(i: number, slug: string) {
		const b = blocks[i];
		if (b.type !== 'book_row') return;
		blocks[i] = { ...b, slugs: rowSlugs(b).filter((s) => s !== slug).join(',') };
	}

	// Name what a saved design already points at: one exact lookup per type,
	// for whichever slugs aren't known yet.
	$effect(() => {
		const missing = new Map<LibraryBlockType, string[]>();
		const want = (type: LibraryBlockType, slug: string) => {
			if (!slug || known[keyOf(type, slug)]) return;
			missing.set(type, [...(missing.get(type) ?? []), slug]);
		};
		for (const b of blocks) {
			if (isLibrary(b)) want(b.type, b.slug);
			else if (b.type === 'book_row') rowSlugs(b).forEach((s) => want('book', s));
		}
		for (const [type, slugs] of missing) {
			// Mark them as asked-for first, so this effect doesn't ask twice.
			const pending = Object.fromEntries(
				slugs.map((slug) => [keyOf(type, slug), { slug, title: slug, author: '', languages: [] }])
			);
			known = { ...known, ...pending };
			searchEmailLibrary(type, '', { slugs })
				.then((r) => {
					known = { ...known, ...Object.fromEntries(r.results.map((x) => [keyOf(type, x.slug), x])) };
				})
				.catch(() => {});
		}
	});

	// --- Image upload ------------------------------------------------------------
	let uploading = $state<number | null>(null);
	let uploadError = $state('');

	async function upload(i: number, field: 'url' | 'image', input: HTMLInputElement) {
		const file = input.files?.[0];
		input.value = '';
		if (!file) return;
		uploading = i;
		uploadError = '';
		const target = blocks[i];
		try {
			const url = await uploadEmailImage(file);
			// Blocks may have moved (or this one been removed) while it uploaded:
			// put the picture on the block it was chosen for, wherever it is now.
			const at = blocks.indexOf(target);
			if (at >= 0) blocks[at] = { ...blocks[at], [field]: url } as EmailBlock;
		} catch (e) {
			uploadError = apiErrorDetail(e, "Couldn't upload that picture.");
		} finally {
			uploading = null;
		}
	}
</script>

{#snippet reach(item: EmailLibraryItem | undefined)}
	{#if item && item.languages.length}
		{#if item.languages.includes(locale)}
			<span class="text-micro text-accent">In {localeName}</span>
		{:else}
			<span class="text-micro text-warning">Not in {localeName} — left out of this email</span>
		{/if}
	{/if}
{/snippet}

{#snippet imageField(i: number, field: 'url' | 'image', value: string, label: string)}
	<div class="flex flex-wrap items-center gap-2">
		{#if value}
			<!-- An admin-chosen https URL or site path, shown as a thumbnail only. -->
			<img src={value} alt="" use:hydrateSrc={{ src: value }} class="h-14 w-20 rounded border border-border object-cover" />
		{/if}
		<input class="min-w-0 flex-1 rounded-md border border-border bg-surface p-2 text-small" aria-label={label} value={value} oninput={(e) => (blocks[i] = { ...blocks[i], [field]: (e.currentTarget as HTMLInputElement).value } as EmailBlock)} {disabled} placeholder="https://… or a site path like /covers/humility-2.png" />
		{#if !disabled}
			<label class="btn btn-ghost btn-sm cursor-pointer">
				{uploading === i ? 'Uploading…' : 'Upload'}
				<input class="sr-only" type="file" accept="image/png,image/jpeg,image/gif,image/webp" onchange={(e) => upload(i, field, e.currentTarget as HTMLInputElement)} disabled={uploading !== null} />
			</label>
		{/if}
	</div>
{/snippet}

<div class="space-y-3">
	{#if uploadError}<p class="rounded-md bg-danger/10 p-2 text-small text-danger">{uploadError}</p>{/if}
	{#each blocks as b, i (i)}
		<div class="rounded-md border border-border bg-surface p-3">
			<div class="mb-2 flex items-center justify-between gap-2">
				<span class="text-micro font-semibold uppercase tracking-wide text-muted">{typeLabel(b.type)}</span>
				{#if !disabled}
					<span class="flex gap-1">
						<button class="btn btn-ghost btn-sm" aria-label="Move up" onclick={() => move(i, -1)} disabled={i === 0 || uploading !== null}>↑</button>
						<button class="btn btn-ghost btn-sm" aria-label="Move down" onclick={() => move(i, 1)} disabled={i === blocks.length - 1 || uploading !== null}>↓</button>
						<button class="btn btn-ghost btn-sm" aria-label="Duplicate block" onclick={() => duplicate(i)}>⧉</button>
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
			{:else if b.type === 'scripture'}
				<textarea class="mb-2 h-20 w-full rounded-md border border-border bg-surface p-2 text-body italic" aria-label="Verse" bind:value={b.text} {disabled} placeholder="The verse, in this email's language"></textarea>
				<input class="w-full rounded-md border border-border bg-surface p-2 text-small" aria-label="Reference" bind:value={b.reference} {disabled} placeholder="Reference, e.g. 1 Thessalonians 5:18" />
			{:else if b.type === 'divider'}
				<hr class="border-border" />
			{:else if b.type === 'spacer'}
				<div role="group" aria-label="Spacer height" class="flex gap-1">
					{#each ['small', 'medium', 'large'] as const as size (size)}
						<button class="rounded-full border px-2.5 py-0.5 text-micro {b.size === size ? 'border-accent bg-accent-soft text-accent' : 'border-border text-muted'}" aria-pressed={b.size === size} onclick={() => (b.size = size)} {disabled}>{size}</button>
					{/each}
				</div>
			{:else if b.type === 'continue_reading'}
				<p class="mb-2 text-small text-muted">Each reader’s own book in progress, at the chapter they reached. Left out for a reader with nothing in progress.</p>
				<input class="mb-2 w-full rounded-md border border-border bg-surface p-2 text-small" aria-label="Heading above the card" bind:value={b.heading} {disabled} placeholder="Heading above the card, e.g. Continue reading" />
				<input class="w-full rounded-md border border-border bg-surface p-2 text-small" aria-label="Link label" bind:value={b.label} {disabled} placeholder="Link label, e.g. Pick up at chapter {'{chapter}'}" />
			{:else if b.type === 'image'}
				{@render imageField(i, 'url', b.url, 'Image address')}
				<div class="mt-2 grid grid-cols-1 gap-2 sm:grid-cols-2">
					<input class="rounded-md border border-border bg-surface p-2 text-small" aria-label="Image description" bind:value={b.alt} {disabled} placeholder="Description, for readers who can't see it" />
					<input class="rounded-md border border-border bg-surface p-2 text-small" aria-label="Image link path" bind:value={b.path} {disabled} placeholder="Link path (optional), e.g. books" />
				</div>
				<input class="mt-2 w-full rounded-md border border-border bg-surface p-2 text-small" aria-label="Caption" bind:value={b.caption} {disabled} placeholder="Caption (optional)" />
			{:else if b.type === 'hero'}
				<div role="group" aria-label="Banner colour" class="mb-2 flex flex-wrap items-center gap-1.5">
					{#each Object.entries(HERO_COLORS) as [name, hex] (name)}
						<button class="h-7 w-7 rounded-full border-2 {b.color === name ? 'border-text' : 'border-transparent'}" style="background: {hex}" aria-label="{name} banner" aria-pressed={b.color === name} onclick={() => (b.color = name as typeof b.color)} {disabled}></button>
					{/each}
				</div>
				<input class="mb-2 w-full rounded-md border border-border bg-surface p-2 text-small" aria-label="Small line above the title" bind:value={b.eyebrow} {disabled} placeholder="Small line above the title (optional), e.g. November" />
				<input class="mb-2 w-full rounded-md border border-border bg-surface p-2 text-body font-semibold" aria-label="Banner title" bind:value={b.title} {disabled} placeholder="Title" />
				<textarea class="mb-2 h-16 w-full rounded-md border border-border bg-surface p-2 text-small" aria-label="Banner text" bind:value={b.text} {disabled} placeholder="A sentence or two (optional)"></textarea>
				{@render imageField(i, 'image', b.image, 'Banner picture')}
				<div class="mt-2 grid grid-cols-1 gap-2 sm:grid-cols-2">
					<input class="rounded-md border border-border bg-surface p-2 text-small" aria-label="Banner button label" bind:value={b.label} {disabled} placeholder="Button label (optional)" />
					<input class="rounded-md border border-border bg-surface p-2 text-small" aria-label="Banner button link path" bind:value={b.path} {disabled} placeholder="Link path, e.g. plans" />
				</div>
			{:else if b.type === 'book_row'}
				<ul class="mb-2 space-y-1">
					{#each rowSlugs(b) as slug (slug)}
						{@const item = known[keyOf('book', slug)]}
						<li class="flex flex-wrap items-baseline justify-between gap-2 text-small">
							<span><span class="font-semibold text-text">{item?.title ?? slug}</span>{#if item?.author}<span class="text-muted"> · {item.author}</span>{/if}</span>
							<span class="flex items-center gap-2">
								{@render reach(item)}
								{#if !disabled}<button class="btn btn-ghost btn-sm text-danger" aria-label="Remove {item?.title ?? slug} from the row" onclick={() => dropFromRow(i, slug)}>✕</button>{/if}
							</span>
						</li>
					{/each}
				</ul>
				{#if !disabled && rowSlugs(b).length < ROW_MAX && picking !== i}
					<button class="btn btn-ghost btn-sm" onclick={() => openPicker(i)}>Add a book ({rowSlugs(b).length} of {ROW_MAX})</button>
				{/if}
			{:else if isLibrary(b)}
				{@const item = b.slug ? known[keyOf(b.type, b.slug)] : undefined}
				{#if b.slug}
					<div class="mb-2 flex flex-wrap items-baseline justify-between gap-2">
						<span class="text-body text-text">
							<span class="font-semibold">{item?.title ?? b.slug}</span>
							{#if item?.author}<span class="text-small text-muted"> · {item.author}</span>{/if}
						</span>
						{@render reach(item)}
					</div>
				{/if}
				{#if !disabled && picking !== i}
					<button class="btn btn-ghost btn-sm" onclick={() => openPicker(i)}>{b.slug ? 'Change' : `Choose ${b.type === 'author' ? 'an' : 'a'} ${typeLabel(b.type).toLowerCase()}`}</button>
				{/if}
			{/if}

			{#if !disabled && picking === i}
				<input class="my-2 w-full rounded-md border border-border bg-surface p-2 text-small" aria-label="Search the library" bind:value={query} oninput={search} placeholder="Search by title" />
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
				<button class="btn btn-ghost btn-sm mt-1" onclick={() => (picking = null)}>Done</button>
			{/if}

			{#if !disabled && (isLibrary(b) || b.type === 'book_row')}
				<input class="mt-2 w-full rounded-md border border-border bg-surface p-2 text-small" aria-label="Link label" bind:value={b.label} {disabled} placeholder="Link label under the card (optional), e.g. Start reading" />
			{/if}
		</div>
	{/each}

	{#if !disabled}
		<div class="space-y-1.5">
			{#each GROUPS as g (g.label)}
				<div class="flex flex-wrap gap-1.5">
					<span class="me-1 w-24 self-center text-micro text-muted">Add · {g.label}</span>
					{#each g.types as t (t.type)}
						<button class="rounded-full border border-border px-2.5 py-1 text-micro text-text hover:border-accent hover:text-accent" onclick={() => add(t.type)}>+ {t.label}</button>
					{/each}
				</div>
			{/each}
		</div>
	{/if}
</div>
