/**
 * Test setup for the offline module.
 *
 * jsdom does not implement IndexedDB, so the `fake-indexeddb` shim provides
 * a spec-compliant implementation for the duration of the test run. It is
 * a dev-only dependency and never ships to the browser.
 */

import 'fake-indexeddb/auto'
