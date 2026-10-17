<script lang="ts">
	/**
	 * A small picture of an email: the server's own render of it (the same
	 * preview the designer shows), drawn at 600px and scaled to fit the card.
	 * Rendered once, when it first scrolls into view, in a fully sandboxed
	 * iframe that can't be clicked into.
	 */
	import { previewEmail, type BroadcastBlock } from '$lib/library-admin';
	import { thumbnailCache } from './emailThumbnailCache';

	let {
		locale,
		subject,
		content,
		height = 220
	}: { locale: string; subject: string; content: BroadcastBlock; height?: number } = $props();

	let box = $state<HTMLDivElement>();
	let width = $state(0);
	let html = $state('');
	let failed = $state(false);
	const scale = $derived(width ? width / 600 : 0.4);

	$effect(() => {
		if (!box) return;
		const target = box;
		const controller = new AbortController();
		const observer = new IntersectionObserver((entries) => {
			if (!entries.some((e) => e.isIntersecting)) return;
			observer.disconnect();
			const snap = $state.snapshot(content);
			const key = JSON.stringify([locale, subject, snap]);
			const cached = thumbnailCache.get(key);
			if (cached) {
				html = cached;
				return;
			}
			previewEmail(locale, subject, snap, controller.signal)
				.then((r) => {
					thumbnailCache.set(key, r.html);
					html = r.html;
				})
				.catch(() => {
					if (!controller.signal.aborted) failed = true;
				});
		});
		observer.observe(target);
		return () => {
			observer.disconnect();
			controller.abort();
		};
	});
</script>

<div
	bind:this={box}
	bind:clientWidth={width}
	class="relative overflow-hidden bg-surface-2"
	style="height: {height}px"
	aria-hidden="true"
>
	{#if html}
		<iframe
			title="Email thumbnail"
			sandbox=""
			srcdoc={html}
			tabindex="-1"
			class="pointer-events-none absolute left-0 top-0 origin-top-left border-0 bg-white"
			style="width: 600px; height: {Math.ceil(height / scale)}px; transform: scale({scale})"
		></iframe>
	{:else}
		<div class="flex h-full items-center justify-center text-micro text-muted">{failed ? 'No preview' : 'Rendering…'}</div>
	{/if}
</div>
