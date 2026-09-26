<script lang="ts">
	import Icon from '$lib/components/Icon.svelte';

	// The shared "Questions and Answers" section (book and topic pages; the
	// sermon <dl> and bio accordion are not yet converged — see
	// docs/questions-and-answers-plan.md). An accordion per plan §3.2: first
	// question open, an anchor id per question. Answers stay in the prerendered
	// HTML, so the page's FAQPage JSON-LD (same array, via pickQa) still
	// describes content on the page. Section id fixed to `questions` — the book
	// page's jump-nav points there.
	// A deep link to a question (#q-3) opens it: the browser scrolls to a
	// closed <details> without expanding it, so the answer that was linked
	// stayed hidden. Also on hashchange, for in-page links.
	$effect(() => {
		const openTarget = () => {
			const el = /^#q-\d+$/.test(location.hash) ? document.getElementById(location.hash.slice(1)) : null;
			if (el instanceof HTMLDetailsElement) el.open = true;
		};
		openTarget();
		window.addEventListener('hashchange', openTarget);
		return () => window.removeEventListener('hashchange', openTarget);
	});

	let {
		items,
		title,
		headingClass = 'text-h3'
	}: { items: { q: string; a: string }[]; title: string; headingClass?: string } = $props();
</script>

{#if items.length}
	<section id="questions" class="jump-anchor mt-12" aria-labelledby="qa-heading">
		<h2 id="qa-heading" class={headingClass}>{title}</h2>
		<div class="mt-3 divide-y divide-border border-y border-border">
			{#each items as item, i (item.q)}
				<details id="q-{i + 1}" class="qa-item" open={i === 0}>
					<summary class="qa-q">
						<span class="flex-1" dir="auto">{item.q}</span>
						<Icon name="chevron-right" size={18} class="qa-chevron shrink-0" />
					</summary>
					<p class="qa-a" dir="auto">{item.a}</p>
				</details>
			{/each}
		</div>
	</section>
{/if}

<style>
	/* A deep link (#q-3) lands below the pinned bars — the page publishes
	   --pinned-offset (app nav + any sticky sub-nav). */
	.qa-item {
		scroll-margin-top: calc(var(--pinned-offset, var(--appnav-h, 4rem)) + 0.5rem);
	}
	.qa-q {
		display: flex;
		align-items: center;
		gap: 0.75rem;
		min-height: 2.75rem;
		padding-block: 0.6rem;
		list-style: none;
		cursor: pointer;
		font-size: var(--fs-body);
		font-weight: 500;
		color: var(--text);
	}
	.qa-q::-webkit-details-marker {
		display: none;
	}
	/* Down when closed, up when open — a rotation, not a left/right chevron, so
	   it needs no RTL flip. */
	.qa-q :global(.qa-chevron) {
		color: var(--muted);
		transform: rotate(90deg);
		transition: transform var(--duration-fast) ease;
	}
	.qa-item[open] .qa-q :global(.qa-chevron) {
		transform: rotate(-90deg);
	}
	.qa-a {
		padding-bottom: 1rem;
		font-size: var(--fs-body);
		line-height: 1.6;
		color: var(--muted);
	}
	@media (prefers-reduced-motion: reduce) {
		.qa-q :global(.qa-chevron) {
			transition: none;
		}
	}
</style>
