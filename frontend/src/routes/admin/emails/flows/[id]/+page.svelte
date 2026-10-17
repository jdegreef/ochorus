<script lang="ts">
	import { goto } from '$app/navigation';
	import { adminResource } from '$lib/adminResource.svelte';
	import AdminGate from '$lib/components/AdminGate.svelte';
	import EmailBlocksEditor from '$lib/components/EmailBlocksEditor.svelte';
	import EmailPreview from '$lib/components/EmailPreview.svelte';
	import LibrarySlugPicker from '$lib/components/LibrarySlugPicker.svelte';
	import MergeTagMenu from '$lib/components/MergeTagMenu.svelte';
	import { ApiError, apiErrorDetail } from '$lib/api';
	import { localeName } from '$lib/lang.svelte';
	import { locales } from '$lib/paraglide/runtime';
	import {
		addAutomationEmail,
		automationAction,
		automationEmailTranslation,
		deleteAutomation,
		getAutomation,
		getAutomationVocabulary,
		saveAutomation,
		saveAutomationEmail,
		type AutomationCondition,
		type AutomationDetail,
		type AutomationEmailRow,
		type AutomationKind,
		type AutomationStep,
		type BroadcastBlock,
		type LibraryBlockType
	} from '$lib/library-admin';

	let { data } = $props();
	const id = $derived(data.id);

	const flow = adminResource(
		() => getAutomation(id),
		"Couldn't load this automation.",
		() => id,
		(d) => take(d)
	);
	const vocab = adminResource(getAutomationVocabulary, "Couldn't load the builder's choices.");

	// The flow being edited — the page owns it; Save sends it.
	let name = $state('');
	let trigger = $state<Record<string, string | number>>({});
	let steps = $state<AutomationStep[]>([]);
	let exitConds = $state<AutomationCondition[]>([]);
	let stream = $state('onboarding');
	let baseline = $state('');
	const dirty = $derived(JSON.stringify({ name, trigger, steps, exitConds, stream }) !== baseline);

	// The emails' words, edited apart from the flow (each saves on its own).
	let emails = $state<Record<number, AutomationEmailRow>>({});
	let emailBaseline = $state<Record<number, string>>({});

	let selected = $state<string | null>(null); // a step id, or 'trigger' / 'exit'
	let emailLang = $state('en');
	let busy = $state(false);
	let error = $state('');
	let notice = $state('');
	let problems = $state<string[]>([]);

	function take(d: AutomationDetail) {
		name = d.name;
		trigger = { ...d.trigger };
		steps = structuredClone(d.steps);
		exitConds = structuredClone(d.exit);
		stream = d.stream;
		baseline = JSON.stringify({ name, trigger, steps, exitConds, stream });
		emails = Object.fromEntries(d.email_list.map((e) => [e.id, structuredClone(e)]));
		emailBaseline = Object.fromEntries(d.email_list.map((e) => [e.id, JSON.stringify([e.subject, e.content])]));
		problems = d.problems;
	}

	const LOCALES = locales.map((code) => ({ code, label: localeName(code) }));
	const label = (code: string) => LOCALES.find((l) => l.code === code)?.label ?? code;
	const kindOf = (table: AutomationKind[] | undefined, key: string) => table?.find((k) => k.key === key);
	const newId = () => Math.random().toString(36).slice(2, 10);
	const pickType = (kind: string): LibraryBlockType => (kind === 'author' ? 'author' : kind === 'plan' ? 'plan' : 'book');

	function describeCondition(c: AutomationCondition): string {
		const check = kindOf(vocab.data?.checks, c.check);
		if (!check) return 'Choose a condition';
		const params = check.params.map((p) => c[p.key]).filter((v) => v !== '' && v !== undefined).join(', ');
		return `${check.label}${params ? ` (${params})` : ''}`;
	}
	/** An exit condition in words, its "not" included (a step card says it in its heading). */
	const describeExit = (c: AutomationCondition) => `${c.negate ? 'not: ' : ''}${describeCondition(c)}`;

	function describe(step: AutomationStep): { kind: string; title: string; detail: string } {
		if (step.type === 'wait') return { kind: 'Wait', title: `${step.days ? `${step.days} day${step.days === 1 ? '' : 's'}` : ''}${step.days && step.hours ? ' ' : ''}${step.hours ? `${step.hours} h` : ''}` || 'Choose how long', detail: '' };
		if (step.type === 'condition') return { kind: step.negate ? 'Only if not' : 'Only if', title: describeCondition(step), detail: 'A reader who fails it leaves the automation.' };
		const email = step.email ? emails[step.email] : undefined;
		return {
			kind: 'Send email',
			title: email ? email.subject.en || email.subject[email.locales[0]] || 'Untitled email' : 'Choose an email',
			detail: email ? `Ready in ${email.ready.length ? email.ready.join(', ') : 'no language yet'}` : ''
		};
	}

	function insert(at: number, type: AutomationStep['type']) {
		const step: AutomationStep =
			type === 'wait'
				? { id: newId(), type, days: 1, hours: 0 }
				: type === 'condition'
					? { id: newId(), type, check: '', negate: false }
					: { id: newId(), type, email: null };
		steps = [...steps.slice(0, at), step, ...steps.slice(at)];
		selected = step.id;
		inserting = null;
	}
	let inserting = $state<number | null>(null);

	function removeStep(sid: string) {
		steps = steps.filter((s) => s.id !== sid);
		selected = null;
	}

	const selectedStep = $derived(steps.find((s) => s.id === selected));

	/** Run an action; returns whether it went through. */
	async function run<T>(fn: () => Promise<T>, done: string, after?: (r: T) => void): Promise<boolean> {
		busy = true;
		error = '';
		notice = '';
		try {
			const r = await fn();
			notice = done;
			after?.(r); // may say something more specific
			return true;
		} catch (e) {
			const body = e instanceof ApiError ? (e.body as { problems?: string[] }) : undefined;
			if (body?.problems) problems = body.problems;
			error = apiErrorDetail(e);
			return false;
		} finally {
			busy = false;
		}
	}

	const keepEmails = (d: AutomationDetail) => {
		const unsaved = Object.fromEntries(Object.entries(emails).filter(([eid, e]) => JSON.stringify([e.subject, e.content]) !== emailBaseline[Number(eid)]));
		flow.data = d;
		take(d);
		emails = { ...emails, ...unsaved }; // a flow save doesn't drop unsaved email edits
	};

	async function saveFlow(): Promise<boolean> {
		const payload = { name, trigger, steps, exit: exitConds, stream };
		try {
			busy = true;
			error = '';
			const d = await saveAutomation(id, payload);
			keepEmails(d);
			notice = 'Saved.';
			return true;
		} catch (e) {
			const body = e instanceof ApiError ? (e.body as { needs_end_runs?: boolean; problems?: string[] }) : undefined;
			if (body?.needs_end_runs) {
				busy = false;
				if (!confirm(`${apiErrorDetail(e)}\n\nSave anyway?`)) return false;
				return run(() => saveAutomation(id, { ...payload, end_runs: true }), 'Saved. Readers who were part-way through have been stopped.', keepEmails);
			}
			if (body?.problems) problems = body.problems;
			error = apiErrorDetail(e);
			return false;
		} finally {
			busy = false;
		}
	}

	async function switchTo(on: boolean) {
		if (on && dirty && !(await saveFlow())) return; // never switch on what didn't save
		if (on && !confirm('Turn it on? Readers who trigger it from now on go through it; nobody from before.')) return;
		await run(() => automationAction(id, on ? 'enable' : 'disable'), on ? 'It’s on.' : 'It’s off — readers part-way through wait where they are.', keepEmails);
	}

	const testRun = () =>
		run(() => automationAction(id, 'test'), '', (d) => {
			keepEmails(d);
			notice = d.sent ? `Sent ${d.sent} test email${d.sent === 1 ? '' : 's'} to ${d.sent_to}.` : 'Nothing was sent — no email is ready yet, or your account has no address.';
		});

	async function remove() {
		if (!confirm('Delete this automation? Readers part-way through stop, and its emails are deleted.')) return;
		await run(() => deleteAutomation(id), 'Deleted.', () => goto('/admin/emails/automations'));
	}

	// --- Email steps ----------------------------------------------------------
	async function newEmail(step: Extract<AutomationStep, { type: 'email' }>) {
		await run(() => addAutomationEmail(id, undefined), 'Email added — write it below.', (e) => {
			emails = { ...emails, [e.id]: structuredClone(e) };
			emailBaseline = { ...emailBaseline, [e.id]: JSON.stringify([e.subject, e.content]) };
			step.email = e.id;
			emailLang = 'en';
		});
	}

	const emailDirty = (eid: number) => !!emails[eid] && JSON.stringify([emails[eid].subject, emails[eid].content]) !== emailBaseline[eid];

	const afterEmail = (e: AutomationEmailRow) => {
		emails = { ...emails, [e.id]: structuredClone(e) };
		emailBaseline = { ...emailBaseline, [e.id]: JSON.stringify([e.subject, e.content]) };
	};

	const saveEmail = (eid: number) =>
		run(() => saveAutomationEmail(eid, { subject: emails[eid].subject, content: emails[eid].content }), 'Email saved.', afterEmail);

	async function translateEmail(eid: number, action: 'request' | 'fetch' | 'approve', lang: string) {
		if (emailDirty(eid)) await saveEmail(eid);
		await run(() => automationEmailTranslation(eid, action, lang), { request: `${label(lang)} AI draft requested.`, fetch: 'Checked for the draft.', approve: `${label(lang)} approved.` }[action], (e) => {
			afterEmail(e);
			if (e.content[lang]) emailLang = lang;
		});
	}

	function addLanguage(eid: number, code: string) {
		const e = emails[eid];
		if (!e || e.content[code]) return;
		e.subject[code] = '';
		e.content[code] = structuredClone($state.snapshot(e.content[emailLang]) ?? { preheader: '', blocks: [] }) as BroadcastBlock;
		emailLang = code;
	}

	let tagTarget: HTMLInputElement | HTMLTextAreaElement | null = null;
	function trackTagTarget(e: FocusEvent) {
		const el = e.target;
		if ((el instanceof HTMLTextAreaElement || el instanceof HTMLInputElement) && el.dataset.tags !== undefined) tagTarget = el;
	}
</script>

<svelte:head><title>Admin · Automation — Ochorus</title><meta name="robots" content="noindex" /></svelte:head>

{#snippet params(kind: AutomationKind | undefined, values: Record<string, string | number | boolean>, set: (key: string, v: string | number) => void, locked = false)}
	{#each kind?.params ?? [] as p (p.key)}
		{#if p.kind === 'number'}
			<label class="block text-small">
				<span class="mb-1 block text-micro text-muted">{p.label}</span>
				<input class="w-28 rounded-md border border-border bg-surface p-2" type="number" min="1" value={values[p.key] ?? p.default ?? ''} oninput={(e) => set(p.key, Number((e.currentTarget as HTMLInputElement).value))} disabled={locked} />
			</label>
		{:else}
			<LibrarySlugPicker type={pickType(p.kind)} value={String(values[p.key] ?? '')} label={p.label} optional={!p.required} disabled={locked} onChange={(slug) => set(p.key, slug)} />
		{/if}
	{/each}
{/snippet}

{#snippet conditionEditor(c: AutomationCondition, onDrop?: () => void)}
	<div class="space-y-2">
		<div class="flex flex-wrap gap-2">
			<select class="rounded-md border border-border bg-surface p-2 text-small" aria-label="Has or has not" value={c.negate ? 'not' : 'has'} onchange={(e) => (c.negate = (e.currentTarget as HTMLSelectElement).value === 'not')}>
				<option value="has">The reader</option>
				<option value="not">The reader has NOT —</option>
			</select>
			<select class="rounded-md border border-border bg-surface p-2 text-small" aria-label="Condition" value={c.check} onchange={(e) => (c.check = (e.currentTarget as HTMLSelectElement).value)}>
				<option value="">Choose…</option>
				{#each vocab.data?.checks ?? [] as k (k.key)}<option value={k.key}>{k.label}</option>{/each}
			</select>
			{#if onDrop}<button class="btn btn-ghost btn-sm text-danger" onclick={onDrop} aria-label="Remove this condition">✕</button>{/if}
		</div>
		{@render params(kindOf(vocab.data?.checks, c.check), c, (k, v) => (c[k] = v))}
	</div>
{/snippet}

<div class="mx-auto max-w-7xl px-5 py-10">
	<a class="text-small text-accent hover:underline" href="/admin/emails/automations">← Automated emails</a>

	{#if error}<div class="my-4 rounded-card border border-danger/40 bg-danger/10 p-3 text-small text-danger">{error}</div>{/if}
	{#if notice}<div class="my-4 rounded-card border border-border bg-surface-2 p-3 text-small text-text" aria-live="polite">{notice}</div>{/if}

	<AdminGate resource={flow} errorTitle="Couldn't load this automation">
		{#snippet children(d)}
			<header class="my-4 flex flex-wrap items-end justify-between gap-3">
				<div class="min-w-0 flex-1">
					<label class="block">
						<span class="eyebrow mb-1 block text-accent">Automation</span>
						<input class="w-full max-w-2xl rounded-md border border-transparent bg-transparent p-1 font-serif text-h1 hover:border-border" aria-label="Name" bind:value={name} />
					</label>
					<p class="mt-1 text-small text-muted">
						<span class="rounded-full px-2 py-0.5 text-micro {d.enabled ? 'bg-accent-soft text-accent' : 'bg-surface-2 text-muted'}">{d.enabled ? 'On' : 'Off'}</span>
						{d.runs.active ?? 0} in progress · {d.runs.done ?? 0} finished · {d.runs.exited ?? 0} left early · {d.stats.sent} sent{d.stats.sent ? ` · ${(d.stats.click_rate * 100).toFixed(1)}% clicked` : ''}
					</p>
				</div>
				<div class="flex flex-wrap gap-2">
					<button class="btn btn-ghost btn-sm" onclick={testRun} disabled={busy}>Send me a test run</button>
					<button class="btn btn-ghost btn-sm" onclick={saveFlow} disabled={busy || !dirty}>Save</button>
					{#if d.enabled}
						<button class="btn btn-ghost btn-sm" onclick={() => switchTo(false)} disabled={busy}>Turn off</button>
					{:else}
						<button class="btn btn-primary btn-sm" onclick={() => switchTo(true)} disabled={busy}>Turn on</button>
					{/if}
					<button class="btn btn-ghost btn-sm text-danger" onclick={remove} disabled={busy}>Delete</button>
				</div>
			</header>

			{#if problems.length && !d.enabled}
				<ul class="mb-4 list-disc space-y-0.5 rounded-card border border-warning/40 bg-warning/10 p-3 ps-8 text-small text-warning">
					{#each problems as p (p)}<li>{p}</li>{/each}
				</ul>
			{/if}
			{#if d.enabled}
				<p class="mb-4 text-small text-muted">It’s on: the steps can’t be added, removed or reordered (readers part-way through are pinned to a step), but waits, conditions and every email’s words can still be edited.</p>
			{/if}

			<div class="grid grid-cols-1 gap-5 lg:grid-cols-[minmax(0,26rem)_1fr]">
				<!-- The flow -->
				<section aria-label="Steps" class="flex flex-col items-stretch rounded-card bg-surface-2 p-4">
					<button class="rounded-card border p-3 text-start {selected === 'trigger' ? 'border-accent bg-surface' : 'border-border bg-surface'}" onclick={() => (selected = 'trigger')}>
						<span class="block text-micro font-semibold uppercase tracking-wide text-accent">Starts when</span>
						<span class="block text-small font-semibold text-text">{kindOf(vocab.data?.triggers, String(trigger.type ?? ''))?.label ?? 'Choose a trigger'}</span>
						<span class="block text-micro text-muted">{Object.entries(trigger).filter(([k, v]) => k !== 'type' && v).map(([, v]) => v).join(' · ')}</span>
					</button>

					{#each steps as step, i (step.id)}
						{@const info = describe(step)}
						<div class="flex flex-col items-center py-1">
							<span class="h-3 w-px bg-border" aria-hidden="true"></span>
							{#if !d.enabled}
								<button class="h-7 w-7 rounded-full border border-dashed border-border bg-surface text-small" aria-label="Add a step here" onclick={() => (inserting = inserting === i ? null : i)}>+</button>
								{#if inserting === i}
									<div class="mt-1 flex gap-1">
										<button class="btn btn-ghost btn-sm" onclick={() => insert(i, 'wait')}>Wait</button>
										<button class="btn btn-ghost btn-sm" onclick={() => insert(i, 'condition')}>Only if</button>
										<button class="btn btn-ghost btn-sm" onclick={() => insert(i, 'email')}>Send email</button>
									</div>
								{/if}
							{/if}
							<span class="h-3 w-px bg-border" aria-hidden="true"></span>
						</div>
						<button class="rounded-card border p-3 text-start {selected === step.id ? 'border-accent bg-surface' : 'border-border bg-surface'}" onclick={() => (selected = step.id)}>
							<span class="block text-micro font-semibold uppercase tracking-wide {step.type === 'email' ? 'text-accent' : step.type === 'condition' ? 'text-warning' : 'text-muted'}">{info.kind}</span>
							<span class="block text-small font-semibold text-text">{info.title}</span>
							{#if info.detail}<span class="block text-micro text-muted">{info.detail}</span>{/if}
						</button>
					{/each}

					<div class="flex flex-col items-center py-1">
						<span class="h-3 w-px bg-border" aria-hidden="true"></span>
						{#if !d.enabled}
							<button class="h-7 w-7 rounded-full border border-dashed border-border bg-surface text-small" aria-label="Add a step at the end" onclick={() => (inserting = inserting === steps.length ? null : steps.length)}>+</button>
							{#if inserting === steps.length}
								<div class="mt-1 flex gap-1">
									<button class="btn btn-ghost btn-sm" onclick={() => insert(steps.length, 'wait')}>Wait</button>
									<button class="btn btn-ghost btn-sm" onclick={() => insert(steps.length, 'condition')}>Only if</button>
									<button class="btn btn-ghost btn-sm" onclick={() => insert(steps.length, 'email')}>Send email</button>
								</div>
							{/if}
						{/if}
						<span class="h-3 w-px bg-border" aria-hidden="true"></span>
					</div>
					<p class="self-center rounded-full border border-border bg-surface px-3 py-1 text-micro text-muted">End — the reader leaves this automation</p>

					<button class="mt-4 rounded-card border p-3 text-start {selected === 'exit' ? 'border-accent bg-surface' : 'border-border bg-surface'}" onclick={() => (selected = 'exit')}>
						<span class="block text-micro font-semibold uppercase tracking-wide text-muted">Leaves early if</span>
						<span class="block text-small text-text">
							{exitConds.length ? exitConds.map(describeExit).join('; ') : 'Nothing extra'} — and always if they unsubscribe. Each reader goes through it once.
						</span>
					</button>
				</section>

				<!-- The selected step -->
				<section aria-label="Selected step" class="min-w-0 rounded-card border border-border bg-surface p-4" onfocusin={trackTagTarget}>
					{#if selected === 'trigger'}
						<h2 class="mb-3 text-h3">Starts when</h2>
						<select class="mb-3 rounded-md border border-border bg-surface p-2 text-small" aria-label="Trigger" value={trigger.type ?? ''} disabled={d.enabled} onchange={(e) => (trigger = { type: (e.currentTarget as HTMLSelectElement).value })}>
							<option value="">Choose…</option>
							{#each vocab.data?.triggers ?? [] as k (k.key)}<option value={k.key}>{k.label}</option>{/each}
						</select>
						<div class="space-y-3">{@render params(kindOf(vocab.data?.triggers, String(trigger.type ?? '')), trigger, (k, v) => (trigger[k] = v))}</div>
						<label class="mt-4 block text-small">
							<span class="mb-1 block text-micro text-muted">Obeys the reader’s email choice for</span>
							<select class="rounded-md border border-border bg-surface p-2" bind:value={stream}>
								{#each vocab.data?.streams ?? [] as s (s.key)}<option value={s.key}>{s.label}</option>{/each}
							</select>
						</label>
						<p class="mt-3 text-micro text-muted">Only what readers do after it is switched on counts — turning it on never mails the past.</p>
					{:else if selected === 'exit'}
						<h2 class="mb-3 text-h3">Leaves early if…</h2>
						<div class="space-y-4">
							{#each exitConds as c, i (i)}{@render conditionEditor(c, () => (exitConds = exitConds.filter((_, k) => k !== i)))}{/each}
						</div>
						<button class="btn btn-ghost btn-sm mt-3" onclick={() => (exitConds = [...exitConds, { check: '', negate: false }])}>+ Add a condition</button>
					{:else if selectedStep}
						<div class="mb-3 flex items-center justify-between gap-2">
							<h2 class="text-h3">{describe(selectedStep).kind}</h2>
							{#if !d.enabled}<button class="btn btn-ghost btn-sm text-danger" onclick={() => removeStep(selectedStep.id)}>Remove step</button>{/if}
						</div>
						{#if selectedStep.type === 'wait'}
							<div class="flex gap-3 text-small">
								<label><span class="mb-1 block text-micro text-muted">Days</span><input class="w-24 rounded-md border border-border bg-surface p-2" type="number" min="0" bind:value={selectedStep.days} /></label>
								<label><span class="mb-1 block text-micro text-muted">Hours</span><input class="w-24 rounded-md border border-border bg-surface p-2" type="number" min="0" max="23" bind:value={selectedStep.hours} /></label>
							</div>
						{:else if selectedStep.type === 'condition'}
							{@render conditionEditor(selectedStep)}
						{:else if selectedStep.type === 'email'}
							{@const e = selectedStep.email ? emails[selectedStep.email] : undefined}
							{#if !e}
								<p class="mb-2 text-small text-muted">This step has no email yet.</p>
								<button class="btn btn-primary btn-sm" onclick={() => newEmail(selectedStep as Extract<AutomationStep, { type: 'email' }>)} disabled={busy}>Write a new email</button>
							{:else}
								<div class="mb-3 flex flex-wrap items-center gap-1.5">
									{#each e.locales as code (code)}
										{@const t = e.translations[code]}
										<button class="rounded-full border px-2.5 py-0.5 text-micro {code === emailLang ? 'border-accent bg-accent-soft text-accent' : 'border-border text-muted'}" onclick={() => (emailLang = code)}>
											{label(code)}{t?.state === 'draft' ? ' · review' : t?.state === 'requested' ? ' · requested' : e.ready.includes(code) ? '' : ' · incomplete'}
										</button>
									{/each}
									<select class="rounded-md border border-border bg-surface p-1 text-micro" aria-label="Add a language" onchange={(ev) => { const v = (ev.currentTarget as HTMLSelectElement).value; (ev.currentTarget as HTMLSelectElement).value = ''; if (v) addLanguage(e.id, v); }}>
										<option value="">+ Write a language</option>
										{#each LOCALES.filter((l) => !e.content[l.code]) as l (l.code)}<option value={l.code}>{l.label}</option>{/each}
									</select>
									<select class="rounded-md border border-border bg-surface p-1 text-micro" aria-label="Draft a language with AI" disabled={busy || !e.ready.includes('en')} onchange={(ev) => { const v = (ev.currentTarget as HTMLSelectElement).value; (ev.currentTarget as HTMLSelectElement).value = ''; if (v) translateEmail(e.id, 'request', v); }}>
										<option value="">✦ Draft with AI</option>
										{#each LOCALES.filter((l) => l.code !== 'en' && !e.translations[l.code]) as l (l.code)}<option value={l.code}>{l.label}</option>{/each}
									</select>
								</div>
								<p class="mb-3 text-micro text-muted">Readers in a language this email isn’t ready in skip it and carry on to the next step.</p>
								{#if e.translations[emailLang]?.state === 'draft'}
									<div class="mb-3 flex flex-wrap items-center justify-between gap-2 rounded-md bg-warning/10 p-2 text-small text-warning">
										AI draft — read it, edit anything that’s off, then approve it. It isn’t sent until you do.
										<button class="btn btn-primary btn-sm" onclick={() => translateEmail(e.id, 'approve', emailLang)} disabled={busy}>Approve {label(emailLang)}</button>
									</div>
								{/if}
								{#each Object.entries(e.translations).filter(([, t]) => t.state === 'requested') as [code] (code)}
									<p class="mb-2 text-small text-muted">{label(code)}: AI draft requested. <button class="btn btn-ghost btn-sm" onclick={() => translateEmail(e.id, 'fetch', code)} disabled={busy}>Check for it</button></p>
								{/each}
								{#if e.content[emailLang]}
									<div class="mb-3 grid grid-cols-1 gap-3 sm:grid-cols-2">
										<label class="block"><span class="mb-1 block text-micro text-muted">Subject line</span><input class="w-full rounded-md border border-border bg-surface p-2 text-body" bind:value={e.subject[emailLang]} data-tags /></label>
										<label class="block"><span class="mb-1 block text-micro text-muted">Inbox preview text</span><input class="w-full rounded-md border border-border bg-surface p-2 text-body" bind:value={e.content[emailLang].preheader} data-tags /></label>
									</div>
									<div class="mb-2 flex flex-wrap items-center gap-2">
										<MergeTagMenu getTarget={() => tagTarget} />
										<button class="btn btn-primary btn-sm" onclick={() => saveEmail(e.id)} disabled={busy || !emailDirty(e.id)}>Save email</button>
									</div>
									<div class="grid grid-cols-1 gap-5 2xl:grid-cols-2">
										<EmailBlocksEditor bind:blocks={e.content[emailLang].blocks} locale={emailLang} localeName={label(emailLang)} />
										<EmailPreview locale={emailLang} subject={e.subject[emailLang] ?? ''} content={e.content[emailLang]} />
									</div>
								{/if}
							{/if}
						{/if}
					{:else}
						<p class="text-small text-muted">Choose a step on the left to edit it, or press + to add one.</p>
					{/if}
				</section>
			</div>
		{/snippet}
	</AdminGate>
</div>
