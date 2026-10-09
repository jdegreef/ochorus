<script lang="ts">
	import type { Seal } from '$lib/seals';
	import { ERAS } from '$lib/eras';
	import { getLang } from '$lib/lang.svelte';
	import { i18n } from '$lib/i18n.svelte';
	import { sealFamily, sealName, sealNext, sealRule } from '$lib/sealData';
	import ModalShell from '$lib/components/ModalShell.svelte';
	import SealMark from '$lib/components/SealMark.svelte';

	/**
	 * One seal's own sheet: what it marks, and either when and with what it was
	 * earned, or how far there is to go — with the one way onward (sealNext). An
	 * unearned seal's sheet is the useful one: it names exactly what's missing.
	 */
	let { seal, title, onClose }: { seal: Seal; title: string | null; onClose: () => void } = $props();
	const t = i18n.t;

	const name = $derived(sealName(seal));
	const next = $derived(sealNext(seal));
	const date = $derived(
		seal.earnedOn
			? new Intl.DateTimeFormat(getLang(), { day: 'numeric', month: 'long', year: 'numeric' }).format(
					new Date(`${seal.earnedOn}T12:00:00`)
				)
			: ''
	);
	const status = $derived(
		seal.state === 'earned' ? t('seals.earned') : seal.state === 'progress' ? t('seals.onTheWay') : t('seals.notYet')
	);
</script>

<ModalShell {onClose} ariaLabelledby="seal-sheet-name" width="26rem">
	<div class="flex flex-col items-center gap-2 text-center">
		<SealMark id={seal.id} state={seal.state} size="8rem" />
		<p class="eyebrow mt-2 text-muted">{sealFamily(seal.family)} · {status}</p>
		<h2 id="seal-sheet-name" class="font-display text-h2">{name}</h2>
		<p class="text-body text-muted">{sealRule(seal.id)}</p>

		{#if seal.state === 'earned'}
			{#if date || title}
				<p class="mt-2 text-small">
					{#if date}{t('seals.earnedOn').replace('%date%', date)}{/if}{#if date && title}{' · '}{/if}{#if title}<em
							>{title}</em
						>{/if}
				</p>
			{/if}
		{:else if seal.id === 'centuries'}
			<ul class="eras mt-3 text-small">
				{#each ERAS as era (era.id)}
					{@const has = !seal.missingEras?.includes(era.id)}
					<li class:has>
						<span aria-hidden="true">{has ? '✓' : '○'}</span>
						{t(era.k)}
					</li>
				{/each}
			</ul>
		{:else if seal.need > 1}
			<p class="mt-2 text-small">{t('seals.count').replace('%n%', String(seal.have)).replace('%t%', String(seal.need))}</p>
			<div class="meter" aria-hidden="true"><i style:width="{(seal.have / seal.need) * 100}%"></i></div>
		{/if}

		<div class="mt-4 flex flex-wrap justify-center gap-2">
			<a class="btn btn-primary hover:no-underline" href={next.href} onclick={onClose}>{next.label}</a>
			<button type="button" class="btn btn-ghost" onclick={onClose}>{t('a11y.close')}</button>
		</div>
	</div>
</ModalShell>

<style>
	.eras {
		display: grid;
		grid-template-columns: repeat(2, minmax(0, 1fr));
		gap: 0.3rem 1.25rem;
		text-align: start;
		color: var(--muted);
	}
	.eras .has {
		color: var(--text);
	}
	.meter {
		width: 70%;
		height: 0.3rem;
		border-radius: 999px;
		background: var(--surface-2);
		overflow: hidden;
	}
	.meter i {
		display: block;
		height: 100%;
		background: var(--accent);
	}
</style>
