<script lang="ts">
	import type { QrMatrix } from '$lib/qr';

	/**
	 * A link as a QR code ($lib/qr): one crisp SVG path, black on white with
	 * its quiet zone whatever the theme — a scanner wants dark on light, and a
	 * night palette's light-on-dark code reads on far fewer phones. It sizes to
	 * its box (`class`), so the same code serves a card and a printed page.
	 *
	 * The encoder loads when a code is first drawn, not with the page: a code
	 * is only shown on request, and most visitors never ask for one.
	 */
	let { value, label, class: cls = '' }: { value: string; label: string; class?: string } = $props();

	let qr = $state<(QrMatrix & { margin: number }) | null>(null);
	$effect(() => {
		const text = value;
		let live = true;
		import('$lib/qr').then(({ qrMatrix, QR_MARGIN }) => {
			if (live) qr = { ...qrMatrix(text), margin: QR_MARGIN };
		});
		return () => (live = false);
	});
	const box = $derived(qr ? qr.size + qr.margin * 2 : 0);
</script>

{#if qr}
	<svg
		class="qr {cls}"
		viewBox="-{qr.margin} -{qr.margin} {box} {box}"
		shape-rendering="crispEdges"
		role="img"
		aria-label={label}
	>
		<rect x={-qr.margin} y={-qr.margin} width={box} height={box} fill="white" />
		<path d={qr.path} fill="black" />
	</svg>
{:else}
	<div class="qr {cls}" aria-hidden="true"></div>
{/if}

<style>
	.qr {
		display: block;
		aspect-ratio: 1;
		height: auto;
		border-radius: 0.375rem;
	}
</style>
