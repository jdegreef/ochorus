<script lang="ts">
	import { localizeHref } from '$lib/href';
	import { i18n } from '$lib/i18n.svelte';
	import Portrait from '$lib/components/Portrait.svelte';

	/**
	 * The top of the A–Z: the library's people as a wall of faces, earliest-born
	 * first, so the centuries run across it — "a great cloud of witnesses".
	 * Each face is a link to the writer's page. The list below is still the
	 * complete index; this is the door into it, not a second copy of it.
	 *
	 * The caller picks WHICH faces (the writers with the most books here, a real
	 * portrait each) — this only lays them out. Grey until hovered, like the
	 * Biographies roster, so forty photographs of different ages and inks read
	 * as one picture rather than forty.
	 */
	type Face = { slug: string; name: string; photo_url: string };
	let { faces }: { faces: Face[] } = $props();
	const t = i18n.t;
</script>

{#if faces.length}
	<section class="wall card-tint mb-8 rounded-[var(--radius-card)] border border-border px-5 py-7 sm:px-8" aria-labelledby="cloud-title">
		<h2 id="cloud-title" class="font-display text-center text-h2 font-semibold">{t('authors.cloudTitle')}</h2>
		<p class="mx-auto mt-1.5 max-w-prose text-center text-small text-muted">{t('authors.cloudLine')}</p>
		<ul class="faces mt-6">
			{#each faces as f (f.slug)}
				<li>
					<a class="face group" href={localizeHref(`/authors/${f.slug}`)} title={f.name}>
						<Portrait slug={f.slug} name={f.name} url={f.photo_url} px={56} tone="hover" class="h-11 w-11 sm:h-14 sm:w-14" />
					</a>
				</li>
			{/each}
		</ul>
	</section>
{/if}

<style>
	.faces {
		display: flex;
		flex-wrap: wrap;
		justify-content: center;
		gap: 0.5rem;
	}
	/* Five even rows of six on a phone, not five and a stub. */
	@media (max-width: 639.98px) {
		.faces > li:nth-child(n + 31) {
			display: none;
		}
	}
	.face {
		display: block;
		border-radius: var(--radius-pill);
		transition: transform var(--duration-base);
	}
	.face:hover,
	.face:focus-visible {
		transform: scale(1.12);
	}
	@media (prefers-reduced-motion: reduce) {
		.face {
			transition: none;
		}
		.face:hover,
		.face:focus-visible {
			transform: none;
		}
	}
</style>
