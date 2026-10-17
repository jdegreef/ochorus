<script lang="ts">
	import { QR_MARGIN, qrMatrix } from '$lib/qr';

	/**
	 * A link as a QR code ($lib/qr): one crisp SVG path, black on white with
	 * its quiet zone whatever the theme — a scanner wants dark on light, and a
	 * night palette's light-on-dark code reads on far fewer phones. It sizes to
	 * its box (`class`), so the same code serves a card and a printed page.
	 */
	let { value, label, class: cls = '' }: { value: string; label: string; class?: string } = $props();

	const qr = $derived(qrMatrix(value));
	const box = $derived(qr.size + QR_MARGIN * 2);
</script>

<svg
	class="qr {cls}"
	viewBox="-{QR_MARGIN} -{QR_MARGIN} {box} {box}"
	shape-rendering="crispEdges"
	role="img"
	aria-label={label}
>
	<rect x={-QR_MARGIN} y={-QR_MARGIN} width={box} height={box} fill="white" />
	<path d={qr.path} fill="black" />
</svg>

<style>
	.qr {
		display: block;
		aspect-ratio: 1;
		height: auto;
		border-radius: 0.375rem;
	}
</style>
