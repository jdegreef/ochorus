<script lang="ts">
	import { onMount } from 'svelte';
	import { listSermons, type SermonSummary } from '$lib/library';
	import { getLang } from '$lib/lang.svelte';
	import { readingTime } from '$lib/reading';

	/**
	 * "Sermon of the week" — a weekly rotating pick from the sermon shelf.
	 * Deterministic (ISO week number modulo shelf size), so every visitor sees
	 * the same sermon all week and it advances with no manual step. Fetched
	 * CLIENT-SIDE: the homepage is prerendered, and baking the pick at build
	 * time would freeze it on whatever week the site last deployed.
	 */
	let pick = $state<SermonSummary | null>(null);

	function isoWeek(d: Date): { year: number; week: number } {
		const date = new Date(Date.UTC(d.getFullYear(), d.getMonth(), d.getDate()));
		const day = date.getUTCDay() || 7;
		date.setUTCDate(date.getUTCDate() + 4 - day);
		const year = date.getUTCFullYear();
		const start = new Date(Date.UTC(year, 0, 1));
		const week = Math.ceil(((date.getTime() - start.getTime()) / 86400000 + 1) / 7);
		return { year, week };
	}

	onMount(async () => {
		try {
			const sermons = await listSermons(getLang());
			if (!sermons.length) return;
			const { year, week } = isoWeek(new Date());
			pick = sermons[(year * 53 + week) % sermons.length];
		} catch {
			pick = null;
		}
	});
</script>

{#if pick}
	<section class="mx-auto max-w-5xl px-5 pt-14">
		<a
			href="/sermons/{pick.slug}"
			class="block rounded-card border border-border bg-surface-2 px-6 py-6 transition-colors hover:bg-surface hover:no-underline sm:px-8"
		>
			<p class="mb-2 text-small font-semibold uppercase tracking-widest text-accent">
				Sermon of the Week
			</p>
			<h2 class="text-h2 mb-1">{pick.title}</h2>
			<p class="text-small text-muted">
				{pick.author.name}{#if pick.scripture_ref}
					· {pick.scripture_ref}{/if} · {readingTime(pick.word_count)} — read it, or listen with ▶
			</p>
		</a>
	</section>
{/if}
