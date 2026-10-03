<!--
	The admin's small trend line: a soft fill, the line, and a dot on the latest
	point. `partial` draws the last segment dashed and unfilled, for a week still
	in progress, so it never reads as a drop (the weekly chart outlines it the
	same way). `mark` puts a red dot on one point (a book's steepest drop).
-->
<script lang="ts">
	let {
		values,
		labels,
		name,
		description,
		partial = false,
		mark = -1,
		width = 72,
		height = 28,
		format = (n: number) => String(n)
	}: {
		values: number[];
		/** One per value: what each point is ("week of Sep 14"). */
		labels: string[];
		/** What the line plots, for screen readers ("Hearts per week"). */
		name: string;
		/** Overrides the generated "name: label value, …" text. */
		description?: string;
		partial?: boolean;
		mark?: number;
		width?: number;
		height?: number;
		format?: (n: number) => string;
	} = $props();

	const max = $derived(Math.max(1, ...values));
	const x = (i: number) => (values.length > 1 ? (i / (values.length - 1)) * width : width / 2);
	const y = (v: number) => height - 2 - (v / max) * (height - 6);
	const pts = $derived(values.map((v, i) => `${x(i).toFixed(1)},${y(v).toFixed(1)}`));
	const solid = $derived(partial ? pts.slice(0, -1) : pts);
	const last = $derived(values.length - 1);
	const text = $derived(
		description ?? `${name}: ` + values.map((v, i) => `${labels[i]} ${format(v)}`).join(', ')
	);
</script>

{#if values.length > 1}
	<svg class="spark" {width} {height} viewBox="0 0 {width} {height}" role="img" aria-label={text}>
		<title>{text}</title>
		<polygon points="0,{height} {solid.join(' ')} {x(solid.length - 1).toFixed(1)},{height}" class="fill-accent-soft" />
		<polyline points={solid.join(' ')} fill="none" class="stroke-accent" stroke-width="1.6" stroke-linejoin="round" stroke-linecap="round" />
		{#if partial}
			<line x1={x(last - 1)} y1={y(values[last - 1])} x2={x(last)} y2={y(values[last])} class="stroke-accent" stroke-width="1.6" stroke-dasharray="2 2" />
		{/if}
		<circle cx={x(last)} cy={y(values[last])} r="2.5" class="fill-accent" />
		{#if mark >= 0 && mark < values.length}
			<circle cx={x(mark)} cy={y(values[mark])} r="2.5" class="fill-danger" />
		{/if}
	</svg>
{/if}

<style>
	.spark {
		display: block;
		flex: none;
		overflow: visible;
	}
</style>
