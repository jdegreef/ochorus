<script lang="ts">
	import type { BookSummary } from '$lib/library';

	/**
	 * A book's cover: the real cover image when there is one, otherwise a
	 * generated gradient cover carrying the author and title. Either way the box
	 * keeps a fixed 3:4 aspect so nothing shifts while a lazy image loads — a
	 * subtle skeleton shows underneath until then.
	 */
	let { book, rounded = 'rounded-card' }: { book: BookSummary; rounded?: string } = $props();

	let loaded = $state(false);
	let failed = $state(false);

	const onCover = (hex: string) => `linear-gradient(150deg, ${hex} 0%, ${shade(hex, -28)} 100%)`;
	function shade(hex: string, amt: number): string {
		const n = hex.replace('#', '');
		if (n.length !== 6) return hex;
		const c = [0, 2, 4].map((i) => {
			const v = Math.round(parseInt(n.slice(i, i + 2), 16) * (1 + amt / 100));
			return Math.max(0, Math.min(255, v)).toString(16).padStart(2, '0');
		});
		return `#${c.join('')}`;
	}
	const lastName = $derived(book.author.name.split(' ').slice(-1).join(' '));
</script>

<div class="relative aspect-[3/4] w-full overflow-hidden {rounded} shadow-sm">
	{#if book.cover_url && !failed}
		{#if !loaded}
			<div class="absolute inset-0 animate-pulse bg-surface-2"></div>
		{/if}
		<img
			src={book.cover_url}
			alt="Cover of {book.title}"
			loading="lazy"
			onload={() => (loaded = true)}
			onerror={() => (failed = true)}
			class="absolute inset-0 h-full w-full object-cover transition-opacity duration-300"
			class:opacity-0={!loaded}
			class:opacity-100={loaded}
		/>
	{:else}
		<div
			class="flex h-full w-full flex-col justify-between p-4"
			style="background: {onCover(book.cover_color || '#3b5bdb')}"
		>
			<span class="text-[0.7rem] font-semibold uppercase tracking-wider text-white/70">
				{lastName}
			</span>
			<span
				style="font-family: var(--font-display)"
				class="text-[1.1rem] font-semibold leading-tight text-white"
			>
				{book.title}
			</span>
		</div>
	{/if}
</div>
