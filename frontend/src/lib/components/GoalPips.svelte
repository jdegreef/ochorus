<script lang="ts">
	/**
	 * The weekly-goal row: one pip per goal day, gold up to this week's read-day
	 * count. Shared by the home nudge, the dashboard stats and Settings, which
	 * had grown three copies (and three edits whenever the colours changed).
	 *
	 * The empty pip is `border-strong` at 40%, not `--border`: on the dark
	 * theme's `--surface-2` cards `--border` is nearly the same colour, so the
	 * unread days vanished and "2 of 4" showed two pips.
	 */
	let { goal, weekCount, stretch = false }: { goal: number; weekCount: number; stretch?: boolean } =
		$props();
</script>

<div class="flex gap-1.5">
	{#each Array(goal) as _, i (i)}
		<span
			class="h-2 rounded-full {stretch ? 'flex-1' : 'w-6'} {i < weekCount
				? 'bg-gold'
				: 'bg-border-strong/40'}"
		></span>
	{/each}
</div>
