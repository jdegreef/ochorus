<script lang="ts">
	/**
	 * The author-page lifespan timeline. Two modes, chosen by the data:
	 *
	 * - **Milestones present** — the axis spans the author's own events (born →
	 *   died) and each is plotted as a labelled dot, so the reader walks the life
	 *   rather than reading two bare years floating on an empty century. Only the
	 *   handful of curated authors have these; everyone else falls through to:
	 * - **Bare lifespan** — the life drawn as an accent segment on a century-scale
	 *   axis, the original behaviour, so an un-curated author is unchanged.
	 *
	 * Pure computation from the props — renders nothing without at least the two
	 * years.
	 */
	import type { Milestone } from '$lib/library-public';

	interface Props {
		birthYear: number | null;
		deathYear: number | null;
		milestones?: Milestone[];
		/** Show the event LABELS. The milestone labels are hand-authored ENGLISH,
		 *  so on a localized page (`labels={false}`) we render the dots and years
		 *  only — the years are universal — rather than print untranslated words
		 *  beside a translated bio. */
		labels?: boolean;
	}
	let { birthYear, deathYear, milestones = [], labels = true }: Props = $props();

	// --- Milestone mode -------------------------------------------------------
	// Sorted, valid events. Two is the floor: a lone dot is not a timeline, and
	// the axis needs a span. The years drive the axis directly (not birth/death),
	// so a curated list is authoritative — it carries its own "Born"/"Died".
	const events = $derived(
		[...(milestones ?? [])]
			.filter((m) => typeof m?.year === 'number' && !!m?.label)
			.sort((a, b) => a.year - b.year)
	);
	const span = $derived.by(() => {
		if (events.length < 2) return null;
		const lo = events[0].year;
		const hi = events[events.length - 1].year;
		return hi > lo ? { lo, hi } : null;
	});
	// SVG geometry. A fixed viewBox the CSS scales to the column width; padding
	// leaves room for the outermost year labels not to clip.
	const PAD = 40;
	const W = 640;
	const ex = (year: number) => (span ? PAD + ((year - span.lo) / (span.hi - span.lo)) * (W - PAD * 2) : 0);

	// --- Bare-lifespan fallback (unchanged) -----------------------------------
	const domain = $derived.by(() => {
		if (birthYear == null || deathYear == null || deathYear < birthYear) return null;
		const start = Math.floor(birthYear / 100) * 100;
		const end = Math.ceil(deathYear / 100) * 100;
		return { start, end: end === start ? start + 100 : end };
	});
	const pct = (year: number) =>
		domain ? ((year - domain.start) / (domain.end - domain.start)) * 100 : 0;
	const ticks = $derived.by(() => {
		if (!domain) return [];
		const out: number[] = [];
		for (let y = domain.start; y <= domain.end; y += 100) out.push(y);
		return out;
	});
</script>

{#if span}
	<!-- Milestone timeline. Decorative in the sense that every fact here is also
	     in the prose, so it carries an aria-label summary and hides the dots from
	     the a11y tree; each dot still names itself via <title> for pointer users. -->
	<figure
		class="life-events mx-auto mt-6 max-w-[40rem]"
		aria-label={labels
			? `Timeline: ${events[0].label} (${events[0].year}) to ${events[events.length - 1].label} (${events[events.length - 1].year})`
			: `${events[0].year}–${events[events.length - 1].year}`}
	>
		<!-- Labels alternate ABOVE and BELOW the axis (even index below, odd above),
		     so two adjacent events never share a horizontal band — the only way a
		     short axis can carry the tighter clusters a real life throws up (a
		     conversion two years before an ordination) without the words colliding.
		     A hairline stem ties each label back to its dot. -->
		<svg class="ev-svg" viewBox="0 0 {W} 82" role="img" aria-hidden="true">
			<line class="ev-axis" x1={PAD} y1="41" x2={W - PAD} y2="41"></line>
			<line class="ev-life" x1={ex(span.lo)} y1="41" x2={ex(span.hi)} y2="41"></line>
			{#each events as m, i (m.year + m.label)}
				{@const below = i % 2 === 0}
				<g class="ev" class:key={m.key}>
					<title>{m.year}{labels ? ` — ${m.label}` : ''}</title>
					<line class="ev-stem" x1={ex(m.year)} y1="41" x2={ex(m.year)} y2={below ? 48 : 34}
					></line>
					<circle cx={ex(m.year)} cy="41" r={m.key ? 5.5 : 4.5}></circle>
					<text class="ev-yr" x={ex(m.year)} y={below ? 60 : 29} text-anchor="middle">{m.year}</text>
					{#if labels}
						<text class="ev-lb" x={ex(m.year)} y={below ? 73 : 16} text-anchor="middle">{m.label}</text>
					{/if}
				</g>
			{/each}
		</svg>
	</figure>
{:else if domain && birthYear != null && deathYear != null}
	<div class="life-timeline mx-auto mt-6 max-w-[40rem]" aria-hidden="true">
		<div class="track">
			{#each ticks as y (y)}
				<span class="tick" style="left: {pct(y)}%">
					<span class="tick-label">{y}</span>
				</span>
			{/each}
			<span class="span" style="left: {pct(birthYear)}%; right: {100 - pct(deathYear)}%">
				<span class="dot start"></span>
				<span class="dot end"></span>
			</span>
			<span class="year year-start" style="left: {pct(birthYear)}%">{birthYear}</span>
			<span class="year year-end" style="left: {pct(deathYear)}%">{deathYear}</span>
		</div>
	</div>
{/if}

<style>
	/* ── Milestone timeline ─────────────────────────────────────────────────── */
	.life-events {
		margin-block-start: 1.5rem;
	}
	.ev-svg {
		width: 100%;
		height: auto;
		display: block;
		overflow: visible;
	}
	.ev-axis {
		stroke: var(--border);
		stroke-width: 2;
	}
	.ev-life {
		stroke: var(--accent);
		stroke-width: 3;
		stroke-linecap: round;
	}
	/* Hairline tying each label back to its dot across the axis. */
	.ev-stem {
		stroke: var(--border);
		stroke-width: 1;
	}
	.ev circle {
		fill: var(--bg);
		stroke: var(--accent);
		stroke-width: 2.5;
	}
	.ev.key circle {
		fill: var(--accent);
	}
	.ev-yr {
		font-family: var(--font-sans);
		font-weight: 600;
		font-size: var(--fs-eyebrow);
		fill: var(--text);
		font-variant-numeric: tabular-nums;
	}
	.ev-lb {
		font-family: var(--font-sans);
		font-size: var(--fs-micro);
		fill: var(--muted);
	}
	.ev.key .ev-lb {
		fill: var(--accent);
	}

	/* ── Bare-lifespan fallback (unchanged) ─────────────────────────────────── */
	.track {
		position: relative;
		height: 3.5rem;
		margin-top: 1.25rem;
	}
	.track::before {
		content: '';
		position: absolute;
		inset-inline: 0;
		top: 1.6rem;
		height: 2px;
		background: var(--border);
		border-radius: 2px;
	}
	.tick {
		position: absolute;
		top: 1.2rem;
		width: 1px;
		height: 0.8rem;
		background: var(--border);
		transform: translateX(-0.5px);
	}
	.tick-label {
		position: absolute;
		top: 1.1rem;
		left: 50%; /* rtl-ok: paired with the inline left:%% positions above */
		transform: translateX(-50%);
		font-size: var(--fs-micro);
		color: var(--muted);
		white-space: nowrap;
	}
	.span {
		position: absolute;
		top: 1.45rem;
		height: 5px;
		background: var(--accent);
		border-radius: 999px;
	}
	.dot {
		position: absolute;
		top: 50%;
		width: 9px;
		height: 9px;
		border-radius: 999px;
		background: var(--accent);
		transform: translate(-50%, -50%);
	}
	.dot.start {
		left: 0; /* rtl-ok: chart coordinate, see .tick-label */
	}
	.dot.end {
		left: 100%; /* rtl-ok: chart coordinate, see .tick-label */
	}
	.year {
		position: absolute;
		top: 0;
		font-family: var(--font-display);
		font-size: var(--fs-small);
		font-weight: 600;
		color: var(--text);
	}
	.year-start {
		transform: translateX(-50%);
	}
	.year-end {
		transform: translateX(-50%);
	}
</style>
