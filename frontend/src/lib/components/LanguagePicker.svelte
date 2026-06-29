<script lang="ts">
	import { invalidate } from '$app/navigation';
	import { lang } from '$lib/lang.svelte';
	import { i18n } from '$lib/i18n.svelte';

	let open = $state(false);
	let wrap = $state<HTMLDivElement>();

	async function choose(code: string) {
		open = false;
		if (lang.set(code)) {
			i18n.set(code); // UI locale follows content language by default
			await invalidate('app:lang'); // re-run book/chapter loads
		}
	}

	function onWindowClick(e: MouseEvent) {
		if (open && wrap && !wrap.contains(e.target as Node)) open = false;
	}
</script>

<svelte:window onclick={onWindowClick} />

{#if lang.available.length > 1}
	<div class="relative" bind:this={wrap}>
		<button
			class="rounded-md px-2.5 py-1.5 text-small text-muted hover:bg-surface-2"
			onclick={() => (open = !open)}
			aria-haspopup="listbox"
			aria-expanded={open}
			aria-label="Language"
		>
			{lang.currentEntry?.native_name ?? lang.current}
			<span aria-hidden="true">▾</span>
		</button>
		{#if open}
			<ul
				class="absolute right-0 z-30 mt-2 max-h-72 w-44 overflow-auto rounded-card border border-border bg-surface py-1 shadow-lg"
				role="listbox"
			>
				{#each lang.available as l (l.code)}
					<li>
						<button
							class="flex w-full items-center justify-between px-3 py-1.5 text-small hover:bg-surface-2"
							class:text-accent={l.code === lang.current}
							class:text-text={l.code !== lang.current}
							role="option"
							aria-selected={l.code === lang.current}
							onclick={() => choose(l.code)}
						>
							<span>{l.native_name}</span>
							<span class="text-muted">{l.name}</span>
						</button>
					</li>
				{/each}
			</ul>
		{/if}
	</div>
{/if}
