<script lang="ts">
	// Test fixture: renders WorkCard's exported placeholder the way
	// ContinueReading does, so WorkCard.test.ts can compare it with a real card.
	import { placeholder } from '$lib/components/WorkCard.svelte';

	let { kind }: { kind: 'book' | 'sermon' } = $props();
</script>

{@render placeholder(kind)}
