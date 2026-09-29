<script lang="ts">
	import type { Pager } from '$lib/paging.svelte';
	import { i18n } from '$lib/i18n.svelte';

	/** The "Show N more" button under a paged shelf; nothing once all are shown. */
	let { pager }: { pager: Pager } = $props();
	const t = i18n.t;
</script>

{#if pager.remaining > 0}
	<div class="mt-8 flex justify-center">
		<button type="button" class="btn btn-ghost" onclick={pager.more}>
			{t('bios.showMore').replace('%n%', String(pager.next))}
		</button>
	</div>
{/if}
