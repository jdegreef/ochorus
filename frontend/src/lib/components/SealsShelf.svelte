<script lang="ts">
	import { onMount } from 'svelte';
	import { computeSeals, shelfOrder, type Seal } from '$lib/seals';
	import { loadSealInput, sealName } from '$lib/sealData';
	import { sealsPref } from '$lib/sealsPref.svelte';
	import { getLang } from '$lib/lang.svelte';
	import { i18n } from '$lib/i18n.svelte';
	import SealMark from '$lib/components/SealMark.svelte';
	import SealSheet from '$lib/components/SealSheet.svelte';

	/**
	 * "Your seals" on the Bookshelf: every seal, earned first (newest first),
	 * then those on the way, then the rest, each opening its own sheet. Worked
	 * out on the device after mount (the page is client-side), and again on
	 * `ochorus:sync`, when a sign-in brings the account's reading in. Hidden
	 * entirely when the reader has switched seals off in Settings.
	 */
	const t = i18n.t;

	let seals = $state<Seal[]>([]);
	let titles = $state(new Map<string, string>());
	let open = $state<Seal | null>(null);

	async function load() {
		const data = await loadSealInput(getLang());
		seals = shelfOrder(computeSeals(data.input));
		titles = data.titles;
	}

	onMount(() => {
		load();
		window.addEventListener('ochorus:sync', load);
		return () => window.removeEventListener('ochorus:sync', load);
	});

	const earned = $derived(seals.filter((s) => s.state === 'earned').length);
	const titleOf = (s: Seal) => (s.via ? (titles.get(`${s.via.kind}:${s.via.slug}`) ?? null) : null);
</script>

{#if sealsPref.on && seals.length}
	<section id="seals" class="seals mt-10 scroll-mt-24" aria-labelledby="seals-h">
		<h2 id="seals-h" class="section-heading">
			{t('seals.title')}
			<span class="meta">· {t('seals.count').replace('%n%', String(earned)).replace('%t%', String(seals.length))}</span>
		</h2>
		<ul class="seal-grid">
			{#each seals as seal (seal.key)}
				<li>
					<button type="button" class="seal-cell" class:dim={seal.state !== 'earned'} onclick={() => (open = seal)}>
						<SealMark id={seal.id} state={seal.state} size="4rem" />
						<span class="seal-name font-display">{sealName(seal)}</span>
					</button>
				</li>
			{/each}
		</ul>
	</section>
{/if}

{#if open}
	<SealSheet seal={open} title={titleOf(open)} onClose={() => (open = null)} />
{/if}

<style>
	.seals {
		padding: 1.25rem 1.25rem 1rem;
		border-radius: var(--radius-card);
		/* The Bookshelf's own back wall, so the seals hang in the same room. */
		background: var(--shelf-back);
	}
	.seal-grid {
		display: grid;
		grid-template-columns: repeat(auto-fill, minmax(6.5rem, 1fr));
		gap: 0.75rem 0.5rem;
		list-style: none;
		margin: 0;
		padding: 0;
	}
	.seal-cell {
		display: flex;
		width: 100%;
		flex-direction: column;
		align-items: center;
		gap: 0.4rem;
		padding: 0.5rem 0.25rem;
		border: 0;
		border-radius: var(--radius-card);
		background: none;
		color: var(--text);
		cursor: pointer;
		text-align: center;
	}
	.seal-cell:hover,
	.seal-cell:focus-visible {
		background: color-mix(in srgb, var(--text) 6%, transparent);
	}
	.seal-name {
		font-size: var(--fs-small);
		line-height: 1.25;
	}
	.dim .seal-name {
		color: var(--muted);
	}
</style>
