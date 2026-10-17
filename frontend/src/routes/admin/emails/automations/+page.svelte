<script lang="ts">
	import { goto } from '$app/navigation';
	import { adminResource } from '$lib/adminResource.svelte';
	import AdminGate from '$lib/components/AdminGate.svelte';
	import { apiErrorDetail } from '$lib/api';
	import {
		getAutoEmails,
		listLifecycleEmails,
		listAutomations,
		createAutomation,
		updateAutoEmail,
		buildDigestNow,
		type AutoEmailConfig,
		type AutoEmailKey,
		type AutoEmails,
		type BroadcastStatus,
		type DigestSection
	} from '$lib/library-admin';

	const auto = adminResource(getAutoEmails, "Couldn't load the automated emails.");
	const lifecycle = adminResource(listLifecycleEmails, "Couldn't load the onboarding emails.");
	const flows = adminResource(listAutomations, "Couldn't load your automations.");

	async function newFlow() {
		const name = prompt('Name the automation', 'Finished a Murray book → suggest Humility')?.trim();
		if (!name) return;
		busy = true;
		try {
			const created = await createAutomation(name);
			await goto(`/admin/emails/flows/${created.id}`);
		} catch (e) {
			error = apiErrorDetail(e);
		} finally {
			busy = false;
		}
	}
	const triggerLabel = (key: string | undefined) =>
		flows.data?.vocabulary.triggers.find((t) => t.key === key)?.label ?? 'No trigger yet';

	let busy = $state(false);
	let error = $state('');
	let notice = $state('');

	// What each one does, in a sentence: the switch alone doesn't say.
	const ABOUT: Record<AutoEmailKey, string> = {
		digest:
			'Built three days before the first Monday of each month, per language: what was published there since the last issue, a quote, a reading plan, and each reader’s own book in progress. A language with nothing new, no quote and no plan is left out that month.',
		new_in_language:
			'When a book or sermon is published in a language, it waits three days to gather anything else new, then sends one email to readers of that language — at most one a week. Only works published after it is switched on are announced.'
	};
	const SECTION_LABELS: Record<DigestSection, string> = {
		letter: 'A short letter you write (an empty text block to fill in each month)',
		continue: 'Continue reading — each reader’s own book in progress',
		new: 'New this month — books and sermons published in the language',
		quote: 'A quote from the library',
		plan: 'A reading plan to start'
	};
	const SECTIONS = Object.keys(SECTION_LABELS) as DigestSection[];

	const statusTone: Record<BroadcastStatus, string> = {
		draft: 'bg-warning/15 text-warning',
		scheduled: 'bg-accent-soft text-accent',
		sending: 'bg-accent-soft text-accent',
		paused: 'bg-warning/15 text-warning',
		sent: 'bg-surface-2 text-text',
		canceled: 'bg-surface-2 text-muted'
	};

	const dateFmt = new Intl.DateTimeFormat('en', { dateStyle: 'medium', timeStyle: 'short' });
	const when = (iso: string | null) => (iso ? dateFmt.format(new Date(iso)) : '—');

	async function run(fn: () => Promise<AutoEmails>, done: string) {
		busy = true;
		error = '';
		notice = '';
		try {
			auto.data = await fn();
			notice = done;
		} catch (e) {
			error = apiErrorDetail(e);
		} finally {
			busy = false;
		}
	}

	const toggle = (c: AutoEmailConfig) =>
		run(
			() => updateAutoEmail({ key: c.key, enabled: !c.enabled }),
			c.enabled ? `${c.label} is off.` : `${c.label} is on.`
		);

	const setApproval = (c: AutoEmailConfig, require_approval: boolean) =>
		run(() => updateAutoEmail({ key: c.key, require_approval }), 'Saved.');

	const setSection = (c: AutoEmailConfig, section: DigestSection, on: boolean) =>
		run(
			() => updateAutoEmail({ key: c.key, sections: { ...c.sections!, [section]: on } }),
			'Saved.'
		);

	const buildNow = () =>
		run(buildDigestNow, 'Built. It is a draft — open it below to read, edit and approve it.');
</script>

<svelte:head><title>Admin · Automated emails — Ochorus</title><meta name="robots" content="noindex" /></svelte:head>

<div class="mx-auto max-w-5xl px-5 py-10">
	<header class="mb-6">
		<p class="eyebrow mb-2 text-accent">Admin</p>
		<h1 class="text-h1">Automated emails</h1>
		<p class="mt-2 max-w-prose text-body text-muted">
			Emails the system builds on its own. Each one becomes an ordinary broadcast you can open, edit and send from
			Compose; with approval on, nothing goes out until you approve it. Readers choose these in their email
			preferences, separately from announcements.
		</p>
	</header>

	{#if error}
		<div class="mb-4 rounded-card border border-danger/40 bg-danger/10 p-3 text-small text-danger">{error}</div>
	{/if}
	{#if notice}
		<div class="mb-4 rounded-card border border-border bg-surface-2 p-3 text-small text-text" aria-live="polite">{notice}</div>
	{/if}

	<section class="mb-6 rounded-card border border-border bg-surface p-4" aria-labelledby="flows-title">
		<div class="mb-3 flex flex-wrap items-baseline justify-between gap-2">
			<div>
				<h2 id="flows-title" class="text-h3">Your automations</h2>
				<p class="text-small text-muted">“When a reader does this, wait, check that, send this” — built here, without a developer.</p>
			</div>
			<button class="btn btn-primary btn-sm" onclick={newFlow} disabled={busy}>New automation</button>
		</div>
		<AdminGate resource={flows} errorTitle="Couldn't load your automations">
			{#snippet children(f)}
				{#if f.automations.length === 0}
					<p class="text-small text-muted">None yet.</p>
				{:else}
					<div class="overflow-x-auto">
						<table class="w-full text-small">
							<thead>
								<tr class="border-b border-border text-left text-muted">
									<th class="p-2 font-semibold">Automation</th>
									<th class="p-2 font-semibold">Starts when</th>
									<th class="p-2 text-right font-semibold">Emails</th>
									<th class="p-2 text-right font-semibold">In progress</th>
									<th class="p-2 text-right font-semibold">Sent</th>
									<th class="p-2 text-right font-semibold">Click rate</th>
									<th class="p-2 font-semibold">Status</th>
									<th class="p-2"></th>
								</tr>
							</thead>
							<tbody>
								{#each f.automations as a (a.id)}
									<tr class="border-b border-border/50">
										<td class="p-2 font-medium text-text">{a.name}</td>
										<td class="p-2 text-muted">{triggerLabel(a.trigger.type)}</td>
										<td class="p-2 text-right tabular-nums">{a.emails}</td>
										<td class="p-2 text-right tabular-nums">{a.runs.active ?? 0}</td>
										<td class="p-2 text-right tabular-nums">{a.stats.sent}</td>
										<td class="p-2 text-right tabular-nums">{a.stats.sent ? `${(a.stats.click_rate * 100).toFixed(1)}%` : '—'}</td>
										<td class="p-2"><span class="rounded-full px-2 py-0.5 text-micro {a.enabled ? 'bg-accent-soft text-accent' : 'bg-surface-2 text-muted'}">{a.enabled ? 'On' : 'Off'}</span></td>
										<td class="p-2 text-right"><a class="btn btn-ghost btn-sm" href="/admin/emails/flows/{a.id}">Open</a></td>
									</tr>
								{/each}
							</tbody>
						</table>
					</div>
				{/if}
			{/snippet}
		</AdminGate>
	</section>

	<section class="mb-6 rounded-card border border-border bg-surface p-4" aria-labelledby="words-title">
		<h2 id="words-title" class="text-h3">Onboarding and reading emails</h2>
		<p class="mb-3 text-small text-muted">
			The emails readers get as they go — their words, per language. Each starts from the original; edit and publish to
			change what readers get.
		</p>
		<AdminGate resource={lifecycle} errorTitle="Couldn't load the onboarding emails">
			{#snippet children(l)}
				<div class="overflow-x-auto">
					<table class="w-full text-small">
						<thead>
							<tr class="border-b border-border text-left text-muted">
								<th class="p-2 font-semibold">Email</th>
								<th class="p-2 font-semibold">Goes out</th>
								<th class="p-2 font-semibold">Subject (English)</th>
								<th class="p-2 font-semibold">Languages</th>
								<th class="p-2"></th>
							</tr>
						</thead>
						<tbody>
							{#each l.steps as s (s.key)}
								<tr class="border-b border-border/50">
									<td class="p-2 font-medium text-text">{s.label}</td>
									<td class="p-2 text-muted">{s.when}</td>
									<td class="p-2 text-text">{s.subject}</td>
									<td class="p-2 text-muted">
										{s.languages}
										{#if s.counts.published}· {s.counts.published} published{/if}
										{#if s.counts.edited}· {s.counts.edited} unpublished{/if}
										{#if s.counts.draft || s.counts.requested}· {(s.counts.draft ?? 0) + (s.counts.requested ?? 0)} AI draft{/if}
										{#if s.counts.original === s.languages}· all original{/if}
										{#if s.stale}<span class="text-warning"> · {s.stale} to review</span>{/if}
									</td>
									<td class="p-2 text-right"><a class="btn btn-ghost btn-sm" href="/admin/emails/automations/{s.key}">Edit</a></td>
								</tr>
							{/each}
						</tbody>
					</table>
				</div>
			{/snippet}
		</AdminGate>
	</section>

	<AdminGate resource={auto} errorTitle="Couldn't load the automated emails">
		{#snippet children(d)}
			<div class="mb-6 grid grid-cols-1 gap-4 lg:grid-cols-2">
				{#each d.configs as c (c.key)}
					<section class="rounded-card border border-border bg-surface p-4">
						<div class="mb-2 flex items-start justify-between gap-3">
							<h2 class="text-h3">{c.label}</h2>
							<button
								class="btn btn-sm {c.enabled ? 'btn-ghost' : 'btn-primary'}"
								onclick={() => toggle(c)}
								disabled={busy}
								aria-pressed={c.enabled}
							>{c.enabled ? 'Turn off' : 'Turn on'}</button>
						</div>
						<p class="mb-3 text-small text-muted">{ABOUT[c.key]}</p>
						<p class="mb-3 text-small">
							{#if c.enabled}
								<span class="rounded-full bg-accent-soft px-2 py-0.5 text-micro text-accent">On</span>
								<span class="text-muted">since {when(c.enabled_at)}{c.updated_by ? ` · last changed by ${c.updated_by}` : ''}</span>
							{:else}
								<span class="rounded-full bg-surface-2 px-2 py-0.5 text-micro text-muted">Off</span>
							{/if}
						</p>
						{#if c.key === 'digest'}
							<p class="mb-3 text-small text-text">
								Next issue: <strong>{when(d.digest_next_send)}</strong>
								<span class="text-muted">(built {when(d.digest_builds_at)})</span>
							</p>
						{/if}

						<fieldset class="mb-3">
							<legend class="mb-1 text-small font-semibold text-text">Before it sends</legend>
							<label class="flex items-center gap-2 text-small">
								<input type="radio" name="approval-{c.key}" checked={c.require_approval} onchange={() => setApproval(c, true)} disabled={busy} />
								Build a draft and wait for my approval
							</label>
							<label class="flex items-center gap-2 text-small">
								<input type="radio" name="approval-{c.key}" checked={!c.require_approval} onchange={() => setApproval(c, false)} disabled={busy} />
								Send automatically
							</label>
						</fieldset>

						{#if c.sections}
							<fieldset class="mb-3">
								<legend class="mb-1 text-small font-semibold text-text">What goes in</legend>
								{#each SECTIONS as s (s)}
									<label class="flex items-start gap-2 text-small">
										<input class="mt-1" type="checkbox" checked={c.sections[s]} onchange={(e) => setSection(c, s, (e.currentTarget as HTMLInputElement).checked)} disabled={busy} />
										{SECTION_LABELS[s]}
									</label>
								{/each}
							</fieldset>
							<button class="btn btn-ghost btn-sm" onclick={buildNow} disabled={busy}>Build the next issue now</button>
							<p class="mt-1 text-micro text-muted">
								For a look before its date, or to send early. It holds only what is published so far, and it
								won’t be rebuilt later.
							</p>
						{/if}
					</section>
				{/each}
			</div>

			<section class="rounded-card border border-border bg-surface p-4">
				<h2 class="mb-3 text-h3">What they built</h2>
				{#if d.recent.length === 0}
					<p class="text-small text-muted">Nothing yet. Built emails appear here and in Compose.</p>
				{:else}
					<div class="overflow-x-auto">
						<table class="w-full text-small">
							<thead>
								<tr class="border-b border-border text-left text-muted">
									<th class="p-2 font-semibold">Name</th>
									<th class="p-2 font-semibold">Status</th>
									<th class="p-2 font-semibold">For</th>
									<th class="p-2 font-semibold">Languages</th>
									<th class="p-2 text-right font-semibold">Sent</th>
									<th class="p-2"></th>
								</tr>
							</thead>
							<tbody>
								{#each d.recent as b (b.id)}
									<tr class="border-b border-border/50">
										<td class="p-2 font-medium text-text">{b.name}</td>
										<td class="p-2">
											<span class="rounded-full px-2 py-0.5 text-micro {statusTone[b.status]}">{b.status === 'draft' ? 'awaiting approval' : b.status}</span>
										</td>
										<td class="p-2 text-muted">{when(b.scheduled_at)}</td>
										<td class="p-2 text-muted">{b.locales.join(', ') || '—'}</td>
										<td class="p-2 text-right tabular-nums">{b.progress.sent}</td>
										<td class="p-2 text-right"><a class="btn btn-ghost btn-sm" href="/admin/emails/compose?id={b.id}">Open</a></td>
									</tr>
								{/each}
							</tbody>
						</table>
					</div>
				{/if}
			</section>
		{/snippet}
	</AdminGate>
</div>
