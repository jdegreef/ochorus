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

	/**
	 * A bulletin insert, printed: the button prints a sheet holding two copies
	 * of a half-page notice — what to read, from when, a QR code and the link
	 * spelled out — with a cut line between, which is how a church hands a
	 * thing out on a Sunday. Nothing is generated server-side: the notice is
	 * drawn into the page only while printing, portalled to <body> so the print
	 * rule can hide everything else (`html.print-flyer`), and taken away after.
	 */

	let { label, flyer, onprint }: { label: string; flyer: Flyer; onprint?: () => void } = $props();

	let printing = $state(false);
	/** The address as it prints: no scheme, no trailing slash — shortest to type. */
	const shown = $derived(flyer.url.replace(/^https?:\/\//, '').replace(/\/$/, ''));

	async function print() {
		printing = true;
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
		window.print();
		// Browsers whose print() returns only once the dialog closes have fired
		// afterprint by now; a listener left behind is harmless.
		if (!html.classList.contains('print-flyer')) return;
		setTimeout(() => {
			if (!matchMedia('print').matches) done();
		}, 1000);
	}
</script>

<button type="button" class="btn btn-sm" onclick={print}>
	<Icon name="print" size={15} />
	{label}
</button>

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
		@page {
			margin: 0;
		}
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
			height: 148mm; /* half an A5-folded A4; a Letter sheet leaves a margin */
			padding: 16mm 18mm;
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
			inset-inline-end: 18mm;
			bottom: 10mm;
			font-size: 11pt;
			font-weight: 600;
			letter-spacing: 0.06em;
		}
	}
</style>
