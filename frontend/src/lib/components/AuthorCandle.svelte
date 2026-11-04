<script lang="ts">
	import type { Anniversary } from '$lib/authorDays';
	import { anniversaryDate } from '$lib/anniversaryFormat';
	import { getLang } from '$lib/lang.svelte';
	import { watchToday } from '$lib/today';
	import * as m from '$lib/paraglide/messages.js';
	import Candle from '$lib/components/Candle.svelte';

	/**
	 * On the writer's birthday (or the day they died), a candle and the day by
	 * their name on their page: "Born on this day, 13 November 354".
	 *
	 * Decided in the browser, never at render: the author pages are
	 * prerendered on the build's day and must not carry it into every other.
	 * Re-checked as the day turns ($lib/today). The table of days loads after
	 * the page's first paint, not in its bundle — and a page whose chunk a
	 * deploy has since removed simply shows no candle.
	 */
	let { slug }: { slug: string } = $props();
	const table = import('$lib/authorDays').catch(() => null);
	let day = $state<Anniversary | null>(null);
	$effect(() => {
		const writer = slug;
		let live = true;
		const stop = watchToday((now) =>
			table.then((t) => {
				if (live) day = t?.anniversaryOn(writer, now) ?? null;
			})
		);
		return () => {
			live = false;
			stop();
		};
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
