<script lang="ts">
	import { onMount } from 'svelte';
	import { listSermons, type SermonSummary } from '$lib/library-public';
	import { getLang } from '$lib/lang.svelte';
	import { readingTime } from '$lib/reading';
	import { i18n } from '$lib/i18n.svelte';
	import { localizeHref } from '$lib/href';
	import { portraitPosition } from '$lib/portraits';
	import SermonPlate from '$lib/components/SermonPlate.svelte';

	const t = i18n.t;

	/**
	 * "Sermon of the week" — a weekly rotating pick from the sermon shelf.
	 * Deterministic (ISO week number modulo shelf size), so every visitor sees
	 * the same sermon all week and it advances with no manual step. Fetched
	 * CLIENT-SIDE: the homepage is prerendered, and baking the pick at build
	 * time would freeze it on whatever week the site last deployed.
	 */
	// `embedded` drops the home-page section chrome (own max-width + top
	// padding) so the card can sit inside another page's column (e.g. the
	// sermons shelf) without fighting its container.
	let { embedded = false }: { embedded?: boolean } = $props();

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
	<section class={embedded ? '' : 'page-col px-5 pt-14'}>
		<!-- The plate IS this panel's card, so the hover affordance the old
		     bordered box had has to live here — the plate itself heads a page
		     more often than it is a link, and shouldn't assume it is one. Same
		     moves as .shelf-card:hover, mixed off the plate's own hue. -->
		<a href={localizeHref(`/sermons/${pick.slug}`)} class="plate-link block hover:no-underline">
			<SermonPlate
				slug={pick.slug}
				compact
				portrait={pick.author.photo_url
					? { src: pick.author.photo_url, pos: portraitPosition(pick.author.slug) }
					: null}
			>
				<p class="eyebrow mb-2 text-accent">
					{t('home.sermonOfWeek')}
				</p>
				<h2 class="text-h2 mb-1">{pick.title}</h2>
				<p class="text-small text-muted">
					<!-- The separators are expressions: text at an {#if} block boundary gets
					     its leading whitespace trimmed by the compiler, which rendered
					     "A. B. Simpson· 1 Kings" with the space missing. -->
					{pick.author.name}{#if pick.scripture_ref}{` · ${pick.scripture_ref}`}{/if}
					· {readingTime(pick.word_count)} — {t('home.sermonReadOrListen')} ▶
				</p>
			</SermonPlate>
		</a>
	</section>
{/if}

<style>
	/* The lift language (STYLE_GUIDE §5 → "Card hover"), hue-mixed like
	   .shelf-card — but it cannot wear the shared .card-lift:hover, because the
	   thing that lifts (the nested .sermon-plate) is not the thing that takes the
	   interaction: the <a> is, and it must lift the plate on BOTH pointer hover
	   and keyboard :focus-visible (the plate is not focusable). So the recipe is
	   restated here against the parent trigger; the values match .shelf-card's
	   hue lift on purpose. */
	.plate-link > :global(.sermon-plate) {
		transition:
			border-color var(--duration-fast),
			box-shadow var(--duration-fast),
			transform var(--duration-fast);
	}
	.plate-link:hover > :global(.sermon-plate),
	.plate-link:focus-visible > :global(.sermon-plate) {
		border-color: color-mix(in srgb, var(--band-hue) 55%, var(--border));
		box-shadow: 0 6px 20px -12px color-mix(in srgb, var(--band-hue) 70%, transparent);
		transform: translateY(-2px);
	}
	@media (prefers-reduced-motion: reduce) {
		.plate-link:hover > :global(.sermon-plate),
		.plate-link:focus-visible > :global(.sermon-plate) {
			transform: none;
		}
	}
</style>
