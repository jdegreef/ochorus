<!--
	A small trend line for a stat tile: a soft fill, the line, and a dot on the
	latest point. `partial` draws the last segment dashed, for a week still in
	progress, so it never reads as a drop (the weekly chart outlines it the
	same way). Hover shows each point's label and value.
-->
<script lang="ts">
	let {
		values,
		labels,
		name,
		partial = false,
		format = (n: number) => String(n)
	}: {
		values: number[];
		/** One per value: what each point is ("Week of Sep 14"). */
		labels: string[];
		/** What the line plots, for screen readers ("Hearts per week"). */
		name: string;
		partial?: boolean;
		format?: (n: number) => string;
	} = $props();

	const W = 72;
	const H = 28;
	const max = $derived(Math.max(1, ...values));
	const x = (i: number) => (values.length > 1 ? (i / (values.length - 1)) * W : W / 2);
	const y = (v: number) => H - 2 - (v / max) * (H - 6);
	const pts = $derived(values.map((v, i) => `${x(i).toFixed(1)},${y(v).toFixed(1)}`));
	const solid = $derived(partial ? pts.slice(0, -1) : pts);
	const last = $derived(values.length - 1);
	const description = $derived(
		`${name}: ` + values.map((v, i) => `${labels[i]} ${format(v)}`).join(', ')
	);
</script>

{#if values.length > 1}
	<svg class="spark" width={W} height={H} viewBox="0 0 {W} {H}" role="img" aria-label={description}>
		<title>{description}</title>
		<polygon points="0,{H} {pts.join(' ')} {W},{H}" class="fill-accent-soft" />
		<polyline points={solid.join(' ')} fill="none" class="stroke-accent" stroke-width="1.6" stroke-linejoin="round" stroke-linecap="round" />
		{#if partial}
			<line x1={x(last - 1)} y1={y(values[last - 1])} x2={x(last)} y2={y(values[last])} class="stroke-accent" stroke-width="1.6" stroke-dasharray="2 2" />
		{/if}
		<circle cx={x(last)} cy={y(values[last])} r="2.5" class="fill-accent" />
	</svg>
{/if}

<style>
	.spark {
		display: block;
		flex: none;
		overflow: visible;
	}
</style>
