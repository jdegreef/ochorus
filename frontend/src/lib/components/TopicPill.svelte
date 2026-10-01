<script lang="ts">
	// One topic pill — a theme's title and how many items it holds. Shared by the
	// home page's topic row (TopicChips) and the /quotes index's theme chips.
	let { href, title, count }: { href: string; title: string; count: number } = $props();
</script>

<a
	{href}
	class="inline-flex items-baseline gap-1.5 rounded-full border border-border bg-surface px-4 py-2 text-small font-medium text-text hover:border-accent hover:text-accent hover:no-underline"
>
	{title}
	<span class="text-eyebrow font-normal text-muted">{count}</span>
</a>
