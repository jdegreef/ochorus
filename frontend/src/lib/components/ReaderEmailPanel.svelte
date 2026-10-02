<script lang="ts">
	/**
	 * One reader's email on their admin page: everything we've sent them (with
	 * what happened to it), and a form to write to them directly. Super-admin
	 * only — the backend gates it with IsAdminEmail, like the Emails section.
	 */
	import { ApiError, apiErrorDetail } from '$lib/api';
	import {
		formatDateTime,
		getReaderEmails,
		sendDirectEmail,
		type ReaderEmailRow,
		type ReaderEmails
	} from '$lib/library-admin';

	let { uid, name }: { uid: string; name: string } = $props();

	let emails = $state<ReaderEmails | null>(null);
	let loadError = $state('');
	let composing = $state(false);
	let subject = $state('');
	let heading = $state('');
	let body = $state('');
	let ctaLabel = $state('');
	let ctaPath = $state('');
	let busy = $state(false);
	let error = $state('');
	let notice = $state('');
	let expanded = $state<number | null>(null);

	async function load() {
		loadError = '';
		try {
			emails = await getReaderEmails(uid);
		} catch {
			loadError = "Couldn't load this reader's email.";
		}
	}

	$effect(() => {
		void uid;
		load();
	});

	async function send() {
		if (!confirm(`Send this email to ${name}?`)) return;
		busy = true;
		error = '';
		notice = '';
		try {
			emails = await sendDirectEmail(uid, {
				subject,
				heading,
				// Blank lines separate paragraphs; single line breaks stay in one.
				paragraphs: body.split(/\n\s*\n/).map((p) => p.trim()).filter(Boolean),
				cta_label: ctaLabel,
				cta_path: ctaPath
			});
			notice = 'Sent.';
			subject = heading = body = ctaLabel = ctaPath = '';
			composing = false;
		} catch (e) {
			error = apiErrorDetail(e);
			// A 409 was recorded but not delivered; its body carries the fresh history.
			if (e instanceof ApiError && e.status === 409) emails = e.body as ReaderEmails;
		} finally {
			busy = false;
		}
	}

	/** The furthest thing that happened to a message, for one compact label. */
	function outcome(m: ReaderEmailRow): { text: string; tone: string } {
		if (m.status === 'failed') return { text: 'failed', tone: 'text-danger' };
		if (m.status === 'skipped') return { text: 'not sent', tone: 'text-muted' };
		if (m.status === 'queued') return { text: 'queued', tone: 'text-muted' };
		for (const [ev, tone] of [
			['complained', 'text-danger'],
			['bounced', 'text-danger'],
			['clicked', 'text-accent'],
			['opened', 'text-text'],
			['delivered', 'text-muted']
		] as const) {
			if (m.events.includes(ev)) return { text: ev, tone };
		}
		return { text: 'sent', tone: 'text-muted' };
	}
</script>

<section class="mb-8 rounded-card border border-border bg-surface p-5">
	<div class="mb-3 flex flex-wrap items-baseline justify-between gap-2">
		<h2 class="text-h3">Email</h2>
		{#if emails && !emails.blocked_reason && !composing}
			<button class="btn btn-primary btn-sm" onclick={() => (composing = true)}>Email this reader</button>
		{/if}
	</div>

	{#if loadError}
		<p class="text-body text-danger">{loadError}</p>
	{:else if !emails}
		<p class="text-body text-muted">Loading…</p>
	{:else}
		{#if emails.blocked_reason}
			<p class="mb-3 rounded-md bg-surface-2 p-3 text-small text-muted">{emails.blocked_reason} You can't write to them from here.</p>
		{/if}
		{#if notice}<p class="mb-3 text-small text-accent" role="status">{notice}</p>{/if}

		{#if composing}
			<form class="mb-5 space-y-3 rounded-md border border-border p-4" onsubmit={(e) => { e.preventDefault(); send(); }}>
				<p class="text-small text-muted">
					It goes out in the reader's email language, in the standard Ochorus email layout, with the usual unsubscribe footer.
				</p>
				<label class="block">
					<span class="mb-1 block text-micro text-muted">Subject line</span>
					<input class="w-full rounded-md border border-border bg-surface p-2 text-body" bind:value={subject} maxlength="300" required />
				</label>
				<label class="block">
					<span class="mb-1 block text-micro text-muted">Heading (optional)</span>
					<input class="w-full rounded-md border border-border bg-surface p-2 text-body" bind:value={heading} />
				</label>
				<label class="block">
					<span class="mb-1 block text-micro text-muted">Message — leave a blank line between paragraphs</span>
					<textarea class="h-40 w-full rounded-md border border-border bg-surface p-2 text-body" bind:value={body} required></textarea>
				</label>
				<div class="grid grid-cols-1 gap-3 sm:grid-cols-2">
					<label class="block">
						<span class="mb-1 block text-micro text-muted">Button label (optional)</span>
						<input class="w-full rounded-md border border-border bg-surface p-2 text-small" bind:value={ctaLabel} />
					</label>
					<label class="block">
						<span class="mb-1 block text-micro text-muted">Button link path (e.g. books/humility-2)</span>
						<input class="w-full rounded-md border border-border bg-surface p-2 text-small" bind:value={ctaPath} />
					</label>
				</div>
				{#if error}<p class="text-small text-danger" role="alert">{error}</p>{/if}
				<div class="flex gap-2">
					<button type="submit" class="btn btn-primary btn-sm" disabled={busy || !subject.trim() || !body.trim()}>{busy ? 'Sending…' : 'Send'}</button>
					<button type="button" class="btn btn-ghost btn-sm" onclick={() => { composing = false; error = ''; }} disabled={busy}>Cancel</button>
				</div>
			</form>
		{/if}

		{#if emails.messages.length}
			<ul class="divide-y divide-border/60">
				{#each emails.messages as m (m.id)}
					{@const o = outcome(m)}
					<li class="py-2.5">
						<div class="flex items-baseline justify-between gap-3">
							<span class="min-w-0 truncate text-body text-text">
								<span class="text-muted">{m.label} ·</span> {m.subject || '(no subject)'}
							</span>
							<span class="shrink-0 whitespace-nowrap text-small tabular-nums">
								<span class={o.tone}>{o.text}</span>
								<span class="text-muted"> · {formatDateTime(m.sent_at ?? m.created_at)}</span>
							</span>
						</div>
						{#if m.kind === 'direct'}
							<button class="mt-0.5 text-micro text-muted hover:text-text" onclick={() => (expanded = expanded === m.id ? null : m.id)}>
								{expanded === m.id ? 'Hide message' : 'Show message'}{m.sent_by ? ` · from ${m.sent_by}` : ''}
							</button>
							{#if expanded === m.id}
								<p class="mt-1 whitespace-pre-line rounded-md bg-surface-2 p-3 text-small text-text">{m.body_text}</p>
							{/if}
						{/if}
						{#if m.error}<p class="text-micro text-muted">{m.error}</p>{/if}
					</li>
				{/each}
			</ul>
		{:else}
			<p class="text-body text-muted">No email sent to this reader yet.</p>
		{/if}
	{/if}
</section>
