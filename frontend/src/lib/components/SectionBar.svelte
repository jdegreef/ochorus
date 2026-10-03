<!--
	A row of section links that sticks under the site header as the page
	scrolls, highlighting the section in view. Plain #anchors, so the browser
	does the jump; each target needs a scroll margin at least as tall as the
	site header plus this bar, or the jump lands under them. On a phone the row scrolls sideways and keeps the
	current link in view.
-->
<script lang="ts">
	let { sections }: { sections: { id: string; label: string }[] } = $props();

	let current = $state('');
	let bar: HTMLElement | undefined = $state();

	// The section in view: the last one whose top has passed just under the
	// bar. Re-observed whenever the list changes (a section appears or hides).
	$effect(() => {
		const targets = sections
			.map((s) => document.getElementById(s.id))
			.filter((el): el is HTMLElement => !!el);
		if (!targets.length) return;
		const visible = new Set<string>();
		const observer = new IntersectionObserver(
			(entries) => {
				for (const e of entries) {
					if (e.isIntersecting) visible.add(e.target.id);
					else visible.delete(e.target.id);
				}
				current = sections.find((s) => visible.has(s.id))?.id ?? current;
			},
			// A band across the top third of the screen, below the sticky bars.
			{ rootMargin: '-120px 0px -66% 0px' }
		);
		targets.forEach((t) => observer.observe(t));
		return () => observer.disconnect();
	});

	// Keep the current link in view on a phone, where the row scrolls.
	$effect(() => {
		const link = current && bar?.querySelector<HTMLElement>(`a[href="#${current}"]`);
		if (link && bar) bar.scrollTo({ left: link.offsetLeft - 24, behavior: 'smooth' });
	});
</script>

<nav
	bind:this={bar}
	aria-label="Sections"
	class="sticky top-[var(--appnav-h,0px)] z-10 -mx-5 mb-6 flex gap-1.5 overflow-x-auto border-b border-border bg-bg/90 px-5 py-2 backdrop-blur [scrollbar-width:none]"
>
	{#each sections as s (s.id)}
		<a
			href="#{s.id}"
			aria-current={current === s.id ? 'true' : undefined}
			class="shrink-0 whitespace-nowrap rounded-full border px-3 py-1 text-small transition-colors {current === s.id
				? 'border-transparent bg-accent-soft font-semibold text-accent'
				: 'border-border bg-surface text-muted hover:text-text'}">{s.label}</a
		>
	{/each}
</nav>
