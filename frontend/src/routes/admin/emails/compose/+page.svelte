<script lang="ts">
	import { adminResource } from '$lib/adminResource.svelte';
	import AdminGate from '$lib/components/AdminGate.svelte';
	import { ApiError } from '$lib/api';
	import {
		listBroadcasts,
		getBroadcast,
		createBroadcast,
		updateBroadcast,
		deleteBroadcast,
		broadcastAction,
		previewAudience,
		type AdminBroadcast,
		type BroadcastAudience,
		type BroadcastBlock,
		type BroadcastStatus
	} from '$lib/library-admin';

	// The languages a broadcast can be composed in. Extend when a locale is added.
	const LOCALES: { code: string; label: string }[] = [
		{ code: 'en', label: 'English' },
		{ code: 'es', label: 'Español' },
		{ code: 'pt', label: 'Português' },
		{ code: 'fr', label: 'Français' },
		{ code: 'sw', label: 'Kiswahili' },
		{ code: 'lg', label: 'Luganda' },
		{ code: 'ar', label: 'العربية' },
		{ code: 'hi', label: 'हिन्दी' },
		{ code: 'uk', label: 'Українська' },
		{ code: 'am', label: 'አማርኛ' }
	];
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
	};

	const list = adminResource(listBroadcasts, 'Something went wrong loading broadcasts.');

	let mode = $state<'list' | 'edit'>('list');
	let draft = $state<Draft | null>(null);
	let editLocale = $state('en');
	let paragraphsText = $state(''); // the selected locale's paragraphs, one per line
	let audienceCount = $state<number | null>(null);
	let busy = $state(false);
	let notice = $state('');
	let error = $state('');
	let scheduleAt = $state('');

	const readOnly = $derived(draft?.status === 'sending' || draft?.status === 'sent');
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
			scheduled_at: b.scheduled_at
		};
	}

	function loadLocaleFields() {
		if (!draft) return;
		const block = draft.content[editLocale] ?? {};
		paragraphsText = (block.paragraphs ?? []).join('\n');
	}

	async function openEditor(id: number) {
		error = '';
		notice = '';
		try {
			const b = await getBroadcast(id);
			draft = toDraft(b);
			const locales = Object.keys(draft.content);
			editLocale = locales.includes(editLocale) ? editLocale : (locales[0] ?? 'en');
			loadLocaleFields();
			await refreshCount();
			mode = 'edit';
		} catch (e) {
			error = message(e);
		}
	}

	async function newBroadcast() {
		error = '';
		try {
			const b = await createBroadcast({
				name: 'Untitled broadcast',
				subject: { en: '' },
				content: { en: {} },
				audience: {}
			});
			await list.load();
			await openEditor(b.id);
		} catch (e) {
			error = message(e);
		}
	}

	function syncParagraphs() {
		if (!draft) return;
		const block = draft.content[editLocale] ?? {};
		block.paragraphs = paragraphsText
			.split('\n')
			.map((p) => p.trim())
			.filter(Boolean);
		draft.content[editLocale] = block;
	}

	async function persist() {
		if (!draft) return;
		syncParagraphs();
		const b = await updateBroadcast(draft.id, {
			name: draft.name,
			subject: draft.subject,
			content: draft.content,
			audience: draft.audience,
			from_address: draft.from_address
		});
		draft = toDraft(b);
		loadLocaleFields();
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
			error = message(e);
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

	async function act(action: 'send' | 'schedule' | 'cancel' | 'test') {
		if (!draft) return;
		if (action === 'send' && !confirm('Send this broadcast to its whole audience now?')) return;
		busy = true;
		error = '';
		notice = '';
		try {
			await persist(); // persist edits first
			const extra =
				action === 'schedule' && scheduleAt
					? { scheduled_at: new Date(scheduleAt).toISOString() }
					: {};
			const res = await broadcastAction(draft.id, action, extra);
			if (action === 'test') notice = `Test sent to ${res.sent_to ?? 'your address'}.`;
			else if (action === 'send') notice = `Sent. ${JSON.stringify(res.tally ?? {})}`;
			else notice = 'Done.';
			if (res.status) draft = toDraft(res as AdminBroadcast);
			await list.load();
		} catch (e) {
			error = message(e);
		} finally {
			busy = false;
		}
	}

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
			error = message(e);
		} finally {
			busy = false;
		}
	}

	function addLocale(code: string) {
		if (!draft || draft.content[code]) return;
		draft.subject[code] = '';
		draft.content[code] = {};
		editLocale = code;
		loadLocaleFields();
	}

	function switchLocale(code: string) {
		syncParagraphs();
		editLocale = code;
		loadLocaleFields();
	}

	function message(e: unknown): string {
		if (e instanceof ApiError) {
			const body = e.body as { detail?: string } | undefined;
			return body?.detail || `Request failed (${e.status}).`;
		}
		return 'Something went wrong.';
	}

	const availableToAdd = $derived(LOCALES.filter((l) => !draft?.content[l.code]));
	const statusTone: Record<BroadcastStatus, string> = {
		draft: 'bg-surface-2 text-muted',
		scheduled: 'bg-accent-soft text-accent',
		sending: 'bg-accent-soft text-accent',
		sent: 'bg-surface-2 text-text',
		canceled: 'bg-surface-2 text-muted'
	};
</script>

<svelte:head><title>Admin · Compose email — Ochorus</title><meta name="robots" content="noindex" /></svelte:head>

<div class="mx-auto max-w-4xl px-5 py-10">
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
					<button class="btn btn-primary btn-sm" onclick={newBroadcast}>New broadcast</button>
				</div>
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
			<p class="mb-4 text-small text-muted">This broadcast has been sent and is read-only.</p>
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
				{/if}
			</div>

			{#if draft.content[editLocale]}
				<label class="mb-3 block">
					<span class="mb-1 block text-micro text-muted">Subject line</span>
					<input class="w-full rounded-md border border-border bg-surface p-2 text-body" bind:value={draft.subject[editLocale]} disabled={readOnly} />
				</label>
				<label class="mb-3 block">
					<span class="mb-1 block text-micro text-muted">Heading</span>
					<input class="w-full rounded-md border border-border bg-surface p-2 text-body" bind:value={draft.content[editLocale].heading} disabled={readOnly} />
				</label>
				<label class="mb-3 block">
					<span class="mb-1 block text-micro text-muted">Body — one paragraph per line</span>
					<textarea class="h-40 w-full rounded-md border border-border bg-surface p-2 text-body" bind:value={paragraphsText} onblur={syncParagraphs} disabled={readOnly}></textarea>
				</label>
				<div class="grid grid-cols-2 gap-3">
					<label class="block">
						<span class="mb-1 block text-micro text-muted">Button label (optional)</span>
						<input class="w-full rounded-md border border-border bg-surface p-2 text-small" bind:value={draft.content[editLocale].cta_label} disabled={readOnly} />
					</label>
					<label class="block">
						<span class="mb-1 block text-micro text-muted">Button link path (e.g. books)</span>
						<input class="w-full rounded-md border border-border bg-surface p-2 text-small" bind:value={draft.content[editLocale].cta_path} disabled={readOnly} />
					</label>
				</div>
			{/if}
		</section>

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
					<span class="mx-1 h-5 w-px bg-border"></span>
					<input type="datetime-local" class="rounded-md border border-border bg-surface p-1.5 text-small" bind:value={scheduleAt} />
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
