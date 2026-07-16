<script lang="ts">
	import type { BookSummary } from '$lib/library';
	import { i18n } from '$lib/i18n.svelte';

	const t = i18n.t;

	/**
	 * A book's cover: the real cover image when there is one, otherwise a
	 * generated typographic cover. The fallback mirrors the server-side
	 * `generate_covers` SVG (framed, OCHORUS eyebrow, centred title, divider,
	 * author) so a book without an image looks the same as one that has a
	 * generated cover — and it scales cleanly at any size. The box keeps a fixed
	 * 3:4 aspect so nothing shifts while a lazy image loads.
	 */
	let { book, rounded = 'rounded-card' }: { book: BookSummary; rounded?: string } = $props();

	let loaded = $state(false);
	let failed = $state(false);

	// Darken a hex colour for the gradient foot (matches generate_covers' 0.55).
	function darken(hex: string, factor = 0.55): string {
		const n = (hex || '#3b5bdb').replace('#', '');
		if (n.length !== 6) return '#1e2a52';
		const c = [0, 2, 4].map((i) =>
			Math.max(0, Math.round(parseInt(n.slice(i, i + 2), 16) * factor))
				.toString(16)
				.padStart(2, '0')
		);
		return `#${c.join('')}`;
	}

	// Greedy word-wrap to a character budget (mirrors the generator).
	function wrap(title: string, maxChars: number): string[] {
		const lines: string[] = [];
		let line = '';
		for (const word of title.split(/\s+/)) {
			if (line && line.length + 1 + word.length > maxChars) {
				lines.push(line);
				line = word;
			} else {
				line = `${line} ${word}`.trim();
			}
		}
		if (line) lines.push(line);
		return lines;
	}

	const color = $derived(book.cover_color || '#3b5bdb');
	// Smaller type for longer titles so they always fit.
	const fontSize = $derived(book.title.length <= 22 ? 58 : 46);
	const maxChars = $derived(book.title.length <= 22 ? 12 : 16);
	const lineH = $derived(fontSize + 8);
	const lines = $derived(wrap(book.title, maxChars));
	const blockTop = $derived(360 - ((lines.length - 1) * lineH) / 2);
	const dividerY = $derived(blockTop + (lines.length - 1) * lineH + 46);
	const author = $derived(book.author.name.toUpperCase());
	const gradId = $derived(`bc-${book.slug}`);
</script>

<div class="relative aspect-[3/4] w-full overflow-hidden {rounded} shadow-sm">
	{#if book.cover_url && !failed}
		{#if !loaded}
			<div class="absolute inset-0 animate-pulse bg-surface-2"></div>
		{/if}
		<img
			src={book.cover_url}
			alt="{t('a11y.coverOf')} {book.title}"
			loading="lazy"
			onload={() => (loaded = true)}
			onerror={() => (failed = true)}
			class="absolute inset-0 h-full w-full object-cover transition-opacity duration-300"
			class:opacity-0={!loaded}
			class:opacity-100={loaded}
		/>
	{:else}
		<svg
			viewBox="0 0 600 800"
			class="h-full w-full"
			preserveAspectRatio="xMidYMid slice"
			role="img"
			aria-label="{t('a11y.coverOf')} {book.title}"
		>
			<defs>
				<linearGradient id={gradId} x1="0" y1="0" x2="0.3" y2="1">
					<stop offset="0" stop-color={color} />
					<stop offset="1" stop-color={darken(color)} />
				</linearGradient>
			</defs>
			<rect width="600" height="800" fill="url(#{gradId})" />
			<rect
				x="26"
				y="26"
				width="548"
				height="748"
				fill="none"
				stroke="#ffffff"
				stroke-opacity="0.22"
				stroke-width="1.5"
			/>
			<text
				x="300"
				y="96"
				text-anchor="middle"
				fill="#ffffff"
				fill-opacity="0.7"
				font-family="Georgia, serif"
				font-size="19"
				letter-spacing="7">OCHORUS</text
			>
			<text
				text-anchor="middle"
				fill="#ffffff"
				font-family="Georgia, 'Times New Roman', serif"
				font-weight="600"
				font-size={fontSize}
			>
				{#each lines as ln, i (i)}
					<tspan x="300" y={blockTop + i * lineH}>{ln}</tspan>
				{/each}
			</text>
			<line
				x1="262"
				y1={dividerY}
				x2="338"
				y2={dividerY}
				stroke="#ffffff"
				stroke-opacity="0.55"
				stroke-width="1.5"
			/>
			{#if book.subtitle}
				<text
					x="300"
					y={dividerY + 40}
					text-anchor="middle"
					fill="#ffffff"
					fill-opacity="0.85"
					font-family="Georgia, serif"
					font-style="italic"
					font-size="22">{book.subtitle}</text
				>
			{/if}
			<text
				x="300"
				y="724"
				text-anchor="middle"
				fill="#ffffff"
				fill-opacity="0.82"
				font-family="Georgia, serif"
				font-size="22"
				letter-spacing="3">{author}</text
			>
		</svg>
	{/if}
</div>
