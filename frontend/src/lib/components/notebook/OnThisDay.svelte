<script lang="ts">
	import { i18n } from '$lib/i18n.svelte';
	import * as m from '$lib/paraglide/messages.js';
	import type { Ago, Memory } from '$lib/journal';

	/**
	 * "On this day" — what the reader wrote, and what God answered, on this
	 * date months and years ago. A few lines at the top of the Notebook, each
	 * a link down to its entry. Hidden for the rest of the day on request.
	 */
	let { memories, onhide }: { memories: Memory[]; onhide: () => void } = $props();

	const t = i18n.t;

	function ago(a: Ago): string {
		if (a.unit === 'month') return a.n === 1 ? t('notebook.otdMonth') : m.notebook_otd_months({ n: String(a.n) });
		return a.n === 1 ? t('notebook.otdYear') : m.notebook_otd_years({ n: String(a.n) });
	}
</script>

<aside class="otd" aria-labelledby="otd-title">
	<div class="head">
		<h2 id="otd-title" class="title">{t('notebook.otdTitle')}</h2>
		<button class="hide text-micro" onclick={onhide}>{t('notebook.otdHide')}</button>
	</div>
	<ul>
		{#each memories as mem (`${mem.what}:${mem.entry.id}`)}
			<li>
				<a class="memory" href="#entry-{mem.entry.id}">
					<span class="when text-micro">
						{ago(mem.ago)} ·
						{#if mem.what === 'answered'}<span class="answered">✓ {t('notebook.otdAnswered')}</span>{:else}{t('notebook.otdWrote')}{/if}
					</span>
					<span class="text">{mem.entry.title || mem.entry.body}</span>
					{#if mem.what === 'answered' && mem.entry.answer}
						<span class="answer">{mem.entry.answer}</span>
					{/if}
				</a>
			</li>
		{/each}
	</ul>
</aside>

<style>
	/* A slip of older paper tucked into today's page. */
	.otd {
		margin-bottom: 1.25rem;
		padding: 0.85rem 1rem 0.6rem;
		border: 1px dashed color-mix(in srgb, var(--accent) 35%, transparent);
		border-radius: var(--radius-sm);
		background: color-mix(in srgb, var(--accent) 5%, var(--surface));
		transform: rotate(-0.3deg);
	}
	.head {
		display: flex;
		align-items: baseline;
		justify-content: space-between;
		gap: 1rem;
	}
	.title {
		font-family: var(--font-display);
		font-size: var(--fs-small);
		font-style: italic;
		font-weight: 600;
		color: var(--accent);
	}
	.hide {
		color: var(--muted);
		cursor: pointer;
	}
	.hide:hover {
		color: var(--text);
	}
	ul {
		display: grid;
		gap: 0.2rem;
		margin-top: 0.35rem;
	}
	.memory {
		display: block;
		padding: 0.4rem 0;
		color: inherit;
	}
	li + li .memory {
		border-top: 1px solid var(--border);
	}
	.memory:hover {
		text-decoration: none;
	}
	.memory:hover .text {
		color: var(--accent);
	}
	.when {
		display: block;
		color: var(--muted);
	}
	.answered {
		color: color-mix(in srgb, var(--hl-green) 65%, var(--text));
		font-weight: 600;
	}
	.text {
		display: -webkit-box;
		-webkit-line-clamp: 2;
		line-clamp: 2;
		-webkit-box-orient: vertical;
		overflow: hidden;
		font-family: var(--font-display);
		color: var(--text);
		line-height: 1.5;
	}
	.answer {
		display: block;
		font-family: var(--font-display);
		font-style: italic;
		color: color-mix(in srgb, var(--hl-green) 65%, var(--text));
	}
	@media (prefers-reduced-motion: reduce) {
		.otd {
			transform: none;
		}
	}
</style>
