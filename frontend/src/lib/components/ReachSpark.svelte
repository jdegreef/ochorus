<script lang="ts">
	import { formatRate, type EngagementReach } from '$lib/library-admin';

	// A book's "where readers stop" curve at a glance, for a leaderboard row:
	// the share of its readers reaching each chapter, with the steepest drop
	// dotted.
	let { reach }: { reach: EngagementReach } = $props();

	const W = 96;
	const H = 24;
	const top = $derived(Math.max(1, reach.reached[0] ?? 0));
	const x = (i: number) => (reach.reached.length > 1 ? (i / (reach.reached.length - 1)) * W : W / 2);
	const y = (n: number) => H - 1 - (n / top) * (H - 2);
	const line = $derived(reach.reached.map((n, i) => `${x(i).toFixed(1)},${y(n).toFixed(1)}`).join(' '));
	const cliffIndex = $derived(reach.steepest ? reach.chapters.indexOf(reach.steepest.chapter) : -1);
	const last = $derived(reach.reached.at(-1) ?? 0);
	const label = $derived(
		[
			`${formatRate(last / top)} reach the last chapter (${reach.language})`,
			reach.steepest ? `${formatRate(reach.steepest.rate)} stop at chapter ${reach.steepest.chapter}` : ''
		]
			.filter(Boolean)
			.join(' · ')
	);
</script>

<svg width={W} height={H} viewBox="0 0 {W} {H}" role="img" aria-label={label} class="overflow-visible">
	<title>{label}</title>
	<polyline points="0,{H} {line} {W},{H}" class="fill-accent-soft" />
	<polyline points={line} fill="none" class="stroke-accent" stroke-width="1.5" stroke-linejoin="round" />
	{#if cliffIndex >= 0}
		<circle cx={x(cliffIndex)} cy={y(reach.reached[cliffIndex])} r="2.5" class="fill-danger" />
	{/if}
</svg>
