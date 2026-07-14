/**
 * Barrel for the library API client. Split into the public reader surface
 * (`library-public`) and the admin-dashboard surface (`library-admin`) so
 * reader code doesn't pull in the admin types; both re-exported here so every
 * `import … from '$lib/library'` call site is unchanged.
 */
export * from './library-public';
export * from './library-admin';
