<script lang="ts">
	import { planProgress } from '$lib/planProgress.svelte';
	import { i18n } from '$lib/i18n.svelte';

	/** A plan day's "Mark day done" — or, once it is, the quiet ✓ that says so. */
	let { slug, day, oncomplete }: { slug: string; day: number; oncomplete: () => void } = $props();
	const t = i18n.t;
</script>

{#if planProgress.isDone(slug, day)}
	<span class="text-small font-semibold text-accent">✓ {t('plans.dayDone')}</span>
{:else}
	<button class="btn btn-sm btn-primary" onclick={oncomplete}>{t('plans.markDone')}</button>
{/if}
