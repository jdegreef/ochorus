<!--
	A row of section links that sticks under the site header, lighting the
	section in view: the same tabs (`.subnav-link`) and handler (scrollSpy's
	`jump`) as the book, author and scripture pages' sticky bars. It publishes
	its measured height as `--section-bar-h` on its parent, so the sections'
	scroll margin clears it. On a phone the row scrolls sideways and keeps the
	lit tab in view.
-->
<script lang="ts">
	import { tick } from 'svelte';
	import { jumpToSection, scrollSpy, SUBNAV_H_EST } from '$lib/scrollSpy.svelte';

	let { sections }: { sections: { id: string; label: string }[] } = $props();

	// A band across the top third of the screen, below the pinned bars.
	const spy = scrollSpy(() => sections.map((s) => s.id), { rootMargin: '-120px 0px -66% 0px' });
	let bar: HTMLElement | undefined = $state();
	let barH = $state(0);

	$effect(() => {
		bar?.parentElement?.style.setProperty('--section-bar-h', `${barH || SUBNAV_H_EST}px`);
	});

	// A cold load of `/admin/engagement#plans`: the sections only exist once
	// the data arrives, after the browser has given up on the hash, so land
	// it once they are there.
	let landed = false;
	$effect(() => {
		if (landed || !sections.length) return;
		landed = true;
		const id = location.hash.slice(1);
		if (sections.some((s) => s.id === id)) tick().then(() => jumpToSection(id));
	});

	$effect(() => {
		const tab = spy.active && bar?.querySelector<HTMLElement>(`a[href="#${spy.active}"]`);
		if (tab && bar) bar.scrollTo({ left: tab.offsetLeft - 24, behavior: 'smooth' });
	});
</script>

<nav
	bind:this={bar}
	bind:clientHeight={barH}
	aria-label="Sections"
	class="sticky top-[var(--appnav-h,0px)] z-(--z-pinned) -mx-5 mb-6 flex overflow-x-auto border-b border-border bg-bg px-3 [scrollbar-width:none]"
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
