<script lang="ts">
	import '../app.css';
	import { onMount } from 'svelte';
	import { theme } from '$lib/theme.svelte';

	let { children } = $props();

	onMount(() => theme.init());
</script>

<div class="min-h-screen flex flex-col">
	<header class="border-b border-border">
		<div class="mx-auto flex max-w-3xl items-center justify-between px-5 py-4">
			<a href="/" class="text-display !text-2xl tracking-tight !text-text hover:no-underline">
				Ochorus
			</a>
			<button
				class="btn btn-ghost !px-3 !py-1.5 text-small"
				onclick={() => theme.toggle()}
				aria-label="Toggle light and dark theme"
			>
				{theme.current === 'dark' ? '☾ Lamplight' : '☀ Paper'}
			</button>
		</div>
	</header>

	<main class="flex-1">
		{@render children()}
	</main>

	<footer class="border-t border-border">
		<div class="mx-auto max-w-3xl px-5 py-6 text-small text-muted">
			Ochorus · public-domain Christian classics · free forever
		</div>
	</footer>
</div>
