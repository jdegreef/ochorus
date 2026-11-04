<script lang="ts">
	import { anniversaryDate, anniversaryOn, type Anniversary } from '$lib/authorDays';
	import { getLang } from '$lib/lang.svelte';
	import * as m from '$lib/paraglide/messages.js';
	import Candle from '$lib/components/Candle.svelte';

	/**
	 * On the writer's birthday (or the day they died), a candle and the day by
	 * their name on their page: "Born on this day, 13 November 354".
	 *
	 * Decided in the browser, never at render: the author pages are
	 * prerendered on the build's day and must not carry it into every other.
	 * Re-checked when the tab comes back into view, so a page left open across
	 * midnight lights (and puts out) the candle with the day.
	 */
	let { slug }: { slug: string } = $props();
	let day = $state<Anniversary | null>(null);
	$effect(() => {
		const writer = slug;
		const check = () => {
			if (document.visibilityState === 'visible') day = anniversaryOn(writer, new Date());
		};
		check();
		document.addEventListener('visibilitychange', check);
		return () => document.removeEventListener('visibilitychange', check);
	});
	const said = $derived.by(() => {
		if (!day) return '';
		const date = anniversaryDate(day.date, getLang());
		return day.kind === 'born' ? m.author_born_today({ date }) : m.author_died_today({ date });
	});
</script>

{#if day}
	<p class="author-candle text-small"><Candle /><span>{said}</span></p>
{/if}

<style>
	.author-candle {
		display: inline-flex;
		align-items: center;
		gap: 0.5em;
		margin-top: 0.75rem;
	}
</style>
