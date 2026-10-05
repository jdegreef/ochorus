<script lang="ts">
	import type { Snippet } from 'svelte';
	import AccountGate from '$lib/components/AccountGate.svelte';

	let { children }: { children: Snippet } = $props();
</script>

<!-- The notebook, its Today view and its print sheet are signed-in only. -->
<AccountGate>
	{@render children()}
</AccountGate>
