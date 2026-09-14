<script lang="ts">
	// The shared "Questions and Answers" section. Used by the book page now; the
	// topic page adopts it in the Topics PR. (The sermon <dl> and the bio accordion
	// predate it and are not yet converged onto it — see
	// docs/questions-and-answers-plan.md, Phase 0.)
	//
	// Visible list ONLY: the page owns the FAQPage JSON-LD, built from the same
	// array by `pickQa`/`faqPage`, so the markup and the structured data stay in
	// lockstep. A <dl> (every answer visible, no accordion) because it is literally
	// a list of question/answer pairs. `title` is passed in so each page names the
	// section in its own words. The section id is fixed to `questions` — the book
	// page's jump-nav anchor points at `#questions`.
	let { items, title }: { items: { q: string; a: string }[]; title: string } = $props();
</script>

{#if items.length}
	<section id="questions" class="jump-anchor mt-12" aria-labelledby="qa-heading">
		<h2 id="qa-heading" class="text-h3">{title}</h2>
		<dl class="mt-4 flex flex-col gap-5">
			{#each items as item (item.q)}
				<div>
					<dt class="text-body font-medium text-text">{item.q}</dt>
					<dd class="mt-1 text-body text-muted" dir="auto">{item.a}</dd>
				</div>
			{/each}
		</dl>
	</section>
{/if}
