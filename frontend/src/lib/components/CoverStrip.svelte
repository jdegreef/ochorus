<script lang="ts">
	import type { TopicCover } from '$lib/library';

	/**
	 * A small fanned "shelf peek" of book covers — the visual signature shared by
	 * topic and plan cards. Decorative (aria-hidden); falls back to the book's
	 * cover colour when there's no image.
	 */
	let { covers, max = 4 }: { covers: TopicCover[]; max?: number } = $props();
</script>

{#if covers.length}
	<div class="covers" aria-hidden="true">
		{#each covers.slice(0, max) as cover (cover.title)}
			<div class="cover">
				{#if cover.cover_url}
					<img src={cover.cover_url} alt="" loading="lazy" />
				{:else}
					<div class="cover-fallback" style="background: {cover.cover_color || '#3b5bdb'}"></div>
				{/if}
			</div>
		{/each}
	</div>
{/if}

<style>
	.covers {
		display: flex;
	}
	.cover {
		width: 2.5rem;
		aspect-ratio: 3 / 4;
		border-radius: 0.25rem;
		overflow: hidden;
		box-shadow: 0 2px 6px -2px #0006;
		margin-left: -0.7rem;
		background: var(--surface);
		transform: rotate(-3deg);
	}
	.cover:first-child {
		margin-left: 0;
	}
	.cover:nth-child(2) {
		transform: rotate(1deg);
	}
	.cover:nth-child(3) {
		transform: rotate(4deg);
	}
	.cover:nth-child(4) {
		transform: rotate(7deg);
	}
	.cover img,
	.cover-fallback {
		width: 100%;
		height: 100%;
		object-fit: cover;
	}
</style>
