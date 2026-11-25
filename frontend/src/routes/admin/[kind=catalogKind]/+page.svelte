<script lang="ts">
	import AdminCatalog from '$lib/components/admin/AdminCatalog.svelte';

	let { data } = $props();
</script>

<!-- Keyed, so moving between lists starts each with its own search box. -->
{#key data.kind}
	<AdminCatalog kind={data.kind} />
{/key}
