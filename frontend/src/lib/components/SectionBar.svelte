<!--
	A row of section links that sticks under the site header, lighting the
	section in view: the same tabs (`.subnav-link`) and handler (scrollSpy's
	`jump`) as the book, author and scripture pages' sticky bars. Each target
	carries a scroll margin as tall as the header plus this bar (`.anchor` on
	the page), so a jump lands below them. On a phone the row scrolls sideways
	and keeps the lit tab in view.
-->
<script lang="ts">
	import { scrollSpy } from '$lib/scrollSpy.svelte';

	let { sections }: { sections: { id: string; label: string }[] } = $props();

	// A band across the top third of the screen, below the pinned bars.
	const spy = scrollSpy(() => sections.map((s) => s.id), { rootMargin: '-120px 0px -66% 0px' });
	let bar: HTMLElement | undefined = $state();

	$effect(() => {
		const tab = spy.active && bar?.querySelector<HTMLElement>(`a[href="#${spy.active}"]`);
		if (tab && bar) bar.scrollTo({ left: tab.offsetLeft - 24, behavior: 'smooth' });
	});
</script>

<nav
	bind:this={bar}
	aria-label="Sections"
	class="sticky top-[var(--appnav-h,0px)] z-10 -mx-5 mb-6 flex overflow-x-auto border-b border-border bg-bg px-3 [scrollbar-width:none]"
>
	{#each sections as s (s.id)}
		<a
			href="#{s.id}"
			class="subnav-link"
			class:is-active={spy.active === s.id}
			aria-current={spy.active === s.id ? 'location' : undefined}
			onclick={(e) => spy.jump(e, s.id)}>{s.label}</a
		>
	{/each}
</nav>
