<script lang="ts">
	import { adminResource } from '$lib/adminResource.svelte';
	import type { AdminScope } from '$lib/adminAccess';
	import { languageNames } from '$lib/adminHelp';
	import { emailProblem, memberLanguages, sharedLanguages } from '$lib/adminTeam';
	import AdminGate from '$lib/components/AdminGate.svelte';
	import { localeName } from '$lib/lang.svelte';
	import {
		getAdminTeam,
		grantAdminAccess,
		revokeAdminAccess,
		type AdminTeam,
		type TeamMember
	} from '$lib/library-admin';

	const res = adminResource(getAdminTeam, 'Something went wrong loading the team.');

	// A role + language choice, shared by the grant form and each member's
	// Manage panel. No language is chosen to start: the quickest path through
	// the form must not be the widest grant, and "all" also covers every
	// language added later.
	type RoleChoice = { role: string; langs: Record<string, boolean>; all: boolean };
	const freshChoice = (): RoleChoice => ({ role: 'contributor', langs: {}, all: false });
	const choiceLangs = (p: RoleChoice, available: string[]) => (p.all ? ['*'] : available.filter((c) => p.langs[c]));

	// Grant form state.
	let email = $state('');
	let emailTouched = $state(false); // judge the address at blur, not per keystroke
	let form = $state<RoleChoice>(freshChoice());
	let granting = $state(false);
	let formError = $state('');

	// Per-member row state, keyed by email.
	let busy = $state<Record<string, boolean>>({}); // a request in flight
	let confirming = $state<Record<string, boolean>>({}); // revoke asked, not yet confirmed
	let rowError = $state<Record<string, string>>({});
	// The one member whose Manage panel is open, with the edit in progress.
	let editing = $state<{ email: string; pick: RoleChoice; mixed: boolean } | null>(null);
	// Recent revokes, each with the exact rows to put back. A list, so a second
	// revoke never takes away the first one's Undo.
	type Undo = { email: string; scopes: AdminScope[]; error?: string };
	let undos = $state<Undo[]>([]);

	const errMsg = (e: unknown, fallback: string) => (e instanceof Error && e.message ? e.message : fallback);
	const emailHint = $derived(emailTouched ? emailProblem(email) : '');
	// Granting a role to someone who already has one REPLACES their role, so
	// say what changes before it happens — and point at Manage, which is the
	// direct way to change an existing member.
	const existing = $derived(res.data?.members.find((m) => m.email === email.trim().toLowerCase()) ?? null);
	const newLangs = $derived(choiceLangs(form, res.data?.languages ?? []));

	function labels(team: AdminTeam) {
		const lang = (code: string) => languageNames([code], team.language_names)[0] ?? localeName(code);
		const role = (code: string) => team.role_info.find((r) => r.code === code)?.label ?? code;
		return {
			lang,
			// "*" swallows the rest: a scope that includes all languages is all languages.
			langs: (codes: string[]) => (codes.length ? languageNames(codes, team.language_names).join(', ') : 'no languages'),
			role,
			roles: (m: TeamMember) => (m.roles.length ? m.roles.map(role).join(', ') : 'Individual permissions'),
			cap: (c: string) => team.capabilities.find(([v]) => v === c)?.[1] ?? c,
			// "Act (apply changes)" → "Act": the ladder word is enough in a list.
			verb: (v: string) => (team.verbs.find(([x]) => x === v)?.[1] ?? v).split(' (')[0]
		};
	}

	const initial = (addr: string) => addr.trim().charAt(0).toUpperCase() || '?';

	async function grant() {
		const addr = email.trim().toLowerCase();
		if (!addr) {
			formError = 'An email is required.';
			return;
		}
		const problem = emailProblem(addr);
		if (problem) {
			emailTouched = true;
			formError = problem;
			return;
		}
		if (!newLangs.length) {
			formError = 'Pick at least one language, or choose "All languages".';
			return;
		}
		granting = true;
		formError = '';
		try {
			await grantAdminAccess({ email: addr, role: form.role, languages: newLangs });
			email = '';
			emailTouched = false;
			form = freshChoice();
			await res.load();
		} catch (e) {
			formError = errMsg(e, 'Could not grant access.');
		} finally {
			granting = false;
		}
	}

	async function runForRow(addr: string, work: () => Promise<unknown>, failure: string) {
		busy = { ...busy, [addr]: true };
		rowError = { ...rowError, [addr]: '' };
		try {
			await work();
			await res.load();
			return true;
		} catch (e) {
			rowError = { ...rowError, [addr]: `${failure} ${errMsg(e, '')}`.trim() };
			return false;
		} finally {
			busy = { ...busy, [addr]: false };
		}
	}

	function openManage(m: TeamMember, role?: string) {
		if (editing?.email === m.email && !role) {
			editing = null;
			return;
		}
		// Prefill from the rows the save would replace (the role rows). When
		// they disagree on languages, prefill none: offering their union would
		// let an unchanged Save widen every permission to the widest scope.
		const roleRows = { ...m, scopes: m.scopes.filter((s) => s.role) };
		const shared = m.roles.length ? sharedLanguages(roleRows) : sharedLanguages(m);
		const langs = shared ?? [];
		editing = {
			email: m.email,
			mixed: !shared,
			pick: {
				role: role ?? m.roles[0] ?? 'contributor',
				all: langs.includes('*'),
				langs: Object.fromEntries(langs.filter((c) => c !== '*').map((c) => [c, true]))
			}
		};
	}

	async function saveManage(available: string[]) {
		if (!editing) return;
		const { email: addr, pick } = editing;
		const ok = await runForRow(
			addr,
			() => grantAdminAccess({ email: addr, role: pick.role, languages: choiceLangs(pick, available) }),
			`Couldn't save ${addr}'s changes.`
		);
		// Only close the panel that was saved — another may have been opened meanwhile.
		if (ok && editing?.email === addr) editing = null;
	}

	async function revoke(m: TeamMember) {
		confirming = { ...confirming, [m.email]: false };
		const ok = await runForRow(
			m.email,
			() => revokeAdminAccess(m.email),
			`Couldn't remove access, so ${m.email} still has it.`
		);
		if (ok) {
			if (editing?.email === m.email) editing = null;
			undos = [...undos.filter((u) => u.email !== m.email), { email: m.email, scopes: m.scopes }];
		}
	}

	async function undoRevoke(u: Undo) {
		const ok = await runForRow(
			u.email,
			() => grantAdminAccess({ email: u.email, restore: u.scopes }),
			`Couldn't restore ${u.email}'s access.`
		);
		// The member's row is gone, so a failure is reported on the Undo bar.
		undos = ok
			? undos.filter((x) => x !== u)
			: undos.map((x) => (x === u ? { ...x, error: rowError[u.email] } : x));
	}

	const updateRole = (addr: string, r: { role: string; languages: string[] | null }) =>
		runForRow(
			addr,
			() => grantAdminAccess({ email: addr, role: r.role, languages: r.languages ?? [] }),
			`Couldn't update ${addr}'s role.`
		);
</script>

<svelte:head><title>Admin · Team & access — Ochorus</title><meta name="robots" content="noindex" /></svelte:head>

<!-- Role cards + language chips, shared by the grant form and the Manage panel. -->
{#snippet picker(team: AdminTeam, L: ReturnType<typeof labels>, pick: RoleChoice, idPrefix: string)}
	<fieldset>
		<legend class="mb-2 text-small font-semibold text-text">
			Role <a href="/admin/help#roles" class="ms-1 font-normal text-accent hover:underline">Compare roles</a>
		</legend>
		<div class="grid gap-2 sm:grid-cols-3">
			{#each team.role_info as r (r.code)}
				<label class="flex cursor-pointer flex-col gap-1 rounded-card border p-3 text-small {pick.role === r.code ? 'border-accent bg-accent-soft' : 'border-border-strong hover:border-accent'}">
					<span class="flex items-center gap-2 font-semibold text-text">
						<input type="radio" id="{idPrefix}-role-{r.code}" name="{idPrefix}-role" value={r.code} checked={pick.role === r.code} onchange={() => (pick.role = r.code)} />
						{r.label}
					</span>
					<span class="text-muted">{r.summary}</span>
				</label>
			{/each}
		</div>
	</fieldset>

	<fieldset class="mt-4">
		<legend class="mb-2 text-small font-semibold text-text">Languages <span class="font-normal text-muted">· choose at least one</span></legend>
		<div class="flex flex-wrap gap-2">
			{#each team.languages as code (code)}
				<button
					type="button"
					disabled={pick.all}
					aria-pressed={pick.all || !!pick.langs[code]}
					onclick={() => (pick.langs = { ...pick.langs, [code]: !pick.langs[code] })}
					class="rounded-full border px-3 py-1 text-small disabled:opacity-60 {pick.all || pick.langs[code] ? 'border-accent bg-accent-soft font-semibold text-accent' : 'border-border-strong text-text hover:border-accent'}">{L.lang(code)}</button>
			{/each}
		</div>
		<label class="mt-3 flex items-center gap-2 text-small text-text">
			<input id="{idPrefix}-all-languages" type="checkbox" checked={pick.all} onchange={(e) => (pick.all = e.currentTarget.checked)} /> All languages, including ones added later
		</label>
	</fieldset>
{/snippet}

<div class="mx-auto max-w-4xl px-5 py-10">
	<a href="/admin" class="text-small text-accent hover:underline">← Back to dashboard</a>

	<AdminGate resource={res} errorTitle="Couldn't load the team" loadingText="Loading…" panelClass="mt-6">
		{#snippet children(team)}
			{@const L = labels(team)}
			{@const formRole = team.role_info.find((r) => r.code === form.role)}
			<header class="mb-6 mt-3">
				<p class="eyebrow mb-2 text-accent">Admin · Access</p>
				<h1 class="text-display">Team &amp; access</h1>
				<p class="mt-2 text-body text-muted">Grant scoped admin access to others. You (the super admin) keep everything; a grant only opens what you choose, in the languages you choose. Only super admins can see or change this.</p>
			</header>

			<!-- Grant form -->
			<section class="mb-8 rounded-card border border-border bg-surface p-5">
				<h2 class="mb-3 text-h3">Grant access</h2>
				<label class="mb-4 flex flex-col gap-1 text-small">
					<span class="font-semibold text-text">Email</span>
					<input id="grant-email" bind:value={email} onblur={() => (emailTouched = true)} type="email" placeholder="person@example.com" aria-invalid={!!emailHint} aria-describedby="grant-email-hint" class="w-full max-w-sm rounded border bg-bg px-2.5 py-1.5 text-body text-text {emailHint ? 'border-danger' : 'border-border-strong'}" />
					<span id="grant-email-hint" class="text-small text-danger">{emailHint}</span>
				</label>

				{@render picker(team, L, form, 'grant')}

				{#if existing}
					<div class="mt-4 rounded-card border border-warning bg-warning/10 px-4 py-3 text-small text-warning" role="status">
						{#if existing.roles.length}
							<p class="font-semibold">{existing.email} already has access. Granting will replace their role.</p>
							<p class="mt-1">Role: {L.roles(existing)} → {L.role(form.role)} · Languages: {L.langs(memberLanguages(existing, true))} → {L.langs(newLangs)}</p>
						{:else}
							<p class="font-semibold">{existing.email} already has individual permissions.</p>
							<p class="mt-1">Granting adds the {L.role(form.role)} role. Their individual permissions stay, except any the role also covers.</p>
						{/if}
					</div>
				{:else if team.super_admins.includes(email.trim().toLowerCase())}
					<p class="mt-4 rounded-card border border-warning bg-warning/10 px-4 py-3 text-small text-warning" role="status">{email.trim().toLowerCase()} is a super admin and already has full access. A grant adds nothing.</p>
				{:else if email.trim() && !emailProblem(email) && formRole && newLangs.length}
					<!-- Read the grant back as a sentence before it's made. -->
					<p class="mt-4 rounded-card border border-accent-soft-border bg-accent-soft px-4 py-3 text-small text-text" role="status">
						<b>{email.trim().toLowerCase()}</b> will be a <b>{formRole.label}</b> in <b>{L.langs(newLangs)}</b>. {formRole.summary}
					</p>
				{/if}

				<div class="mt-4 flex flex-wrap items-center gap-3">
					<button type="button" onclick={grant} disabled={granting} class="btn btn-sm rounded bg-accent px-3 py-1.5 text-small font-semibold text-white disabled:opacity-50">{granting ? 'Granting…' : existing ? 'Replace access' : `Grant ${L.role(form.role)}`}</button>
					{#if formError}<p class="text-small text-danger" role="alert">{formError}</p>{/if}
				</div>
			</section>

			<!-- Members -->
			<section class="mb-8">
				<h2 class="mb-3 text-h3">Granted access <span class="text-muted">· {team.members.length}</span></h2>
				{#each undos as u (u.email)}
					<div class="mb-3 flex flex-wrap items-center justify-between gap-3 rounded-card border border-border bg-surface-2 px-4 py-2.5 text-small text-text" role="status">
						<span>Removed {u.email}'s access.{#if u.error}<span class="block text-danger" role="alert">{u.error} Try Undo again.</span>{/if}</span>
						<span class="flex gap-3">
							<button type="button" onclick={() => undoRevoke(u)} disabled={busy[u.email]} class="font-semibold text-accent hover:underline disabled:opacity-50">Undo</button>
							<button type="button" onclick={() => (undos = undos.filter((x) => x !== u))} class="text-muted hover:text-text" aria-label="Dismiss">✕</button>
						</span>
					</div>
				{/each}
				{#if team.members.length}
					<ul class="divide-y divide-border rounded-card border border-border bg-surface">
						{#each team.members as m (m.email)}
							{@const shared = sharedLanguages(m)}
							<li class="px-4 py-3">
								<div class="flex items-start gap-3">
									<span class="grid h-8 w-8 shrink-0 place-items-center rounded-full bg-accent-soft text-small font-semibold text-accent" aria-hidden="true">{initial(m.email)}</span>
									<div class="min-w-0 flex-1">
										<span class="block break-all font-semibold text-text">{m.email}</span>
										<div class="mt-1 flex flex-wrap items-center gap-1.5">
											<span class="rounded-full bg-accent-soft px-2 py-0.5 text-micro font-semibold text-accent">{L.roles(m)}</span>
											{#each memberLanguages(m) as code (code)}
												<span class="rounded-full border border-border-strong px-2 py-0.5 text-micro text-text">{L.lang(code)}</span>
											{/each}
										</div>
									</div>
									<button type="button" onclick={() => openManage(m)} aria-expanded={editing?.email === m.email} disabled={busy[m.email]} class="shrink-0 rounded-full border border-border-strong px-3 py-0.5 text-small text-text hover:border-accent disabled:opacity-50">{busy[m.email] ? 'Working…' : editing?.email === m.email ? 'Close' : 'Manage'}</button>
								</div>

								<details class="ms-11 mt-2 text-small">
									<summary class="cursor-pointer text-muted hover:text-text">Permissions ({m.scopes.length}){#if shared}&nbsp;· {L.langs(shared)}{/if}</summary>
									<ul class="mt-1 grid gap-0.5 sm:grid-cols-2">
										{#each m.scopes as s (s.capability)}
											<li class="text-muted"><span class="text-text">{L.cap(s.capability)}</span> · {L.verb(s.verb)}{#if !shared}&nbsp;· {L.langs(s.languages)}{/if}</li>
										{/each}
									</ul>
								</details>

								{#each m.outdated as o (o.role)}
									<div class="ms-11 mt-3 flex flex-wrap items-center justify-between gap-3 rounded-card border border-warning bg-warning/10 px-3 py-2 text-small text-warning">
										<span>Out of date: the {L.role(o.role)} role has gained {o.missing.map(L.cap).join(' and ')} since this grant.{#if !o.languages}&nbsp;Its permissions have different languages, so choose the languages to update it with.{/if}</span>
										{#if o.languages}
											<button type="button" onclick={() => updateRole(m.email, o)} disabled={busy[m.email]} class="shrink-0 rounded bg-accent px-2.5 py-1 font-semibold text-white disabled:opacity-50">Update to current role</button>
										{:else}
											<button type="button" onclick={() => openManage(m, o.role)} disabled={busy[m.email]} class="shrink-0 rounded bg-accent px-2.5 py-1 font-semibold text-white disabled:opacity-50">Choose languages…</button>
										{/if}
									</div>
								{/each}

								{#if editing?.email === m.email}
									{@const changedLangs = choiceLangs(editing.pick, team.languages)}
									{@const rolesBefore = m.roles}
									{@const langsBefore = editing.mixed ? null : memberLanguages(m, m.roles.length > 0)}
									{@const roleChanges = rolesBefore.length !== 1 || rolesBefore[0] !== editing.pick.role}
									{@const langsChange = !langsBefore || langsBefore.join() !== [...changedLangs].sort().join()}
									<div class="ms-11 mt-3 rounded-card border border-border bg-bg p-4">
										{@render picker(team, L, editing.pick, `edit-${m.email}`)}
										{#if editing.mixed}
											<p class="mt-3 text-small text-muted">Their permissions currently have different languages. Choose the languages this role should cover; saving applies them to every permission in it.</p>
										{/if}
										{#if !m.roles.length}
											<p class="mt-3 text-small text-muted">Saving adds this role. Their individual permissions stay, except any the role also covers.</p>
										{:else if rolesBefore.length > 1}
											<p class="mt-3 text-small text-warning">They hold {L.roles(m)}. Saving keeps only {L.role(editing.pick.role)}.</p>
										{/if}
										{#if m.roles.length && (roleChanges || langsChange) && changedLangs.length}
											<p class="mt-3 rounded-card border border-warning bg-warning/10 px-3 py-2 text-small text-warning" role="status">
												{#if roleChanges}Role: {L.roles(m)} → {L.role(editing.pick.role)}. {L.role(editing.pick.role)} replaces the old role, so permissions it doesn't include are removed.{/if}
												{#if langsChange}Languages: {langsBefore ? L.langs(langsBefore) : 'mixed'} → {L.langs(changedLangs)}.{/if}
											</p>
										{/if}
										<div class="mt-4 flex flex-wrap items-center justify-between gap-3">
											<button type="button" onclick={() => (confirming = { ...confirming, [m.email]: true })} class="text-small text-danger hover:underline">Remove all access…</button>
											<span class="flex gap-2">
												<button type="button" onclick={() => (editing = null)} class="rounded border border-border-strong px-3 py-1 text-small text-text">Cancel</button>
												<button type="button" onclick={() => saveManage(team.languages)} disabled={busy[m.email] || !changedLangs.length} class="rounded bg-accent px-3 py-1 text-small font-semibold text-white disabled:opacity-50">Save as {L.role(editing.pick.role)}</button>
											</span>
										</div>
									</div>
								{/if}

								{#if confirming[m.email]}
									<div class="ms-11 mt-3 flex flex-wrap items-center justify-between gap-3 rounded-card border border-danger bg-danger/10 px-3 py-2 text-small text-danger" role="alert">
										<span>Remove all of {m.email}'s access ({L.roles(m)} in {L.langs(memberLanguages(m))})?</span>
										<span class="flex gap-2">
											<button type="button" onclick={() => (confirming = { ...confirming, [m.email]: false })} class="rounded border border-border-strong px-2.5 py-1 text-text">Cancel</button>
											<button type="button" onclick={() => revoke(m)} class="rounded bg-danger px-2.5 py-1 font-semibold text-white">Remove access</button>
										</span>
									</div>
								{/if}

								{#if rowError[m.email]}
									<p class="ms-11 mt-2 text-small text-danger" role="alert">{rowError[m.email]}</p>
								{/if}
							</li>
						{/each}
					</ul>
				{:else}
					<p class="rounded-card border border-border bg-surface p-5 text-body text-muted">No one has been granted access yet.</p>
				{/if}
			</section>

			<!-- Super admins (read-only) -->
			<section>
				<h2 class="mb-1 text-h3">Super admins</h2>
				<p class="mb-2 text-small text-muted">Full access, set in the deploy environment (<code class="text-text">ADMIN_EMAILS</code>) — not editable here, by design.</p>
				<ul class="flex flex-wrap gap-2">
					{#each team.super_admins as e (e)}
						<li class="rounded-full border border-border bg-surface-2 px-3 py-1 text-small text-text">{e}</li>
					{/each}
				</ul>
			</section>
		{/snippet}
	</AdminGate>
</div>
