<script lang="ts">
	/**
	 * A live preview of one language of a campaign, rendered by the server's own
	 * email template (so it is the email, not an imitation). Follows the unsaved
	 * editor state, debounced. The HTML is shown in a fully sandboxed iframe — no
	 * scripts, no same-origin access — though it is server-escaped text anyway.
	 */
	import { apiErrorDetail } from '$lib/api';
	import { previewEmail, type BroadcastBlock, type PreviewReader } from '$lib/library-admin';

	let { locale, subject, content }: { locale: string; subject: string; content: BroadcastBlock } =
		$props();

	let html = $state('');
	let error = $state('');
	let width = $state<'desktop' | 'mobile'>('desktop');
	let reader = $state<PreviewReader>('me');
	let renderedSubject = $state('');
	const READERS: { key: PreviewReader; label: string }[] = [
		{ key: 'me', label: 'Me' },
		{ key: 'sample', label: 'A reader with everything' },
		{ key: 'new', label: 'A new reader' }
	];

	$effect(() => {
		// A deep snapshot reads every field, so any edit re-renders the preview.
		const snap = $state.snapshot({ locale, subject, content, reader });
		const controller = new AbortController();
		const timer = setTimeout(async () => {
			try {
				const rendered = await previewEmail(snap.locale, snap.subject, snap.content, controller.signal, snap.reader);
				html = rendered.html;
				renderedSubject = rendered.subject;
				error = '';
			} catch (e) {
				if (!controller.signal.aborted) error = apiErrorDetail(e, "Couldn't render the preview.");
			}
		}, 400);
		// A newer edit supersedes this one: never let a slow, older render land last.
		return () => {
			clearTimeout(timer);
			controller.abort();
		};
	});
</script>

<div>
	<div class="mb-2 flex items-center justify-between gap-2">
		<span class="text-micro text-muted">Preview · {locale} · as you'd receive it</span>
		<div role="group" aria-label="Preview width" class="flex gap-1">
			<button class="rounded-full border px-2 py-0.5 text-micro {width === 'desktop' ? 'border-accent bg-accent-soft text-accent' : 'border-border text-muted'}" aria-pressed={width === 'desktop'} onclick={() => (width = 'desktop')}>Desktop</button>
			<button class="rounded-full border px-2 py-0.5 text-micro {width === 'mobile' ? 'border-accent bg-accent-soft text-accent' : 'border-border text-muted'}" aria-pressed={width === 'mobile'} onclick={() => (width = 'mobile')}>Mobile</button>
		</div>
	</div>
	<div class="mb-2 flex flex-wrap items-center gap-1" role="group" aria-label="Preview as">
		<span class="text-micro text-muted">As</span>
		{#each READERS as r (r.key)}
			<button class="rounded-full border px-2 py-0.5 text-micro {reader === r.key ? 'border-accent bg-accent-soft text-accent' : 'border-border text-muted'}" aria-pressed={reader === r.key} onclick={() => (reader = r.key)}>{r.label}</button>
		{/each}
	</div>
	{#if renderedSubject && renderedSubject !== subject}
		<p class="mb-2 text-micro text-muted">Subject: <span class="text-text">{renderedSubject}</span></p>
	{/if}
	{#if error}<p class="mb-2 text-small text-danger">{error}</p>{/if}
	<div class="flex justify-center rounded-card border border-border bg-surface-2 p-2">
		<iframe
			title="Email preview"
			sandbox=""
			srcdoc={html}
			class="h-[640px] rounded-md bg-white"
			style="width: {width === 'mobile' ? '375px' : '100%'}"
		></iframe>
	</div>
</div>
