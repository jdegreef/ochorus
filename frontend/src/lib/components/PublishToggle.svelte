<script lang="ts">
	// A controlled publish/unpublish control for one edition of a work (book or
	// sermon). The parent owns the authoritative `published` state and passes an
	// `onToggle` that performs the write and resolves with the server's new value;
	// this component owns only the transient UI (a confirm step on the removing
	// direction, a pending flag, an error line). Data flows down, the action up —
	// no child→parent mutation.
	interface Props {
		published: boolean;
		onToggle: (next: boolean) => Promise<unknown>;
	}
	let { published, onToggle }: Props = $props();

	let pending = $state(false);
	let confirming = $state(false);
	let error = $state('');

	async function run(next: boolean) {
		confirming = false;
		pending = true;
		error = '';
		try {
			await onToggle(next);
		} catch (e) {
			error = e instanceof Error ? e.message : 'Could not update.';
		} finally {
			pending = false;
		}
	}
</script>

<div class="flex flex-col items-end gap-1.5">
	{#if confirming}
		<span class="flex items-center gap-2">
			<span class="text-warning">Hide from the site?</span>
			<button type="button" onclick={() => run(false)} class="rounded-full border border-warning px-2.5 py-0.5 text-warning hover:bg-warning/10">Unpublish</button>
			<button type="button" onclick={() => { confirming = false; error = ''; }} class="text-muted hover:text-text">Cancel</button>
		</span>
	{:else if published}
		<button type="button" disabled={pending} onclick={() => (confirming = true)} class="rounded-full border border-border px-2.5 py-0.5 text-muted hover:border-warning hover:text-warning disabled:opacity-50">{pending ? 'Working…' : 'Unpublish'}</button>
	{:else}
		<button type="button" disabled={pending} onclick={() => run(true)} class="rounded-full border border-accent px-2.5 py-0.5 text-accent hover:bg-accent/10 disabled:opacity-50">{pending ? 'Working…' : 'Publish'}</button>
	{/if}
	{#if error}<span class="max-w-[16rem] text-end text-micro text-warning">{error}</span>{/if}
</div>
