<script lang="ts">
	/**
	 * A text arrow that points the way of reading: → onward, ← back — both
	 * mirrored in a right-to-left locale, where onward is leftward. Arrows are
	 * not bidi-mirrored characters (unlike ‹ ›), so a bare "→" in Arabic points
	 * backwards. Decorative: the link or button text beside it carries the
	 * meaning.
	 */
	let { back = false }: { back?: boolean } = $props();
</script>

<span class="arrow" aria-hidden="true">{back ? '←' : '→'}</span>

<style>
	.arrow {
		display: inline-block;
	}
	:global([dir='rtl']) .arrow {
		transform: scaleX(-1);
	}
</style>
