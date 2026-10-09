<script lang="ts">
	import Icon from '$lib/components/Icon.svelte';
	import { messageShareLinks } from '$lib/share';

	/**
	 * An "Ochorus for …" page's "pass it on" kit: the ready-made message a
	 * leader drops into a bulletin, a group chat or an email, shown in full so
	 * they can see exactly what they would send, with one tap to copy it, send
	 * it on WhatsApp (how this content travels) or open it in their mail app.
	 * English-only like the page, so the words are literals, not catalogue keys.
	 */
	let { message, subject }: { message: string; subject: string } = $props();

	const [whatsapp, email] = $derived(messageShareLinks(subject, message, 'Email'));
	let text = $state<HTMLElement>();
	/** What the last copy did, for the status line: done, or select-it-yourself. */
	let copied = $state<'yes' | 'select' | null>(null);
	let timer: ReturnType<typeof setTimeout> | undefined;
	$effect(() => () => clearTimeout(timer));

	async function copy() {
		try {
			await navigator.clipboard.writeText(message);
			copied = 'yes';
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
			{copied === 'yes' ? 'Copied' : 'Copy the message'}
		</button>
		<a class="btn btn-sm" href={whatsapp.href} target="_blank" rel="noopener noreferrer">
			<Icon name="share" size={15} /> {whatsapp.name}
		</a>
		<a class="btn btn-sm" href={email.href}><Icon name="mail" size={15} /> {email.name}</a>
		<!-- The copy's outcome, announced apart from the button that caused it. -->
		<span class="text-small text-muted" role="status"
			>{#if copied === 'select'}Selected: press Ctrl+C, or long-press and Copy.{:else if copied === 'yes'}<span
					class="sr-only">Message copied</span
				>{/if}</span
		>
	</div>
</div>

<style>
	.message {
		white-space: pre-line;
		border-inline-start: 3px solid color-mix(in srgb, var(--group, var(--color-accent)) 60%, transparent);
		padding-inline-start: 1rem;
		overflow-wrap: anywhere;
	}
</style>
