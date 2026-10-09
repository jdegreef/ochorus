<script lang="ts">
	import { adminResource } from '$lib/adminResource.svelte';
	import AdminGate from '$lib/components/AdminGate.svelte';
	import EmailBlocksEditor from '$lib/components/EmailBlocksEditor.svelte';
	import EmailPreview from '$lib/components/EmailPreview.svelte';
	import { ApiError, apiErrorDetail } from '$lib/api';
	import { localeName } from '$lib/lang.svelte';
	import { locales } from '$lib/paraglide/runtime';
	import {
		listBroadcasts,
		getBroadcast,
		createBroadcast,
		updateBroadcast,
		deleteBroadcast,
		broadcastAction,
		previewAudience,
		listEmailTemplates,
		saveEmailTemplate,
		broadcastTranslation,
		deleteEmailTemplate,
		type EmailTemplate,
		type AdminBroadcast,
		type BroadcastActionName,
		type BroadcastAudience,
		type BroadcastCheck,
		type BroadcastBlock,
		type BroadcastStatus
	} from '$lib/library-admin';

	// The languages a broadcast can be composed in: every UI locale, named as the
	// language picker names it. Derived, so a new locale reaches the composer
	// without an edit here — this was a hand-kept third copy of the list.
	const LOCALES: { code: string; label: string }[] = locales.map((code) => ({
		code,
		label: localeName(code)
	}));
	const localeLabel = (code: string) =>
		LOCALES.find((l) => l.code === code)?.label ?? code;

	type Draft = {
		id: number;
		name: string;
		status: BroadcastStatus;
		from_address: string;
		audience: BroadcastAudience;
		subject: Record<string, string>;
		content: Record<string, BroadcastBlock>;
		scheduled_at: string | null;
		// Server-computed, read-only here: the pre-send checklist and send progress.
		checks: BroadcastCheck[];
		progress: AdminBroadcast['progress'];
		status_reason: string;
		audience_count: number;
		locked: boolean;
		translations: NonNullable<AdminBroadcast['translations']>;
	};

	const list = adminResource(listBroadcasts, 'Something went wrong loading broadcasts.');

	let mode = $state<'list' | 'edit'>('list');
	let draft = $state<Draft | null>(null);
	let editLocale = $state('en');
	let audienceCount = $state<number | null>(null);
	let busy = $state(false);
	let notice = $state('');
	let error = $state('');
	let scheduleAt = $state('');

	// Once a send has started (even paused), the copy and audience are frozen;
	// the server says so (`locked`) rather than this page re-deriving the rules.
	const readOnly = $derived(!!draft?.locked);
	const inFlight = $derived(draft?.status === 'sending' || draft?.status === 'paused');
	const processed = $derived(
		draft ? draft.progress.sent + draft.progress.skipped + draft.progress.failed : 0
	);
	const showProgress = $derived(
		inFlight || processed > 0
	);
	const draftLocales = $derived(draft ? Object.keys(draft.content) : []);

	function toDraft(b: AdminBroadcast): Draft {
		return {
			id: b.id,
			name: b.name,
			status: b.status,
			from_address: b.from_address ?? '',
			audience: { ...b.audience },
			subject: { ...b.subject },
			content: structuredClone(b.content ?? {}),
			scheduled_at: b.scheduled_at,
			checks: b.checks ?? [],
			progress: b.progress,
			status_reason: b.status_reason,
			audience_count: b.audience_count,
			locked: b.locked,
			translations: b.translations ?? {}
		};
	}

	async function openEditor(id: number) {
		error = '';
		notice = '';
		try {
			const b = await getBroadcast(id);
			draft = toDraft(b);
			const locales = Object.keys(draft.content);
			editLocale = locales.includes(editLocale) ? editLocale : (locales[0] ?? 'en');
			await refreshCount();
			mode = 'edit';
		} catch (e) {
			error = apiErrorDetail(e);
		}
	}

	async function newBroadcast(template?: EmailTemplate) {
		error = '';
		try {
			const b = await createBroadcast({
				name: template ? template.name : 'Untitled broadcast',
				subject: template?.subject ?? { en: '' },
				content: template?.content ?? { en: { preheader: '', blocks: [] } },
				audience: {}
			});
			await list.load();
			await openEditor(b.id);
		} catch (e) {
			error = apiErrorDetail(e);
		}
	}

	// --- Templates ------------------------------------------------------------
	const templates = adminResource(listEmailTemplates, "Couldn't load templates.");

	async function saveAsTemplate() {
		if (!draft) return;
		const name = prompt('Name this template', draft.name)?.trim();
		if (!name) return;
		busy = true;
		error = '';
		try {
			if (!readOnly) await persist();
			await saveEmailTemplate({ name, from_broadcast: draft.id });
			await templates.load();
			notice = `Saved as the template “${name}”.`;
		} catch (e) {
			error = apiErrorDetail(e);
		} finally {
			busy = false;
		}
	}

	async function removeTemplate(t: EmailTemplate) {
		if (!confirm(`Delete the template “${t.name}”? Broadcasts made from it are unaffected.`)) return;
		try {
			await deleteEmailTemplate(t.id);
			await templates.load();
		} catch (e) {
			error = apiErrorDetail(e);
		}
	}

	async function persist() {
		if (!draft) return;
		const b = await updateBroadcast(draft.id, {
			name: draft.name,
			subject: draft.subject,
			content: draft.content,
			audience: draft.audience,
			from_address: draft.from_address
		});
		draft = toDraft(b);
	}

	async function save() {
		busy = true;
		error = '';
		notice = '';
		try {
			await persist();
			await list.load();
			notice = 'Saved.';
		} catch (e) {
			error = apiErrorDetail(e);
		} finally {
			busy = false;
		}
	}

	async function refreshCount() {
		if (!draft) return;
		try {
			const r = await previewAudience(draft.audience);
			audienceCount = r.count;
		} catch {
			audienceCount = null;
		}
	}

	const CONFIRM: Partial<Record<BroadcastActionName, string>> = {
		send: 'Send this broadcast to its whole audience? It goes out in batches, starting on the next email run.',
		cancel: 'Cancel this broadcast? Anyone already emailed stays emailed; nobody else will get it.'
	};

	async function act(action: BroadcastActionName, extra: { override_guardrail?: boolean } = {}) {
		if (!draft) return;
		if (CONFIRM[action] && !confirm(CONFIRM[action])) return;
		busy = true;
		error = '';
		notice = '';
		try {
			if (!readOnly) await persist(); // persist edits first (a started send is frozen)
			const body =
				action === 'schedule' && scheduleAt
					? { scheduled_at: new Date(scheduleAt).toISOString() }
					: extra;
			const res = await broadcastAction(draft.id, action, body);
			draft = toDraft(res);
			notice =
				action === 'test'
					? `Test sent to ${res.sent_to ?? 'your address'}.`
					: {
							send: 'Queued. It sends in batches, starting on the next email run (every 15 minutes); progress shows below.',
					schedule: 'Scheduled.',
					cancel: 'Canceled.',
					pause: 'Paused. Nobody else is emailed until you resume.',
							resume: 'Resumed. Sending continues on the next email run.'
						}[action];
			await list.load();
		} catch (e) {
			const body = e instanceof ApiError ? (e.body as { checks?: BroadcastCheck[]; needs_override?: boolean }) : undefined;
			if (body?.checks && draft) draft.checks = body.checks;
			if (action === 'resume' && body?.needs_override) {
				busy = false; // not left spinning behind the native dialog
				if (confirm(`${apiErrorDetail(e)}\n\nResume anyway?`)) await act('resume', { override_guardrail: true });
				return;
			}
			error = apiErrorDetail(e);
		} finally {
			busy = false;
		}
	}

	// While a send is running, refresh its progress (and catch a guardrail pause).
	// Progress only moves at batch checkpoints, so every 30 s is plenty, and a
	// hidden tab doesn't poll.
	$effect(() => {
		if (mode !== 'edit' || draft?.status !== 'sending') return;
		const id = draft.id;
		const timer = setInterval(async () => {
			if (document.hidden) return;
			try {
				const b = await getBroadcast(id);
				if (draft?.id === id) draft = toDraft(b);
			} catch {
				/* keep the last known state; the next tick retries */
			}
		}, 30000);
		return () => clearInterval(timer);
	});

	async function removeBroadcast() {
		if (!draft) return;
		if (!confirm('Delete this draft? This cannot be undone.')) return;
		busy = true;
		try {
			await deleteBroadcast(draft.id);
			await list.load();
			mode = 'list';
			draft = null;
		} catch (e) {
			error = apiErrorDetail(e);
		} finally {
			busy = false;
		}
	}

	/** Add a language, starting from a copy of the one on screen: the layout and
	 *  library blocks carry over (each renders that language's own edition), and
	 *  only the words need translating. */
	function addLocale(code: string) {
		if (!draft || draft.content[code]) return;
		draft.subject[code] = '';
		draft.content[code] = $state.snapshot(draft.content[editLocale]) ?? { preheader: '', blocks: [] };
		editLocale = code;
	}

	// --- AI-drafted translations (a job for a worker session; see the backend's
	// emails/translation_jobs.py). A draft blocks sending until approved here.
	const translationOf = (code: string) => draft?.translations[code];
	const pendingLocales = $derived(
		Object.entries(draft?.translations ?? {})
			.filter(([, t]) => t.state === 'requested')
			.map(([code]) => code)
	);

	async function translation(action: 'request' | 'fetch' | 'approve', code: string) {
		if (!draft) return;
		if (action === 'request' && !confirm(`Ask for ${translationOf(code)?.state === 'requested' ? 'a new' : 'an'} AI draft in ${localeLabel(code)}? It goes to the translation queue (replacing any open request); check back once a worker has run.`)) return;
		busy = true;
		error = '';
		notice = '';
		try {
			// Save first: a request is made from what is saved, and the reply
			// replaces this page's copy (unsaved edits would be lost).
			if (!readOnly) await persist();
			const source = editLocale in draft.content && !translationOf(editLocale) ? editLocale : 'en';
			const b = await broadcastTranslation(draft.id, action, code, action === 'request' ? source : undefined);
			draft = toDraft(b);
			const state = draft.translations[code]?.state;
			notice = {
				request: `${localeLabel(code)} draft requested — it's in the translation queue.`,
				fetch: state === 'draft' ? `${localeLabel(code)} draft is in. Read it, edit it if you like, then approve it.` : `${localeLabel(code)} isn't back yet.`,
				approve: `${localeLabel(code)} approved.`
			}[action];
			if (action === 'fetch' && state === 'draft') editLocale = code;
		} catch (e) {
			error = apiErrorDetail(e);
		} finally {
			busy = false;
		}
	}

	function switchLocale(code: string) {
		editLocale = code;
	}

	// How each pre-send check level reads in the checklist.
	const LEVEL: Record<BroadcastCheck['level'], { cls: string; label: string; glyph: string }> = {
		error: { cls: 'bg-danger/15 text-danger', label: 'Must fix', glyph: '!' },
		warning: { cls: 'bg-warning/15 text-warning', label: 'Warning', glyph: '?' },
		ok: { cls: 'bg-accent-soft text-accent', label: 'OK', glyph: '✓' }
	};

	// A language waiting on an AI draft is added by its draft, not by hand.
	const availableToAdd = $derived(LOCALES.filter((l) => !draft?.content[l.code] && !pendingLocales.includes(l.code)));
	const statusTone: Record<BroadcastStatus, string> = {
		draft: 'bg-surface-2 text-muted',
		scheduled: 'bg-accent-soft text-accent',
		sending: 'bg-accent-soft text-accent',
		paused: 'bg-warning/15 text-warning',
		sent: 'bg-surface-2 text-text',
		canceled: 'bg-surface-2 text-muted'
	};
</script>

<svelte:head><title>Admin · Compose email — Ochorus</title><meta name="robots" content="noindex" /></svelte:head>

<div class="mx-auto max-w-6xl px-5 py-10">
	<header class="mb-6">
		<p class="eyebrow mb-2 text-accent">Admin</p>
		<h1 class="text-h1">Compose email</h1>
		<p class="mt-2 max-w-prose text-body text-muted">
			Write and send a broadcast to a segment of readers. Opted-out and suppressed readers are always excluded automatically.
		</p>
	</header>

	{#if error}
		<div class="mb-4 rounded-card border border-danger/40 bg-danger/10 p-3 text-small text-danger">{error}</div>
	{/if}
	{#if notice}
		<div class="mb-4 rounded-card border border-border bg-surface-2 p-3 text-small text-text">{notice}</div>
	{/if}

	{#if mode === 'list'}
		<AdminGate resource={list} errorTitle="Couldn't load broadcasts">
			{#snippet children(d)}
				<div class="mb-4 flex justify-end">
					<button class="btn btn-primary btn-sm" onclick={() => newBroadcast()}>New broadcast</button>
				</div>
				{#if templates.data?.templates.length}
					<section class="mb-5 rounded-card border border-border bg-surface p-4">
						<h2 class="mb-2 text-h3">Start from a template</h2>
						<ul class="divide-y divide-border/60">
							{#each templates.data.templates as t (t.id)}
								<li class="flex flex-wrap items-center justify-between gap-2 py-2">
									<span class="text-small text-text">
										<span class="font-semibold">{t.name}</span>
										<span class="text-muted"> · {t.locales.join(', ') || 'empty'}</span>
									</span>
									<span class="flex gap-1">
										<button class="btn btn-ghost btn-sm" onclick={() => newBroadcast(t)}>Use</button>
										<button class="btn btn-ghost btn-sm text-danger" onclick={() => removeTemplate(t)}>Delete</button>
									</span>
								</li>
							{/each}
						</ul>
					</section>
				{/if}
				{#if d.broadcasts.length === 0}
					<div class="rounded-card border border-border bg-surface p-8 text-center">
						<p class="text-h3">No broadcasts yet</p>
						<p class="mt-1 text-body text-muted">Create one to send an update or showcase to readers.</p>
					</div>
				{:else}
					<div class="overflow-x-auto rounded-card border border-border bg-surface">
						<table class="w-full text-small">
							<thead>
								<tr class="border-b border-border text-left text-muted">
									<th class="p-3 font-semibold">Name</th>
									<th class="p-3 font-semibold">Status</th>
									<th class="p-3 font-semibold">Languages</th>
									<th class="p-3 text-right font-semibold">Audience</th>
									<th class="p-3"></th>
								</tr>
							</thead>
							<tbody>
								{#each d.broadcasts as b (b.id)}
									<tr class="border-b border-border/50">
										<td class="p-3 font-medium text-text">{b.name}</td>
										<td class="p-3"><span class="rounded-full px-2 py-0.5 text-micro {statusTone[b.status]}">{b.status}</span></td>
										<td class="p-3 text-muted">{b.locales.join(', ') || '—'}</td>
										<td class="p-3 text-right tabular-nums">{b.audience_count}</td>
										<td class="p-3 text-right"><button class="btn btn-ghost btn-sm" onclick={() => openEditor(b.id)}>Open</button></td>
									</tr>
								{/each}
							</tbody>
						</table>
					</div>
				{/if}
			{/snippet}
		</AdminGate>
	{:else if draft}
		<div class="mb-4 flex items-center justify-between">
			<button class="btn btn-ghost btn-sm" onclick={() => { mode = 'list'; draft = null; }}>← All broadcasts</button>
			<span class="rounded-full px-2 py-0.5 text-micro {statusTone[draft.status]}">{draft.status}</span>
		</div>

		{#if readOnly}
			<p class="mb-4 text-small text-muted">
				{inFlight
					? 'Sending has started, so the email and its audience are locked.'
					: 'This broadcast has been sent and is read-only.'}
			</p>
		{:else if draft.status_reason}
			<p class="mb-4 rounded-md bg-warning/10 p-2 text-small text-warning">{draft.status_reason}</p>
		{/if}

		<!-- Name -->
		<label class="mb-4 block">
			<span class="mb-1 block text-small font-semibold text-text">Name (internal)</span>
			<input class="w-full rounded-md border border-border bg-surface p-2 text-body" bind:value={draft.name} disabled={readOnly} />
		</label>

		<!-- Audience -->
		<section class="mb-5 rounded-card border border-border bg-surface p-4">
			<div class="mb-3 flex items-baseline justify-between">
				<h2 class="text-h3">Audience</h2>
				<span class="text-small text-muted">{audienceCount === null ? '—' : `${audienceCount} readers`}</span>
			</div>
			<div class="grid grid-cols-2 gap-3 sm:grid-cols-4">
				<label class="block">
					<span class="mb-1 block text-micro text-muted">Language</span>
					<select class="w-full rounded-md border border-border bg-surface p-2 text-small" bind:value={draft.audience.locale} onchange={refreshCount} disabled={readOnly}>
						<option value={undefined}>Any</option>
						{#each LOCALES as l (l.code)}<option value={l.code}>{l.label}</option>{/each}
					</select>
				</label>
				<label class="block">
					<span class="mb-1 block text-micro text-muted">Activity</span>
					<select class="w-full rounded-md border border-border bg-surface p-2 text-small" bind:value={draft.audience.activity} onchange={refreshCount} disabled={readOnly}>
						<option value={undefined}>Any</option>
						<option value="active_7d">Active last 7 days</option>
						<option value="active_30d">Active last 30 days</option>
						<option value="lapsed_30d">Lapsed 30+ days</option>
						<option value="never_seen">Never seen</option>
					</select>
				</label>
				<label class="block">
					<span class="mb-1 block text-micro text-muted">Reading plan</span>
					<select class="w-full rounded-md border border-border bg-surface p-2 text-small" value={draft.audience.has_plan === undefined ? '' : String(draft.audience.has_plan)} onchange={(e) => { const v = (e.currentTarget as HTMLSelectElement).value; draft!.audience.has_plan = v === '' ? undefined : v === 'true'; refreshCount(); }} disabled={readOnly}>
						<option value="">Any</option>
						<option value="true">Has a plan</option>
						<option value="false">No plan</option>
					</select>
				</label>
				<label class="block">
					<span class="mb-1 block text-micro text-muted">Sign-up prompt</span>
					<input class="w-full rounded-md border border-border bg-surface p-2 text-small" bind:value={draft.audience.signup_variant} onblur={refreshCount} placeholder="any" disabled={readOnly} />
				</label>
			</div>
		</section>

		<!-- Content per language -->
		<section class="mb-5 rounded-card border border-border bg-surface p-4">
			<div class="mb-3 flex flex-wrap items-center gap-2">
				<h2 class="mr-2 text-h3">Content</h2>
				{#each draftLocales as code (code)}
					<button class="rounded-full border px-2.5 py-0.5 text-micro {code === editLocale ? 'border-accent bg-accent-soft text-accent' : 'border-border text-muted'}" onclick={() => switchLocale(code)}>{localeLabel(code)}</button>
				{/each}
				{#if !readOnly && availableToAdd.length}
					<select class="rounded-md border border-border bg-surface p-1 text-micro" onchange={(e) => { addLocale((e.currentTarget as HTMLSelectElement).value); (e.currentTarget as HTMLSelectElement).value = ''; }}>
						<option value="">+ Add language</option>
						{#each availableToAdd as l (l.code)}<option value={l.code}>{l.label}</option>{/each}
					</select>
					<select class="rounded-md border border-border bg-surface p-1 text-micro" aria-label="Draft a language with AI" disabled={busy} onchange={(e) => { const v = (e.currentTarget as HTMLSelectElement).value; (e.currentTarget as HTMLSelectElement).value = ''; if (v) translation('request', v); }}>
						<option value="">✦ Draft with AI</option>
						{#each availableToAdd.filter((l) => l.code !== 'en' && !translationOf(l.code)) as l (l.code)}<option value={l.code}>{l.label}</option>{/each}
					</select>
				{/if}
			</div>

			{#each pendingLocales as code (code)}
				<div class="mb-2 flex flex-wrap items-center gap-2 rounded-md bg-surface-2 p-2 text-small">
					<span class="text-text">{localeLabel(code)}: AI draft requested</span>
					<a class="text-micro text-accent hover:underline" href={translationOf(code)?.url} target="_blank" rel="noopener">issue #{translationOf(code)?.issue}</a>
					<button class="btn btn-ghost btn-sm" onclick={() => translation('fetch', code)} disabled={busy}>Check for the draft</button>
					<button class="btn btn-ghost btn-sm" onclick={() => translation('request', code)} disabled={busy || readOnly}>Ask again</button>
				</div>
			{/each}

			{#if translationOf(editLocale)?.state === 'draft'}
				<div class="mb-3 flex flex-wrap items-center justify-between gap-2 rounded-md bg-warning/10 p-3 text-small">
					<span class="text-warning">AI draft — read it, edit anything that's off, then approve it. It can't be sent until you do.</span>
					<button class="btn btn-primary btn-sm" onclick={() => translation('approve', editLocale)} disabled={busy}>Approve {localeLabel(editLocale)}</button>
				</div>
			{:else if translationOf(editLocale)?.state === 'approved'}
				<p class="mb-3 text-micro text-muted">AI draft, approved{translationOf(editLocale)?.approved_by ? ` by ${translationOf(editLocale)?.approved_by}` : ''}.</p>
			{/if}
			{#if translationOf(editLocale)?.stale}
				<p class="mb-3 rounded-md bg-warning/10 p-2 text-small text-warning">The {localeLabel(translationOf(editLocale)?.source_locale ?? 'en')} text changed after this translation was drafted.</p>
			{/if}

			{#if draft.content[editLocale]}
				<div class="mb-3 grid grid-cols-1 gap-3 sm:grid-cols-2">
					<label class="block">
						<span class="mb-1 block text-micro text-muted">Subject line</span>
						<input class="w-full rounded-md border border-border bg-surface p-2 text-body" bind:value={draft.subject[editLocale]} disabled={readOnly} />
					</label>
					<label class="block">
						<span class="mb-1 block text-micro text-muted">Inbox preview text (optional)</span>
						<input class="w-full rounded-md border border-border bg-surface p-2 text-body" bind:value={draft.content[editLocale].preheader} disabled={readOnly} placeholder="Shown after the subject in most inboxes" />
					</label>
				</div>
				<div class="grid grid-cols-1 gap-5 lg:grid-cols-2">
					<EmailBlocksEditor bind:blocks={draft.content[editLocale].blocks} locale={editLocale} localeName={localeLabel(editLocale)} disabled={readOnly} />
					<EmailPreview locale={editLocale} subject={draft.subject[editLocale] ?? ''} content={draft.content[editLocale]} />
				</div>
			{/if}
		</section>

		{#if showProgress}
			<!-- Send progress -->
			<section class="mb-5 rounded-card border border-border bg-surface p-4" aria-live="polite">
				<div class="mb-2 flex flex-wrap items-baseline justify-between gap-2">
					<h2 class="text-h3">Sending</h2>
					<span class="text-small text-muted tabular-nums">{processed} of about {draft.audience_count} readers processed</span>
				</div>
				<div class="h-2 overflow-hidden rounded-full bg-surface-2">
					<div class="h-full rounded-full bg-accent" style="width: {Math.min(100, draft.audience_count ? (processed / draft.audience_count) * 100 : 100)}%"></div>
				</div>
				<p class="mt-2 text-small text-muted tabular-nums">
					{draft.progress.sent} sent · {draft.progress.skipped} skipped (opted out or no address) · {draft.progress.failed} failed
				</p>
				{#if draft.status === 'paused' && draft.status_reason}
					<p class="mt-2 rounded-md bg-warning/10 p-2 text-small text-warning">{draft.status_reason}</p>
				{/if}
				{#if inFlight}
					<div class="mt-3 flex flex-wrap gap-2">
						{#if draft.status === 'sending'}
							<button class="btn btn-ghost btn-sm" onclick={() => act('pause')} disabled={busy}>Pause</button>
						{:else}
							<button class="btn btn-primary btn-sm" onclick={() => act('resume')} disabled={busy}>Resume</button>
						{/if}
						<button class="btn btn-ghost btn-sm text-danger" onclick={() => act('cancel')} disabled={busy}>Cancel sending</button>
					</div>
				{/if}
			</section>
		{/if}

		{#if !readOnly && draft.checks.length}
			<!-- Pre-send checks -->
			<section class="mb-5 rounded-card border border-border bg-surface p-4">
				<div class="mb-2 flex items-baseline justify-between gap-2">
					<h2 class="text-h3">Before you send</h2>
					<span class="text-small text-muted">Saved version · save to re-check</span>
				</div>
				<ul class="space-y-1.5">
					{#each draft.checks as c (c.code)}
						<li class="flex gap-2 text-small">
							<span
								class="mt-0.5 inline-flex h-5 w-5 shrink-0 items-center justify-center rounded-full text-micro font-bold {LEVEL[c.level].cls}"
								aria-label={LEVEL[c.level].label}
							>{LEVEL[c.level].glyph}</span>
							<span class={c.level === 'ok' ? 'text-muted' : 'text-text'}>{c.message}</span>
						</li>
					{/each}
				</ul>
			</section>
		{/if}

		<!-- From + actions -->
		<section class="mb-5 rounded-card border border-border bg-surface p-4">
			<label class="mb-4 block">
				<span class="mb-1 block text-micro text-muted">From address (optional — defaults to the site's)</span>
				<input class="w-full rounded-md border border-border bg-surface p-2 text-small" bind:value={draft.from_address} placeholder="Ochorus <hello@news.ochorus.com>" disabled={readOnly} />
			</label>

			{#if !readOnly}
				<div class="flex flex-wrap items-center gap-2">
					<button class="btn btn-primary btn-sm" onclick={save} disabled={busy}>Save</button>
					<button class="btn btn-ghost btn-sm" onclick={() => act('test')} disabled={busy}>Send test to me</button>
					<button class="btn btn-ghost btn-sm" onclick={saveAsTemplate} disabled={busy}>Save as template</button>
					<span class="mx-1 h-5 w-px bg-border"></span>
					<input type="datetime-local" class="rounded-md border border-border bg-surface p-1.5 text-small" bind:value={scheduleAt} />
					<!-- Not disabled on the checks: they describe the last SAVED version, and
					     act() saves first, then the server re-checks and refuses with the list. -->
					<button class="btn btn-ghost btn-sm" onclick={() => act('schedule')} disabled={busy || !scheduleAt}>Schedule</button>
					<button class="btn btn-primary btn-sm" onclick={() => act('send')} disabled={busy}>Send now</button>
					<span class="mx-1 h-5 w-px bg-border"></span>
					{#if draft.status === 'scheduled'}
						<button class="btn btn-ghost btn-sm" onclick={() => act('cancel')} disabled={busy}>Cancel schedule</button>
					{/if}
					<button class="btn btn-ghost btn-sm text-danger" onclick={removeBroadcast} disabled={busy}>Delete</button>
				</div>
			{/if}
		</section>
	{/if}
</div>
