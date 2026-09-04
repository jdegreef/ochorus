<script lang="ts">
	/**
	 * A section title with an optional "see all" link beside it.
	 *
	 * Five places wrote this row by hand — three on the home page, plus
	 * Recommended and Your plans — with `mb-6` on four of them and `mb-4` on the
	 * fifth, and none of them allowed to wrap. On a phone that meant the link
	 * broke across three lines beside a two-line heading ("All / books / →"),
	 * because `justify-between` on a nowrap flex row squeezes the shorter child
	 * until it has nowhere left to go.
	 *
	 * Wrapping is the whole point of having this in one place: the link drops to
	 * its own line when the title needs the width, and sits beside it when it
	 * doesn't. The bottom margin is fixed rather than a prop — mb-4 on one of
	 * the five was the drift, not a requirement.
	 */
	let {
		title,
		href = '',
		linkText = ''
	}: {
		title: string;
		/** Omit for a heading with no link. */
		href?: string;
		/** Link label; the arrow is added here so every one of them matches. */
		linkText?: string;
	} = $props();
</script>

<div class="mb-6 flex flex-wrap items-end justify-between gap-x-4 gap-y-1">
	<h2 class="text-h2">{title}</h2>
	{#if href && linkText}
		<a {href} class="whitespace-nowrap text-small font-semibold text-accent">{linkText} →</a>
	{/if}
</div>
