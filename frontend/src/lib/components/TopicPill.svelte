<script lang="ts">
	// One topic pill — a theme's title and how many items it holds. Shared by the
	// home page's topic row (TopicChips) and the /quotes index's theme chips.
	// `class` adds to the pill's own classes (the home row's responsive caps).
	import type { ClassValue } from 'svelte/elements';

	let {
		href,
		title,
		count,
		class: extra
	}: { href: string; title: string; count: number; class?: ClassValue } = $props();
</script>

<a
	{href}
	class={[
		'inline-flex items-baseline gap-1.5 rounded-full border border-border bg-surface px-4 py-2 text-small font-medium text-text hover:border-accent hover:text-accent hover:no-underline',
		extra
	]}
>
	{title}
	<span class="text-eyebrow font-normal text-muted">{count}</span>
</a>
