<script lang="ts">
	import { getLang } from '$lib/lang.svelte';
	import { onPageShown } from '$lib/pageHidden';
	import * as m from '$lib/paraglide/messages.js';
	import Candle from '$lib/components/Candle.svelte';

	/**
	 * On the writer's birthday (or the day they died), a candle and the day by
	 * their name on their page: "Born on this day, 13 November 354".
	 *
	 * Decided in the browser, never at render: the author pages are
	 * prerendered on the build's day and must not carry it into every other.
	 * Re-checked when the tab comes back into view, so a page left open across
	 * midnight lights (and puts out) the candle with the day. The table of days
	 * is loaded only then, after the page's first paint, not in its bundle.
	 */
	let { slug }: { slug: string } = $props();
	let said = $state('');
	$effect(() => {
		const writer = slug;
		const lang = getLang();
		let live = true;
		const days = import('$lib/authorDays');
		const stop = onPageShown(() =>
			days.then(({ anniversaryOn, anniversaryDate }) => {
				const day = anniversaryOn(writer, new Date());
				if (!live) return;
				const date = day ? anniversaryDate(day.date, lang) : '';
				said = !day ? '' : day.kind === 'born' ? m.author_born_today({ date }) : m.author_died_today({ date });
			})
		);
		return () => {
			live = false;
			stop();
		};
	});
</script>

{#if said}
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
