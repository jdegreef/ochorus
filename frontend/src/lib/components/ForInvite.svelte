<script lang="ts">
	import Icon from '$lib/components/Icon.svelte';
	import PrintFlyer, { type Flyer } from '$lib/components/PrintFlyer.svelte';
	import QrCode from '$lib/components/QrCode.svelte';
	import { downloadFile } from '$lib/dataExport';
	import type { ForChrome } from '$lib/forChrome';
	import { qrSvg } from '$lib/qr';
	import { messageShareLinks } from '$lib/share';

	/**
	 * An "Ochorus for …" page's "pass it on" kit: the ready-made message a
	 * leader drops into a bulletin, a group chat or an email, shown in full so
	 * they can see exactly what they would send, with one tap to copy it, send
	 * it on WhatsApp (how this content travels) or open it in their mail app.
	 * Its words come with the page's copy ($lib/forChrome), not the catalogues.
	 *
	 * For a room rather than a chat, the same link as a QR code (for the
	 * projector slide or the noticeboard) and as a printed bulletin insert.
	 */
	let {
		message,
		subject,
		words,
		link,
		flyer,
		chrome,
		onaction
	}: {
		message: string;
		subject: string;
		words: ForChrome['invite'];
		/** The link the message ends with, which the code and the insert carry. */
		link: string;
		flyer: Flyer;
		chrome: Pick<ForChrome, 'qr' | 'flyer'>;
		/** Reports what the leader did, for the page's analytics. */
		onaction?: (action: string) => void;
	} = $props();
	let showQr = $state(false);

	const [whatsapp, email] = $derived(messageShareLinks(subject, message, words.email));
	let text = $state<HTMLElement>();
	/** What the last copy did, for the status line: done, or select-it-yourself. */
	let copied = $state<'yes' | 'select' | null>(null);
	let timer: ReturnType<typeof setTimeout> | undefined;
	$effect(() => () => clearTimeout(timer));

	async function copy() {
		try {
			await navigator.clipboard.writeText(message);
			copied = 'yes';
			onaction?.('invite-copy');
		} catch {
			// No clipboard here (an in-app browser, a denied permission): select
			// the message so one long-press or Ctrl+C copies it, and say so.
			if (text) getSelection()?.selectAllChildren(text);
			copied = 'select';
		}
		clearTimeout(timer);
		timer = setTimeout(() => (copied = null), 4000);
	}
</script>

<div class="invite rounded-card border border-border bg-surface p-5">
	<!-- The whole message as it will be sent, link included: selectable by hand
	     where the copy button can't reach the clipboard. -->
	<blockquote class="message text-body" bind:this={text}>{message}</blockquote>
	<div class="mt-4 flex flex-wrap items-center gap-2">
		<button type="button" class="btn btn-sm" onclick={copy}>
			<Icon name={copied === 'yes' ? 'check' : 'page'} size={15} />
			{copied === 'yes' ? words.copied : words.copy}
		</button>
		<a
			class="btn btn-sm"
			href={whatsapp.href}
			target="_blank"
			rel="noopener noreferrer"
			onclick={() => onaction?.('invite-whatsapp')}
		>
			<Icon name="share" size={15} /> {whatsapp.name}
		</a>
		<a class="btn btn-sm" href={email.href} onclick={() => onaction?.('invite-email')}
			><Icon name="mail" size={15} /> {email.name}</a
		>
		<button type="button" class="btn btn-sm" aria-expanded={showQr} onclick={() => (showQr = !showQr)}>
			<Icon name="qr" size={15} />
			{showQr ? chrome.qr.hide : chrome.qr.show}
		</button>
		<PrintFlyer label={chrome.flyer.print} {flyer} onprint={() => onaction?.('invite-flyer')} />
		<!-- The copy's outcome, announced apart from the button that caused it. -->
		<span class="text-small text-muted" role="status"
			>{#if copied === 'select'}{words.selected}{:else if copied === 'yes'}<span class="sr-only"
					>{words.announced}</span
				>{/if}</span
		>
	</div>
	{#if showQr}
		<div class="qr-box mt-4">
			<QrCode value={link} label={flyer.qrLabel} class="w-40" />
			<button
				type="button"
				class="btn btn-sm btn-ghost"
				onclick={() => {
					downloadFile('ochorus-qr.svg', 'image/svg+xml', qrSvg(link, flyer.title));
					onaction?.('invite-qr-download');
				}}
			>
				<Icon name="download" size={15} />
				{chrome.qr.download}
			</button>
		</div>
	{/if}
</div>

<style>
	.qr-box {
		display: flex;
		flex-wrap: wrap;
		align-items: end;
		gap: 0.75rem;
	}
	.message {
		white-space: pre-line;
		border-inline-start: 3px solid color-mix(in srgb, var(--group, var(--color-accent)) 60%, transparent);
		padding-inline-start: 1rem;
		overflow-wrap: anywhere;
	}
</style>
