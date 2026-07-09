<script lang="ts">
	import { page } from '$app/stores';

	const status = $derived($page.status);
	const isNotFound = $derived(status === 404);
	const title = $derived(isNotFound ? 'Page not found' : 'Something went wrong');
	const message = $derived(
		isNotFound
			? "We couldn't find that page. It may have moved, or the link may be out of date."
			: "We hit a snag loading this page. It's usually temporary — please try again."
	);
</script>

<svelte:head><title>{title} — Ochorus</title></svelte:head>

<div class="mx-auto flex max-w-md flex-col items-center px-5 py-24 text-center">
	<p class="text-display mb-1 text-muted" style="font-size: 3rem; line-height: 1">{status || 500}</p>
	<h1 class="text-h1 mb-3">{title}</h1>
	<p class="mb-7 text-body text-muted">{message}</p>
	<div class="flex flex-wrap items-center justify-center gap-3">
		{#if !isNotFound}
			<button class="btn btn-primary" onclick={() => location.reload()}>Try again</button>
		{/if}
		<a class="btn btn-ghost" href="/">Go to the library</a>
	</div>
</div>
