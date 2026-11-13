<script lang="ts">
	/**
	 * "What the Church has said": under a chapter of a Bible book with a catena,
	 * a chip for each verse span the catena comments on. A chip opens the span's
	 * excerpts — commentator, work and the opening of what they wrote — with a
	 * way into the catena at that very block. The Bible text carries no verse
	 * numbers (build_owb_book), so the spans are chosen here rather than tapped
	 * in the text.
	 *
	 * The chips come with the chapter (prerendered); the excerpts are fetched
	 * once, when a reader first opens one ($lib/catena).
	 */
	import { tick } from 'svelte';
	import { getChapterCatena, type CatenaPassage, type CatenaPointer } from '$lib/library-public';
	import { catenaPassageHref, passageFor, spanId } from '$lib/catena';
	import { localizeHref } from '$lib/href';
	import { i18n } from '$lib/i18n.svelte';
	import Arrow from '$lib/components/Arrow.svelte';

	const t = i18n.t;

	let {
		book,
		order,
		catena
	}: {
		/** The Bible book's slug and this chapter's reader order. */
		book: string;
		order: number;
		catena: CatenaPointer;
	} = $props();

	let open = $state<string | null>(null);
	let passages = $state<CatenaPassage[] | null>(null);
	let loading = $state(false);
	let failed = $state(false);
	let panel = $state<HTMLElement | null>(null);

	const passage = $derived(open && passages ? passageFor(passages, open) : null);
	const panelId = $derived(`catena-${book}-${order}`);

	async function load() {
		if (passages || loading) return;
		loading = true;
		failed = false;
		try {
			passages = (await getChapterCatena(book, order)).passages;
		} catch {
			failed = true;
		} finally {
			loading = false;
		}
	}

	async function toggle(ref: string) {
		if (open === ref) {
			open = null;
			return;
		}
		open = ref;
		await load();
		// Take the reader (and a screen reader) to what opened.
		await tick();
		panel?.focus({ preventScroll: true });
	}

	function close(event: KeyboardEvent) {
		if (event.key !== 'Escape' || open === null) return;
		const ref = open;
		open = null;
		document.getElementById(`${panelId}-chip-${spanId(ref)}`)?.focus();
	}
</script>

<!-- svelte-ignore a11y_no_noninteractive_element_interactions -->
<section
	class="mt-10 border-t border-border pt-6"
	aria-labelledby="{panelId}-heading"
	onkeydown={close}
	data-nosnippet
>
	<h2 id="{panelId}-heading" class="eyebrow text-muted">{t('reader.catenaHeading')}</h2>
	<div class="mt-3 flex flex-wrap gap-2">
		{#each catena.verses as ref (ref)}
			<button
				type="button"
				id="{panelId}-chip-{spanId(ref)}"
				class="chip"
				class:active={open === ref}
				aria-expanded={open === ref}
				aria-controls={panelId}
				onclick={() => toggle(ref)}>{ref}</button
			>
		{/each}
	</div>

	<div id={panelId} class="catena-panel" hidden={open === null}>
		{#if open !== null}
			{#if passage}
				<h3 class="font-display text-h3" tabindex="-1" bind:this={panel}>{passage.reference}</h3>
				<blockquote class="verse">{passage.text}</blockquote>
				<ul class="excerpts">
					{#each passage.excerpts as e, i (i)}
						<li>
							<p class="text-small">
								<strong>{e.author}</strong> · <em>{e.work}</em>
							</p>
							<p class="excerpt">{e.text}</p>
						</li>
					{/each}
				</ul>
				<a
					class="text-small text-accent hover:underline"
					href={localizeHref(catenaPassageHref(catena.slug, catena.chapter, passage.p))}
					>{t('reader.catenaRead').replace('%title%', () => catena.title)} <Arrow /></a
				>
			{:else if failed}
				<p class="text-small text-muted" tabindex="-1" bind:this={panel}>
					{t('reader.catenaError')}
					<button type="button" class="underline" onclick={load}>{t('error.tryAgain')}</button>
				</p>
			{:else if loading}
				<p class="text-small text-muted" tabindex="-1" bind:this={panel}>…</p>
			{:else}
				<!-- The served index lacks this span (a prerendered chip racing a
				     newer API): the catena chapter itself still has it. -->
				<a
					class="text-small text-accent hover:underline"
					tabindex="-1"
					bind:this={panel}
					href={localizeHref(catenaPassageHref(catena.slug, catena.chapter, 0))}
					>{t('reader.catenaRead').replace('%title%', () => catena.title)} <Arrow /></a
				>
			{/if}
		{/if}
	</div>
</section>

<style>
	.catena-panel {
		margin-top: 1rem;
		padding: 1rem 1.1rem;
		border-radius: var(--radius-card);
		background: var(--surface-2);
	}
	.catena-panel[hidden] {
		display: none;
	}
	.catena-panel h3:focus {
		outline: none;
	}
	.verse {
		margin: 0.5rem 0 0;
		padding-inline-start: 0.8rem;
		border-inline-start: 3px solid var(--accent);
		font-size: var(--fs-small);
		line-height: 1.55;
		color: var(--muted);
	}
	.excerpts {
		list-style: none;
		margin: 1rem 0;
		padding: 0;
		display: grid;
		gap: 0.9rem;
	}
	.excerpt {
		margin-top: 0.25rem;
		line-height: 1.6;
	}
</style>
