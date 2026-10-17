<script module lang="ts">
	/** What a printed notice says, and the link it carries. */
	export interface Flyer {
		eyebrow: string;
		title: string;
		/** A line under the title: the schedule, or the page's one-line pitch. */
		line?: string;
		/** The link the code and the printed address both carry. */
		url: string;
		scan: string;
		free: string;
		qrLabel: string;
	}
</script>

<script lang="ts">
	import { tick } from 'svelte';
	import Icon from '$lib/components/Icon.svelte';
	import QrCode from '$lib/components/QrCode.svelte';
	import { portal } from '$lib/actions/portal';
	import { IS_APP } from '$lib/platform';

	/**
	 * A bulletin insert, printed: the button prints a sheet holding two copies
	 * of a half-page notice — what to read, from when, a QR code and the link
	 * spelled out — with a cut line between, which is how a church hands a
	 * thing out on a Sunday. Nothing is generated server-side: the notice is
	 * drawn into the page only while printing, portalled to <body> so the print
	 * rule can hide everything else (`html.print-flyer`), and taken away after.
	 * The phone apps' WebView has no print(), so there the button isn't shown.
	 */

	let { label, flyer, onprint }: { label: string; flyer: Flyer; onprint?: () => void } = $props();

	let printing = $state(false);
	/** The address as it prints: no scheme, no trailing slash — shortest to type. */
	const shown = $derived(flyer.url.replace(/^https?:\/\//, '').replace(/\/$/, ''));

	async function print() {
		printing = true;
		await tick();
		// The code draws once its encoder has loaded (QrCode); let it land.
		await import('$lib/qr');
		await tick();
		const html = document.documentElement;
		html.classList.add('print-flyer');
		const done = () => {
			html.classList.remove('print-flyer');
			printing = false;
			removeEventListener('afterprint', done);
		};
		addEventListener('afterprint', done);
		onprint?.();
		// The flyer stays until the print is done with it: a phone's print sheet
		// can take seconds to lay out the preview, so no timer takes it away.
		window.print();
	}
</script>

{#if !IS_APP}
	<button type="button" class="btn btn-sm" onclick={print}>
		<Icon name="print" size={15} />
		{label}
	</button>
{/if}

{#if printing}
	<div class="for-flyer" use:portal aria-hidden="true">
		{#each [0, 1] as copy (copy)}
			<section class="half">
				<div class="text">
					<p class="kicker">{flyer.eyebrow}</p>
					<h2 class="title">{flyer.title}</h2>
					{#if flyer.line}<p class="line">{flyer.line}</p>{/if}
					<p class="free">{flyer.free}</p>
					<p class="scan">{flyer.scan}<br /><strong class="url">{shown}</strong></p>
				</div>
				<QrCode value={flyer.url} label={flyer.qrLabel} class="code" />
				<p class="brand">Ochorus</p>
			</section>
		{/each}
	</div>
{/if}

<style>
	.for-flyer {
		display: none;
	}
	@media print {
		/* While a flyer prints, it is the only thing on the paper. */
		:global(html.print-flyer body > *:not(.for-flyer)) {
			display: none !important;
		}
		.for-flyer {
			display: block;
			color: #000; /* hex-ok: ink on paper, whatever the screen theme */
			background: #fff; /* hex-ok: paper */
			font-family: var(--font-display, Georgia, serif);
		}
		.half {
			position: relative;
			box-sizing: border-box;
			/* Two to a sheet inside the browser's default margins on A4 and on
			   US Letter (the shorter): 2 × 125mm fits Letter's ~259mm. No @page
			   rule — it would reach every other print on the site. */
			height: 125mm;
			padding: 10mm 12mm;
			display: grid;
			grid-template-columns: minmax(0, 1fr) 46mm;
			gap: 10mm;
			align-items: center;
			break-inside: avoid;
		}
		.half + .half {
			border-top: 1px dashed #777; /* hex-ok: the cut line */
		}
		.kicker {
			font-size: 10pt;
			letter-spacing: 0.12em;
			text-transform: uppercase;
		}
		.title {
			margin-top: 3mm;
			font-size: 24pt;
			line-height: 1.15;
			font-weight: 600;
		}
		.line {
			margin-top: 4mm;
			font-size: 13pt;
		}
		.free {
			margin-top: 6mm;
			font-size: 11pt;
		}
		.scan {
			margin-top: 6mm;
			font-size: 10pt;
		}
		.url {
			font-size: 12pt;
			overflow-wrap: anywhere;
		}
		.half :global(.code) {
			width: 46mm;
		}
		.brand {
			position: absolute;
			inset-inline-end: 12mm;
			bottom: 8mm;
			font-size: 11pt;
			font-weight: 600;
			letter-spacing: 0.06em;
		}
	}
</style>
