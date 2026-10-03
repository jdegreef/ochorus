<script lang="ts">
	import Sparkline from '$lib/components/Sparkline.svelte';
	import { formatRate, type EngagementReach } from '$lib/library-admin';

	// A book's "where readers stop" curve at a glance, for a leaderboard row:
	// the readers reaching each chapter, with the steepest drop dotted red.
	let { reach }: { reach: EngagementReach } = $props();

	const top = $derived(Math.max(1, reach.reached[0] ?? 0));
	const last = $derived(reach.reached.at(-1) ?? 0);
	const description = $derived(
		[
			`${formatRate(last / top)} reach the last chapter (${reach.language})`,
			reach.steepest ? `${formatRate(reach.steepest.rate)} stop at chapter ${reach.steepest.chapter}` : ''
		]
			.filter(Boolean)
			.join(' · ')
	);
</script>

<Sparkline
	values={reach.reached}
	labels={reach.chapters.map((c) => `chapter ${c}`)}
	name="Readers reaching each chapter"
	{description}
	mark={reach.steepest ? reach.chapters.indexOf(reach.steepest.chapter) : -1}
	width={96}
	height={24}
/>
