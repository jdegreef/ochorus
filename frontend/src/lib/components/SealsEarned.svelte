<script lang="ts">
	import { onMount } from 'svelte';
	import { computeSeals, type Seal } from '$lib/seals';
	import { loadSealInput, sealName, sealNext, sealRule } from '$lib/sealData';
	import { sealsPref } from '$lib/sealsPref.svelte';
	import { getLang } from '$lib/lang.svelte';
	import { localizeHref } from '$lib/href';
	import { i18n } from '$lib/i18n.svelte';
	import Arrow from '$lib/components/Arrow.svelte';
	import SealMark from '$lib/components/SealMark.svelte';

	/**
	 * The seals this book pressed, in the finish panel (BookFinished): the ones
	 * whose earning finish was this book's — the first finish, the fifth, a
	 * writer's third, the era that completed the set. Never a pop-up mid-
	 * chapter; this is the end of the book, where an arrival is already marked.
	 * Each names its way onward. Nothing shows when the book earned none, or
	 * when the reader has switched seals off.
	 */
	let { slug }: { slug: string } = $props();
	const t = i18n.t;

	let seals = $state<Seal[]>([]);

	async function load() {
		const { input } = await loadSealInput(getLang());
		seals = computeSeals(input).filter(
			(s) => s.state === 'earned' && s.via?.kind === 'book' && s.via.slug === slug
		);
	}

	onMount(() => {
		load();
		window.addEventListener('ochorus:sync', load);
		return () => window.removeEventListener('ochorus:sync', load);
	});
</script>

{#if sealsPref.on && seals.length}
	<div class="mt-6 flex flex-col items-stretch gap-3">
		{#each seals as seal (seal.key)}
			{@const next = sealNext(seal)}
			<div class="seal-earned">
				<SealMark id={seal.id} state="earned" size="4.5rem" />
				<div class="min-w-0 text-start">
					<p class="eyebrow text-gold">{t('seals.new')}</p>
					<p class="font-display text-h3">{sealName(seal)}</p>
					<p class="text-small text-muted">{sealRule(seal.id)}</p>
					<a class="mt-1 inline-block text-small font-semibold text-accent" href={next.href}>{next.label} <Arrow /></a>
				</div>
			</div>
		{/each}
		<a class="text-small text-muted hover:text-accent" href="{localizeHref('/favorites')}#seals">{t('seals.title')} <Arrow /></a>
	</div>
{/if}

<style>
	.seal-earned {
		display: flex;
		align-items: center;
		gap: 1rem;
		margin-inline: auto;
		max-width: 28rem;
		padding: 0.85rem 1.1rem;
		border-radius: var(--radius-card);
		background: var(--surface-2);
	}
</style>
