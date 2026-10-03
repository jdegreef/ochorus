<script lang="ts">
	/**
	 * A printer's ornament: a leaf between two hairlines, in gold. Book pages
	 * mark a title or a break this way; the site used empty space for both.
	 *
	 * Gold here is what STYLE_GUIDE §1 says gold is for — ornament, never a
	 * message — so it carries no meaning and is hidden from assistive tech.
	 * Symmetric, so it needs no mirroring in a right-to-left locale.
	 */
</script>

<div class="fleuron" aria-hidden="true">
	<span></span>
	<svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="currentColor" stroke-width="1.4" stroke-linecap="round">
		<path d="M12 2.5c-4.5 4.5-4.5 14.5 0 19 4.5-4.5 4.5-14.5 0-19z" />
		<path d="M12 6v12" />
	</svg>
	<span></span>
</div>

<style>
	.fleuron {
		display: flex;
		align-items: center;
		gap: 0.5rem;
		width: 10rem;
		color: var(--gold);
	}
	.fleuron span {
		flex: 1;
		height: 1px;
		background: currentColor;
		opacity: 0.45;
	}
</style>
