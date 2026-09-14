<script lang="ts">
	import { adminResource } from '$lib/adminResource.svelte';
	import AdminGate from '$lib/components/AdminGate.svelte';
	import { getAdminTeam, grantAdminAccess, revokeAdminAccess } from '$lib/library-admin';

	const res = adminResource(getAdminTeam, 'Something went wrong loading the team.');

	// Grant form state.
	let email = $state('');
	let role = $state('contributor');
	let allLanguages = $state(true);
	let langs = $state<Record<string, boolean>>({});
	let granting = $state(false);
	let formError = $state('');
	let busy = $state<Record<string, boolean>>({}); // per-email revoke pending

	const chosenLangs = (available: string[]) => available.filter((c) => langs[c]);

	async function grant() {
		const addr = email.trim().toLowerCase();
		if (!addr) {
			formError = 'An email is required.';
			return;
		}
		if (!allLanguages && chosenLangs(res.data?.languages ?? []).length === 0) {
			formError = 'Pick at least one language, or choose "All languages".';
			return;
		}
		granting = true;
		formError = '';
		try {
			await grantAdminAccess({
				email: addr,
				role,
				languages: allLanguages ? ['*'] : chosenLangs(res.data?.languages ?? [])
			});
			email = '';
			await res.load();
		} catch (e) {
			formError = e instanceof Error ? e.message : 'Could not grant access.';
		} finally {
			granting = false;
		}
	}

	async function revoke(addr: string) {
		busy = { ...busy, [addr]: true };
		try {
			await revokeAdminAccess(addr);
			await res.load();
		} catch {
			/* leave the row; a reload will reflect reality */
		} finally {
			busy = { ...busy, [addr]: false };
		}
	}

	const scopeLabel = (s: { capability: string; verb: string; languages: string[] }) =>
		`${s.capability}:${s.verb} · ${s.languages.join(', ')}`;
</script>

<svelte:head><title>Admin · Team & access — Ochorus</title><meta name="robots" content="noindex" /></svelte:head>

<div class="mx-auto max-w-4xl px-5 py-10">
	<a href="/admin" class="text-small text-accent hover:underline">← Back to dashboard</a>

	<AdminGate resource={res} errorTitle="Couldn't load the team" loadingText="Loading…" panelClass="mt-6">
		{#snippet children(team)}
			<header class="mb-6 mt-3">
				<p class="eyebrow mb-2 text-accent">Admin · Access</p>
				<h1 class="text-display">Team &amp; access</h1>
				<p class="mt-2 text-body text-muted">Grant scoped admin access to others. You (the super admin) keep everything; a grant only opens what you choose, in the languages you choose. Only super admins can see or change this.</p>
			</header>

			<!-- Grant form -->
			<section class="mb-8 rounded-card border border-border bg-surface p-5">
				<h2 class="mb-3 text-h3">Grant access</h2>
				<div class="flex flex-wrap items-end gap-3">
					<label class="flex flex-col gap-1 text-small">
						<span class="font-semibold text-text">Email</span>
						<input bind:value={email} type="email" placeholder="person@example.com" class="w-64 rounded border border-border bg-bg px-2.5 py-1.5 text-body text-text" />
					</label>
					<label class="flex flex-col gap-1 text-small">
						<span class="font-semibold text-text">Role</span>
						<select bind:value={role} class="rounded border border-border bg-bg px-2.5 py-1.5 text-body text-text">
							{#each team.roles as r (r)}<option value={r}>{r}</option>{/each}
						</select>
					</label>
					<button type="button" onclick={grant} disabled={granting} class="btn btn-sm rounded bg-accent px-3 py-1.5 text-small font-semibold text-white disabled:opacity-50">{granting ? 'Granting…' : 'Grant'}</button>
				</div>
				<div class="mt-3">
					<label class="flex items-center gap-2 text-small text-text">
						<input type="checkbox" bind:checked={allLanguages} /> All languages
					</label>
					{#if !allLanguages}
						<div class="mt-2 flex flex-wrap gap-x-4 gap-y-1">
							{#each team.languages as code (code)}
								<label class="flex items-center gap-1.5 text-small text-muted">
									<input type="checkbox" checked={langs[code]} onchange={(e) => (langs = { ...langs, [code]: e.currentTarget.checked })} /> {code}
								</label>
							{/each}
						</div>
					{/if}
				</div>
				{#if formError}<p class="mt-2 text-small text-warning">{formError}</p>{/if}
			</section>

			<!-- Members -->
			<section class="mb-8">
				<h2 class="mb-3 text-h3">Granted access <span class="text-muted">· {team.members.length}</span></h2>
				{#if team.members.length}
					<ul class="divide-y divide-border rounded-card border border-border bg-surface">
						{#each team.members as m (m.email)}
							<li class="flex flex-wrap items-start justify-between gap-3 px-4 py-3">
								<div class="min-w-0">
									<span class="block font-semibold text-text">{m.email}</span>
									<span class="text-small text-muted">{m.roles.length ? m.roles.join(', ') : 'custom'}</span>
									<ul class="mt-1 flex flex-wrap gap-x-3 gap-y-0.5">
										{#each m.scopes as s (s.capability)}
											<li class="text-micro tabular-nums text-muted">{scopeLabel(s)}</li>
										{/each}
									</ul>
								</div>
								<button type="button" onclick={() => revoke(m.email)} disabled={busy[m.email]} class="shrink-0 rounded-full border border-border px-2.5 py-0.5 text-small text-muted hover:border-warning hover:text-warning disabled:opacity-50">{busy[m.email] ? 'Removing…' : 'Revoke all'}</button>
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
