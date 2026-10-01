<script lang="ts">
	import { adminResource } from '$lib/adminResource.svelte';
	import type { AdminScope } from '$lib/adminAccess';
	import { emailProblem, memberLanguages } from '$lib/adminTeam';
	import AdminGate from '$lib/components/AdminGate.svelte';
	import { localeName } from '$lib/lang.svelte';
	import { getAdminTeam, grantAdminAccess, revokeAdminAccess, type TeamMember } from '$lib/library-admin';

	const res = adminResource(getAdminTeam, 'Something went wrong loading the team.');

	// Grant form state. No language is chosen to start: the quickest path
	// through the form must not be the widest grant, and "all" also covers
	// every language added later.
	let email = $state('');
	let emailTouched = $state(false); // judge the address once typing pauses at blur, not per keystroke
	let role = $state('contributor');
	let allLanguages = $state(false);
	let langs = $state<Record<string, boolean>>({});
	let granting = $state(false);
	let formError = $state('');

	// Per-member row state, keyed by email.
	let busy = $state<Record<string, boolean>>({}); // a request in flight
	let confirming = $state<Record<string, boolean>>({}); // revoke asked, not yet confirmed
	let rowError = $state<Record<string, string>>({});
	// Recent revokes, each with the exact rows to put back. A list, so a second
	// revoke never takes away the first one's Undo.
	type Undo = { email: string; scopes: AdminScope[]; error?: string };
	let undos = $state<Undo[]>([]);

	const chosenLangs = (available: string[]) => available.filter((c) => langs[c]);
	const langLabel = (code: string) => (code === '*' ? 'All languages' : `${localeName(code)} (${code})`);
	const langList = (codes: string[]) => codes.map(langLabel).join(', ');
	const roleList = (m: TeamMember) => (m.roles.length ? m.roles.join(', ') : 'custom');
	const errMsg = (e: unknown, fallback: string) => (e instanceof Error && e.message ? e.message : fallback);

	const emailHint = $derived(emailTouched ? emailProblem(email) : '');
	// Granting a role to someone who already has one REPLACES their role, so
	// say what changes before it happens.
	const existing = $derived(res.data?.members.find((m) => m.email === email.trim().toLowerCase()) ?? null);
	const newLangs = $derived(allLanguages ? ['*'] : chosenLangs(res.data?.languages ?? []));

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
			await grantAdminAccess({ email: addr, role, languages: newLangs });
			email = '';
			emailTouched = false;
			langs = {};
			allLanguages = false;
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

	async function revoke(m: TeamMember) {
		confirming = { ...confirming, [m.email]: false };
		const ok = await runForRow(
			m.email,
			() => revokeAdminAccess(m.email),
			`Couldn't remove access, so ${m.email} still has it.`
		);
		if (ok) undos = [...undos.filter((u) => u.email !== m.email), { email: m.email, scopes: m.scopes }];
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

	const scopeLabel = (s: { capability: string; verb: string; languages: string[] }) =>
		`${s.capability}:${s.verb} · ${s.languages.join(', ')}`;
</script>

<svelte:head><title>Admin · Team & access — Ochorus</title><meta name="robots" content="noindex" /></svelte:head>

<div class="mx-auto max-w-4xl px-5 py-10">
	<a href="/admin" class="text-small text-accent hover:underline">← Back to dashboard</a>

	<AdminGate resource={res} errorTitle="Couldn't load the team" loadingText="Loading…" panelClass="mt-6">
		{#snippet children(team)}
			{@const capLabel = (c: string) => team.capabilities.find(([v]) => v === c)?.[1] ?? c}
			<header class="mb-6 mt-3">
				<p class="eyebrow mb-2 text-accent">Admin · Access</p>
				<h1 class="text-display">Team &amp; access</h1>
				<p class="mt-2 text-body text-muted">Grant scoped admin access to others. You (the super admin) keep everything; a grant only opens what you choose, in the languages you choose. Only super admins can see or change this.</p>
			</header>

			<!-- Grant form -->
			<section class="mb-8 rounded-card border border-border bg-surface p-5">
				<h2 class="mb-3 text-h3">Grant access</h2>
				<div class="flex flex-wrap items-start gap-3">
					<label class="flex flex-col gap-1 text-small">
						<span class="font-semibold text-text">Email</span>
						<input id="grant-email" bind:value={email} onblur={() => (emailTouched = true)} type="email" placeholder="person@example.com" aria-invalid={!!emailHint} aria-describedby="grant-email-hint" class="w-64 rounded border bg-bg px-2.5 py-1.5 text-body text-text {emailHint ? 'border-danger' : 'border-border-strong'}" />
						<span id="grant-email-hint" class="max-w-64 text-small text-danger">{emailHint}</span>
					</label>
					<label class="flex flex-col gap-1 text-small">
						<span class="font-semibold text-text">Role</span>
						<select id="grant-role" bind:value={role} class="rounded border border-border-strong bg-bg px-2.5 py-1.5 text-body text-text">
							{#each team.roles as r (r)}<option value={r}>{r}</option>{/each}
						</select>
					</label>
				</div>

				<fieldset class="mt-4">
					<legend class="mb-2 text-small font-semibold text-text">Languages <span class="font-normal text-muted">· choose at least one</span></legend>
					<div class="flex flex-wrap gap-2">
						{#each team.languages as code (code)}
							<button
								type="button"
								disabled={allLanguages}
								aria-pressed={allLanguages || !!langs[code]}
								onclick={() => (langs = { ...langs, [code]: !langs[code] })}
								class="rounded-full border px-3 py-1 text-small disabled:opacity-60 {allLanguages || langs[code] ? 'border-accent bg-accent-soft font-semibold text-accent' : 'border-border-strong text-text hover:border-accent'}">{langLabel(code)}</button>
						{/each}
					</div>
					<label class="mt-3 flex items-center gap-2 text-small text-text">
						<input id="grant-all-languages" type="checkbox" bind:checked={allLanguages} /> All languages, including ones added later
					</label>
				</fieldset>

				{#if existing}
					<div class="mt-4 rounded-card border border-warning bg-warning/10 px-4 py-3 text-small text-warning" role="status">
						{#if existing.roles.length}
							<p class="font-semibold">{existing.email} already has access. Granting will replace their role.</p>
							<p class="mt-1">Role: {existing.roles.join(', ')} → {role} · Languages: {langList(memberLanguages(existing, true))} → {newLangs.length ? langList(newLangs) : 'none chosen'}</p>
						{:else}
							<p class="font-semibold">{existing.email} already has individual permissions.</p>
							<p class="mt-1">Granting adds the {role} role. Their individual permissions stay, except any the role also covers.</p>
						{/if}
					</div>
				{/if}

				<div class="mt-4 flex flex-wrap items-center gap-3">
					<button type="button" onclick={grant} disabled={granting} class="btn btn-sm rounded bg-accent px-3 py-1.5 text-small font-semibold text-white disabled:opacity-50">{granting ? 'Granting…' : existing ? 'Replace access' : 'Grant'}</button>
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
							<li class="px-4 py-3">
								<div class="flex flex-wrap items-start justify-between gap-3">
									<div class="min-w-0">
										<span class="block font-semibold text-text">{m.email}</span>
										<span class="text-small text-muted">{roleList(m)}</span>
										<ul class="mt-1 flex flex-wrap gap-x-3 gap-y-0.5">
											{#each m.scopes as s (s.capability)}
												<li class="text-micro tabular-nums text-muted">{scopeLabel(s)}</li>
											{/each}
										</ul>
									</div>
									{#if !confirming[m.email]}
										<button type="button" onclick={() => (confirming = { ...confirming, [m.email]: true })} disabled={busy[m.email]} class="shrink-0 rounded-full border border-border-strong px-2.5 py-0.5 text-small text-muted hover:border-danger hover:text-danger disabled:opacity-50">{busy[m.email] ? 'Working…' : 'Revoke all'}</button>
									{/if}
								</div>

								{#each m.outdated as o (o.role)}
									<div class="mt-3 flex flex-wrap items-center justify-between gap-3 rounded-card border border-warning bg-warning/10 px-3 py-2 text-small text-warning">
										<span>Out of date: the {o.role} role has gained {o.missing.map(capLabel).join(' and ')} since this grant.{#if !o.languages}&nbsp;Its languages differ between permissions, so grant it again above to update.{/if}</span>
										{#if o.languages}
											<button type="button" onclick={() => updateRole(m.email, o)} disabled={busy[m.email]} class="shrink-0 rounded bg-accent px-2.5 py-1 font-semibold text-white disabled:opacity-50">Update to current role</button>
										{/if}
									</div>
								{/each}

								{#if confirming[m.email]}
									<div class="mt-3 flex flex-wrap items-center justify-between gap-3 rounded-card border border-danger bg-danger/10 px-3 py-2 text-small text-danger" role="alert">
										<span>Remove all of {m.email}'s access ({roleList(m)} in {langList(memberLanguages(m))})?</span>
										<span class="flex gap-2">
											<button type="button" onclick={() => (confirming = { ...confirming, [m.email]: false })} class="rounded border border-border-strong px-2.5 py-1 text-text">Cancel</button>
											<button type="button" onclick={() => revoke(m)} class="rounded bg-danger px-2.5 py-1 font-semibold text-white">Remove access</button>
										</span>
									</div>
								{/if}

								{#if rowError[m.email]}
									<p class="mt-2 text-small text-danger" role="alert">{rowError[m.email]}</p>
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
