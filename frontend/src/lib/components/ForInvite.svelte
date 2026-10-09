<script lang="ts">
	import Icon from '$lib/components/Icon.svelte';
	import { inviteLinks } from '$lib/forPages';

	/**
	 * An "Ochorus for …" page's "pass it on" kit: the ready-made message a
	 * leader drops into a bulletin, a group chat or an email, shown in full so
	 * they can see exactly what they would send, with one tap to copy it, send
	 * it on WhatsApp (how this content travels) or open it in their mail app.
	 * English-only like the page, so the words are literals, not catalogue keys.
	 */
	let { message, subject }: { message: string; subject: string } = $props();

	const links = $derived(inviteLinks(subject, message));
	let copied = $state(false);
	let timer: ReturnType<typeof setTimeout> | undefined;
	$effect(() => () => clearTimeout(timer));

	async function copy() {
		try {
			await navigator.clipboard.writeText(message);
			copied = true;
			clearTimeout(timer);
			timer = setTimeout(() => (copied = false), 2000);
		} catch {
			/* no clipboard (an old browser, a denied permission): the text is on screen to select */
		}
	}
</script>

<figure class="invite rounded-card border border-border bg-surface p-5">
	<!-- The whole message as it will be sent, link included: selectable by hand
	     where the copy button can't reach the clipboard. -->
	<blockquote class="message text-body">{message}</blockquote>
	<figcaption class="mt-4 flex flex-wrap gap-2">
		<button type="button" class="btn btn-sm" onclick={copy} aria-live="polite">
			<Icon name={copied ? 'check' : 'page'} size={15} />
			{copied ? 'Copied' : 'Copy the message'}
		</button>
		<a class="btn btn-sm" href={links.whatsapp} target="_blank" rel="noopener noreferrer">
			<Icon name="share" size={15} /> WhatsApp
		</a>
		<a class="btn btn-sm" href={links.email}><Icon name="mail" size={15} /> Email</a>
	</figcaption>
</figure>

<style>
	.message {
		white-space: pre-line;
		border-inline-start: 3px solid color-mix(in srgb, var(--group, var(--color-accent)) 60%, transparent);
		padding-inline-start: 1rem;
		overflow-wrap: anywhere;
	}
</style>
