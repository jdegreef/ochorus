<script lang="ts">
	import type { Snippet } from 'svelte';
	import type { TopicCover } from '$lib/library';
	import Icon, { type IconName } from '$lib/components/Icon.svelte';

	/**
	 * The shared browse-page card: a colour-washed band carrying an icon (or a
	 * portrait) and a fan of covers, over a typographic body.
	 *
	 * This is the Topics card, generalised. It was the best-looking surface in
	 * the app and the only page using it — Plans rendered plain bordered rows
	 * with a ragged cluster of covers floated top-right, and Sermons rendered a
	 * bare text list. Now all three share one card.
	 *
	 * `hue` drives every tint via color-mix (see .shelf-card* in app.css), so a
	 * caller only has to supply a colour and the rest follows.
	 */
	let {
		href,
		hue,
		icon,
		portrait = '',
		covers = [],
		bandAside,
		title,
		aside,
		children
	}: {
		href: string;
		/** The card's accent, any CSS colour. Used only through color-mix(). */
		hue: string;
		/** Line icon for the badge. Ignored when `portrait` is set. */
		icon?: IconName;
		/** Portrait URL to fill the badge instead of an icon (sermons). */
		portrait?: string;
		/** Up to four covers to fan across the band. */
		covers?: TopicCover[];
		/**
		 * Content for the far end of the band, where covers would otherwise fan.
		 * A sermon has no cover art, so it hangs its scripture reference here.
		 */
		bandAside?: Snippet;
		title: string;
		/** Right-aligned meta beside the title (counts, day totals). */
		aside?: Snippet;
		/** Body content under the title. */
		children?: Snippet;
	} = $props();
</script>

<a class="shelf-card" style="--shelf-hue: {hue}" {href}>
	<div class="shelf-card-band">
		<span class="shelf-card-badge">
			{#if portrait}
				<img src={portrait} alt="" loading="lazy" />
			{:else if icon}
				<Icon name={icon} size={20} />
			{/if}
		</span>
		{#if covers.length}
			<div class="cover-fan" aria-hidden="true">
				{#each covers.slice(0, 4) as cover (cover.title)}
					<div class="cover">
						{#if cover.cover_url}
							<img src={cover.cover_url} alt="" loading="lazy" />
						{:else}
							<div
								class="cover-fallback"
								style="background: linear-gradient(150deg, {cover.cover_color || hue} 0%, #0008 100%)"
							></div>
						{/if}
					</div>
				{/each}
			</div>
		{:else if bandAside}
			{@render bandAside()}
		{/if}
	</div>
	<div class="shelf-card-body">
		<div class="flex items-baseline justify-between gap-3">
			<h2 class="shelf-card-title">{title}</h2>
			{#if aside}
				<span class="shrink-0 text-small text-muted">{@render aside()}</span>
			{/if}
		</div>
		{#if children}
			{@render children()}
		{/if}
	</div>
</a>
