// Colour scheme choice (issue #28): light or dark, light by default. MUI stores the choice under STORAGE_KEY
// (its storage access is wrapped in try and catch, so blocked storage only means the choice is not
// remembered). index.html reads the same key before the app loads, so the first paint has the right
// background. Any other stored value, such as "system" from an earlier version, counts as light: the provider
// switches it to light before the first paint, and MUI stores that.

export const STORAGE_KEY = "salesmesh.colorMode";
export const SCHEME_STORAGE_KEY = "salesmesh.colorScheme";
export const MODES = ["light", "dark"];
export const MODE_LABELS = { light: "Light", dark: "Dark" };
export const DEFAULT_MODE = "light";

