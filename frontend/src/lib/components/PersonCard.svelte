<script lang="ts">
	import { formatLifespan } from '$lib/library-public';
	import { i18n } from '$lib/i18n.svelte';
	import { localizeHref } from '$lib/href';
	import { initials, portraitPosition } from '$lib/portraits';

	// A compact person card: portrait (or initials), name and lifespan, linking
	// to the author page. Shared by the book page's "People in this book" strip
	// and the author page's "More lives" contemporaries — one shape, so the two
	// can't drift (they were a hand-rolled copy each before this).
	const t = i18n.t;

	let {
		person
	}: {
		person: {
			slug: string;
			name: string;
			photo_url: string;
			birth_year: number | null;
			death_year: number | null;
		};
	} = $props();
</script>

<a
	href={localizeHref(`/authors/${person.slug}`)}
	data-sveltekit-preload-data="hover"
	class="flex items-center gap-3 rounded-card border border-border p-3 hover:border-accent hover:no-underline"
>
	{#if person.photo_url}
		<img
			src={person.photo_url}
			alt="{t('a11y.portraitOf')} {person.name}"
			loading="lazy"
			class="h-11 w-11 shrink-0 rounded-full border border-border object-cover"
			style="filter: grayscale(1); object-position: {portraitPosition(person.slug)}"
		/>
	{:else}
		<span
			class="flex h-11 w-11 shrink-0 items-center justify-center rounded-full bg-accent-soft text-small font-semibold text-accent"
		>
			{initials(person.name)}
		</span>
	{/if}
	<span class="min-w-0">
		<span class="block truncate text-body font-medium text-text">{person.name}</span>
		{#if person.birth_year}
			<span class="block whitespace-nowrap text-small text-muted"
				>{formatLifespan(person.birth_year, person.death_year, t('common.bornPrefix'))}</span
			>
		{/if}
	</span>
</a>
