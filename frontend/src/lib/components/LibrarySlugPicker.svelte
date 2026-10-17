<script lang="ts">
	/**
	 * Pick one book, plan or author by searching the library; the value is its
	 * slug. Shows the chosen item's title, and a Clear button when optional.
	 */
	import { searchEmailLibrary, type EmailLibraryItem, type LibraryBlockType } from '$lib/library-admin';

	let {
		type,
		value,
		label,
		optional = false,
		disabled = false,
		onChange
	}: {
		type: LibraryBlockType;
		value: string;
		label: string;
		optional?: boolean;
		disabled?: boolean;
		onChange: (slug: string) => void;
	} = $props();

	let query = $state('');
	let results = $state<EmailLibraryItem[]>([]);
	let open = $state(false);
	let title = $state('');

	// Name the chosen item.
	$effect(() => {
		const slug = value;
		if (!slug) {
			title = '';
			return;
		}
		const controller = new AbortController();
		searchEmailLibrary(type, '', { slugs: [slug], signal: controller.signal })
			.then((r) => (title = r.results[0]?.title ?? slug))
			.catch(() => {});
		return () => controller.abort();
	});

	$effect(() => {
		const q = query.trim();
		if (!open) return;
		const controller = new AbortController();
		const timer = setTimeout(() => {
			searchEmailLibrary(type, q, { signal: controller.signal })
				.then((r) => (results = r.results))
				.catch(() => {});
		}, 250);
		return () => {
			clearTimeout(timer);
			controller.abort();
		};
	});

	function choose(item: EmailLibraryItem) {
		onChange(item.slug);
		open = false;
		query = '';
	}
</script>

<div class="text-small">
	<span class="mb-1 block text-micro text-muted">{label}</span>
	<div class="flex flex-wrap items-center gap-2">
		<span class="font-semibold text-text">{value ? title || value : optional ? 'Any' : 'None chosen'}</span>
		{#if !disabled}
			<button class="btn btn-ghost btn-sm" onclick={() => (open = !open)} aria-expanded={open}>{value ? 'Change' : 'Choose'}</button>
			{#if optional && value}<button class="btn btn-ghost btn-sm" onclick={() => onChange('')}>Clear</button>{/if}
		{/if}
	</div>
	{#if open}
		<input class="mt-2 w-full rounded-md border border-border bg-surface p-2" type="search" aria-label="Search {label}" placeholder="Search by name" bind:value={query} />
		<ul class="mt-1 max-h-48 divide-y divide-border/60 overflow-y-auto">
			{#each results as r (r.slug)}
				<li><button class="w-full p-2 text-start hover:bg-surface-2" onclick={() => choose(r)}>{r.title}{#if r.author}<span class="text-muted"> · {r.author}</span>{/if}</button></li>
			{/each}
		</ul>
	{/if}
</div>
