<script lang="ts">
	import type { Anniversary } from '$lib/authorDays';
	import { localizeHref } from '$lib/href';
	import { anniversaryYear } from '$lib/anniversaryFormat';
	import { getLang } from '$lib/lang.svelte';
	import { watchToday } from '$lib/today';
	import * as m from '$lib/paraglide/messages.js';
	import Candle from '$lib/components/Candle.svelte';

	/**
	 * The home dashboard's birthday candles: a writer of the library born, or
	 * gone home, on this day — "Augustine of Hippo was born on this day in
	 * 354" — each a way to their page. Nothing at all on the many days that
	 * are nobody's (`$lib/authorDays` keeps the days).
	 *
	 * The reader's own day, re-read as it turns ($lib/today). The table of
	 * days loads after the dashboard's first paint, not in its bundle.
	 */
	const table = import('$lib/authorDays').catch(() => null);
	let days = $state<Anniversary[]>([]);
	$effect(() => {
		let live = true;
		const stop = watchToday((now) =>
			table.then((t) => {
				if (live) days = t?.anniversariesOn(now) ?? [];
			})
		);
		return () => {
			live = false;
			stop();
		};
	});
	const said = ({ name, year, kind }: Anniversary) => {
		const y = anniversaryYear(year, getLang());
		return kind === 'born' ? m.home_born_today({ name, year: y }) : m.home_died_today({ name, year: y });
	};
</script>

{#if days.length}
	<section class="page-col px-5 pt-6" aria-label={m.home_on_this_day()}>
		<ul class="on-this-day">
			{#each days as a (a.slug + a.kind)}
				<li>
					<Candle />
					<a href={localizeHref(`/authors/${a.slug}`)}>{said(a)}</a>
				</li>
			{/each}
		</ul>
	</section>
{/if}

<style>
	.on-this-day {
		display: flex;
		flex-wrap: wrap;
		gap: 0.5rem 1.5rem;
		font-size: var(--fs-small);
	}
	li {
		display: inline-flex;
		align-items: center;
		gap: 0.5em;
	}
	a {
		color: var(--text);
	}
	a:hover {
		color: var(--accent);
	}
</style>
