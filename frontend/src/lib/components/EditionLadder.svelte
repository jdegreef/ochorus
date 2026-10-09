<script lang="ts">
	import { tileFace, type EditionRung } from '$lib/library-public';
	import { localizeHref } from '$lib/href';
	import { i18n } from '$lib/i18n.svelte';
	import BookCover from './BookCover.svelte';
	import Icon from './Icon.svelte';

	/**
	 * A work's editions as a ladder — For children → For teens → The original —
	 * each a small cover that opens its book page, the edition in hand ringed.
	 * The rungs come from the slug convention on the API (`_edition_ladders`,
	 * the book page's `editions` rule), youngest first, this language only.
	 */
	let {
		rungs,
		current,
		onclimb
	}: { rungs: EditionRung[]; current: string; onclimb?: () => void } = $props();
	const t = i18n.t;

	const LABEL = {
		children: 'audience.rungChildren',
		teens: 'audience.rungTeens',
		full: 'audience.rungFull'
	} as const;
</script>

<ol class="ladder" aria-label={t('audience.spotlightLadder')}>
	{#each rungs as rung, i (rung.slug)}
		{@const face = tileFace(rung)}
		{#if i > 0}
			<li class="step" aria-hidden="true"><Icon name="chevron-right" size={16} /></li>
		{/if}
		<li>
			<a
				class="rung"
				class:here={rung.slug === current}
				href={localizeHref(`/books/${rung.slug}`)}
				aria-current={rung.slug === current ? 'page' : undefined}
				onclick={rung.slug === current ? undefined : onclimb}
			>
				<span class="rung-cover" aria-hidden="true">
					{#if face}<BookCover book={face} />{/if}
				</span>
				<span class="text-eyebrow font-medium">{t(LABEL[rung.rung])}</span>
			</a>
		</li>
	{/each}
</ol>

<style>
	.ladder {
		display: flex;
		align-items: center;
		gap: 0.5rem;
		flex-wrap: wrap;
	}
	.step {
		color: var(--muted);
	}
	.rung {
		display: flex;
		flex-direction: column;
		align-items: center;
		gap: 0.35rem;
		color: var(--muted);
		text-decoration: none;
	}
	.rung:hover {
		color: var(--accent);
	}
	.rung-cover {
		display: block;
		width: 3.25rem;
		border-radius: var(--radius-sm);
		outline: 2px solid transparent;
		outline-offset: 2px;
	}
	.rung.here {
		color: var(--text);
	}
	.rung.here .rung-cover {
		outline-color: var(--accent);
	}
</style>
