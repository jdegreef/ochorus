<script lang="ts">
	import Icon from '$lib/components/Icon.svelte';
	import QrCode from '$lib/components/QrCode.svelte';
	import { downloadFile } from '$lib/dataExport';
	import type { ForChrome } from '$lib/forChrome';
	import { IS_APP } from '$lib/platform';

	/**
	 * A link's QR code on request — the toggle, the code, and a download of it
	 * as an SVG for a slide, a newsletter or a print shop. Shared by the
	 * "Ochorus for …" pages' tools (the reading-group link, the invite kit).
	 * The phone apps' WebView can't save a file, so there the code shows alone.
	 */
	let {
		value,
		label,
		filename,
		words,
		ondownload
	}: {
		value: string;
		/** What the code reads as, for a screen reader and the file's title. */
		label: string;
		filename: string;
		words: ForChrome['qr'];
		ondownload?: () => void;
	} = $props();

	let open = $state(false);

	async function download() {
		const { qrSvg } = await import('$lib/qr');
		downloadFile(filename, 'image/svg+xml', qrSvg(value, label));
		ondownload?.();
	}
</script>

<button type="button" class="btn btn-sm" aria-expanded={open} onclick={() => (open = !open)}>
	<Icon name="qr" size={15} />
	{open ? words.hide : words.show}
</button>

{#if open}
	<div class="qr-box">
		<QrCode {value} label={words.alt(label)} class="w-40" />
		{#if !IS_APP}
			<button type="button" class="btn btn-sm btn-ghost" onclick={download}>
				<Icon name="download" size={15} />
				{words.download}
			</button>
		{/if}
	</div>
{/if}

<style>
	/* A row of its own under the buttons it sits among (a flex-wrap row). */
	.qr-box {
		flex-basis: 100%;
		display: flex;
		flex-wrap: wrap;
		align-items: end;
		gap: 0.75rem;
		margin-top: 0.5rem;
	}
</style>
