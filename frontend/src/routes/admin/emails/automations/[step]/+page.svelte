<script lang="ts">
	import { adminResource } from '$lib/adminResource.svelte';
	import AdminGate from '$lib/components/AdminGate.svelte';
	import EmailBlocksEditor from '$lib/components/EmailBlocksEditor.svelte';
	import EmailPreview from '$lib/components/EmailPreview.svelte';
	import MergeTagMenu from '$lib/components/MergeTagMenu.svelte';
	import { apiErrorDetail } from '$lib/api';
	import {
		getLifecycleEmail,
		lifecycleEmailAction,
		listLifecycleEmails,
		saveLifecycleEmail,
		type BroadcastBlock,
		type LifecycleAction,
		type LifecycleDetail,
		type LifecycleStatus
	} from '$lib/library-admin';

	let { data } = $props();
	const step = $derived(data.step);

	const email = adminResource(
		() => getLifecycleEmail(step),
		"Couldn't load this email.",
		() => step,
		(d) => take(d)
	);
	const steps = adminResource(listLifecycleEmails, "Couldn't load the automated emails.");

	// The working copy being edited (the page owns it; Save sends it).
	let subject = $state<Record<string, string>>({});
	let content = $state<Record<string, BroadcastBlock>>({});
	let lang = $state('en');
	// What was last loaded or saved — unsaved changes are any difference from it.
	let baseline = $state('');
	const dirty = $derived(JSON.stringify({ subject, content }) !== baseline);
	let busy = $state(false);
	let error = $state('');
	let notice = $state('');
	let showHistory = $state(false);

	function take(d: LifecycleDetail) {
		subject = { ...d.subject };
		content = structuredClone(d.content);
		if (!(lang in d.content)) lang = 'en';
		baseline = JSON.stringify({ subject, content });
	}

	// "Insert tag" fills the word field focused last (never a link or address).
	let tagTarget: HTMLInputElement | HTMLTextAreaElement | null = null;
	function trackTagTarget(e: FocusEvent) {
		const el = e.target;
		if ((el instanceof HTMLTextAreaElement || el instanceof HTMLInputElement) && el.dataset.tags !== undefined) tagTarget = el;
	}

	const STATUS: Record<LifecycleStatus, { label: string; cls: string }> = {
		original: { label: 'Original', cls: 'border-border text-muted' },
		edited: { label: 'Unpublished changes', cls: 'border-warning/50 text-warning' },
		published: { label: 'Published', cls: 'border-accent text-accent' },
		requested: { label: 'AI draft requested', cls: 'border-border text-muted' },
		draft: { label: 'AI draft — review', cls: 'border-warning/50 text-warning' }
	};

	const detail = $derived(email.data);
	const status = $derived(detail?.statuses[lang]);
	const edited = $derived(
		detail ? Object.entries(detail.statuses).filter(([, s]) => s.status === 'edited').map(([c]) => c) : []
	);
	const staleCount = $derived(detail ? Object.values(detail.statuses).filter((s) => s.stale).length : 0);
	const name = (code: string) => detail?.names[code] ?? code;

	async function run(fn: () => Promise<LifecycleDetail>, done: string) {
		busy = true;
		error = '';
		notice = '';
		try {
			const d = await fn();
			email.data = d;
			take(d);
			notice = done;
			void steps.load();
		} catch (e) {
			error = apiErrorDetail(e);
		} finally {
			busy = false;
		}
	}

	const save = () =>
		run(() => saveLifecycleEmail(step, { subject, content }), 'Saved. Readers see nothing new until you publish.');

	/** Save first when there are edits, so an action never loses them. */
	async function act(action: LifecycleAction, extra: Parameters<typeof lifecycleEmailAction>[2], done: string) {
		await run(async () => {
			if (dirty) await saveLifecycleEmail(step, { subject, content });
			return lifecycleEmailAction(step, action, extra);
		}, done);
	}

	function publish() {
		const langs = dirty ? [...new Set([...edited, lang])] : edited;
		if (!confirm(`Publish ${langs.map(name).join(', ') || 'these changes'}? Readers get the new words from the next send.`)) return;
		act('publish', {}, 'Published. Readers get the new words from the next send.');
	}

	function resetLanguage() {
		if (!confirm(`Put ${name(lang)} back to the original words? It sends the original from the next send.`)) return;
		act('reset', { language: lang }, `${name(lang)} is back to the original.`);
	}

</script>

<svelte:head><title>Admin · Automated email — Ochorus</title><meta name="robots" content="noindex" /></svelte:head>

<div class="mx-auto max-w-7xl px-5 py-10">
	<a class="text-small text-accent hover:underline" href="/admin/emails/automations">← Automated emails</a>

	{#if error}
		<div class="my-4 rounded-card border border-danger/40 bg-danger/10 p-3 text-small text-danger">{error}</div>
	{/if}
	{#if notice}
		<div class="my-4 rounded-card border border-border bg-surface-2 p-3 text-small text-text" aria-live="polite">{notice}</div>
	{/if}

	<AdminGate resource={email} errorTitle="Couldn't load this email">
		{#snippet children(d)}
			<header class="my-4 flex flex-wrap items-end justify-between gap-3">
				<div>
					<p class="eyebrow mb-1 text-accent">Automated email · {d.when}</p>
					<h1 class="text-h1">{d.label}</h1>
					<p class="mt-1 max-w-prose text-small text-muted">
						Edit freely — saving changes nothing a reader sees. Publish sends the new words from the next send; a language
						you haven't published keeps its original.
					</p>
				</div>
				<div class="flex flex-wrap gap-2">
					<button class="btn btn-ghost btn-sm" onclick={() => (showHistory = !showHistory)} aria-expanded={showHistory}>History · {d.versions.length}</button>
					<button class="btn btn-ghost btn-sm" onclick={save} disabled={busy || !dirty}>Save</button>
					<button class="btn btn-primary btn-sm" onclick={publish} disabled={busy || (!dirty && !edited.length)}>Publish changes</button>
				</div>
			</header>

			{#if showHistory}
				<section class="mb-4 rounded-card border border-border bg-surface p-4">
					<h2 class="mb-2 text-h3">History</h2>
					{#if d.versions.length === 0}
						<p class="text-small text-muted">Nothing published yet — every language sends its original.</p>
					{:else}
						<ul class="divide-y divide-border/60 text-small">
							{#each d.versions as v (v.id)}
								<li class="flex flex-wrap items-center justify-between gap-2 py-2">
									<span>{new Date(v.published_at).toLocaleString()} · {v.published_by || 'someone'} · {v.languages.join(', ')}</span>
									<button class="btn btn-ghost btn-sm" onclick={() => act('restore', { version: v.id }, 'Restored into the working copy — publish to send it.')} disabled={busy}>Restore</button>
								</li>
							{/each}
						</ul>
					{/if}
				</section>
			{/if}

			<div class="grid grid-cols-1 gap-5 lg:grid-cols-[16rem_1fr]">
				<nav aria-label="Automated emails" class="space-y-1">
					{#each steps.data?.steps ?? [] as s (s.key)}
						<a
							class="block rounded-md border p-2 text-small {s.key === step ? 'border-accent bg-accent-soft' : 'border-border bg-surface hover:border-accent'}"
							href="/admin/emails/automations/{s.key}"
							aria-current={s.key === step ? 'page' : undefined}
						>
							<span class="block font-semibold text-text">{s.label}</span>
							<span class="block text-micro text-muted">{s.when}</span>
							{#if s.counts.published || s.counts.edited || s.stale}
								<span class="block text-micro {s.stale ? 'text-warning' : 'text-accent'}">
									{s.counts.published ? `${s.counts.published} published` : ''}{s.counts.edited ? ` · ${s.counts.edited} unpublished` : ''}{s.stale ? ` · ${s.stale} to review` : ''}
								</span>
							{/if}
						</a>
					{/each}
				</nav>

				<section class="min-w-0 rounded-card border border-border bg-surface p-4" onfocusin={trackTagTarget}>
					<div class="mb-3 flex flex-wrap items-center gap-1.5" role="tablist" aria-label="Language">
						{#each Object.keys(d.statuses) as code (code)}
							{@const s = d.statuses[code]}
							<button
								role="tab"
								aria-selected={code === lang}
								class="rounded-full border px-2.5 py-0.5 text-micro {code === lang ? 'bg-accent text-accent-contrast border-accent' : STATUS[s.status].cls}"
								title="{STATUS[s.status].label}{s.stale ? ' · the English changed since' : ''}"
								onclick={() => (lang = code)}>{code}{s.stale ? ' •' : ''}</button
							>
						{/each}
						{#if staleCount}
							<button class="btn btn-ghost btn-sm ms-auto" onclick={() => act('request_stale', {}, 'AI drafts requested for the languages the English change left behind.')} disabled={busy}>
								Re-translate the {staleCount} the English change left behind
							</button>
						{/if}
					</div>

					{#if status}
						<div class="mb-3 flex flex-wrap items-center justify-between gap-2 text-small">
							<span>
								<span class="font-semibold text-text">{name(lang)}</span> · {STATUS[status.status].label}{status.published_at
									? ` · published ${new Date(status.published_at).toLocaleDateString()}${status.published_by ? ` by ${status.published_by}` : ''}`
									: ''}
								{#if status.stale}<span class="text-warning"> · the English changed since — give it a look</span>{/if}
							</span>
							<span class="flex flex-wrap gap-1">
								{#if status.status === 'draft'}
									<button class="btn btn-primary btn-sm" onclick={() => act('approve', { language: lang }, `${name(lang)} approved — publish to send it.`)} disabled={busy}>Approve the AI draft</button>
								{:else if status.status === 'requested'}
									<button class="btn btn-ghost btn-sm" onclick={() => act('fetch', { language: lang }, 'Checked for the draft.')} disabled={busy}>Check for the draft</button>
								{:else if lang !== 'en'}
									<button class="btn btn-ghost btn-sm" onclick={() => act('request', { language: lang }, `AI draft of the English requested for ${name(lang)}.`)} disabled={busy}>Draft from the English with AI</button>
								{/if}
								{#if status.status !== 'original'}
									<button class="btn btn-ghost btn-sm text-danger" onclick={resetLanguage} disabled={busy}>Reset to the original</button>
								{/if}
							</span>
						</div>
					{/if}

					{#if Object.keys(d.placeholders).length || d.link}
						<p class="mb-3 rounded-md bg-surface-2 p-2 text-micro text-muted">
							This email fills in per reader:
							{#each Object.entries(d.placeholders) as [key, what] (key)}<code class="mx-1">{`{${key}}`}</code>({what}){/each}
							{#if d.link}· a button with the link <code>{'{link}'}</code> goes to {d.link}.{/if}
						</p>
					{/if}

					{#if content[lang]}
						<div class="mb-3 grid grid-cols-1 gap-3 sm:grid-cols-2">
							<label class="block">
								<span class="mb-1 block text-micro text-muted">Subject line</span>
								<input class="w-full rounded-md border border-border bg-surface p-2 text-body" bind:value={subject[lang]} data-tags />
							</label>
							<label class="block">
								<span class="mb-1 block text-micro text-muted">Inbox preview text</span>
								<input class="w-full rounded-md border border-border bg-surface p-2 text-body" bind:value={content[lang].preheader} data-tags />
							</label>
						</div>
						<div class="mb-2"><MergeTagMenu getTarget={() => tagTarget} /></div>
						<div class="grid grid-cols-1 gap-5 xl:grid-cols-2">
							<EmailBlocksEditor bind:blocks={content[lang].blocks} locale={lang} localeName={name(lang)} />
							<EmailPreview locale={lang} subject={subject[lang] ?? ''} content={content[lang]} />
						</div>
					{/if}
				</section>
			</div>
		{/snippet}
	</AdminGate>
</div>
