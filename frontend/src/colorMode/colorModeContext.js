// Colour scheme choice (issue #28): light, dark or the device's setting. MUI stores the choice under
// STORAGE_KEY (its storage access is wrapped in try and catch, so blocked storage only means the choice is
// not remembered). index.html reads the same key before the app loads, so the first paint has the right
// background.

export const STORAGE_KEY = "salesmesh.colorMode";
export const SCHEME_STORAGE_KEY = "salesmesh.colorScheme";
export const MODES = ["system", "light", "dark"];
export const MODE_LABELS = { system: "System", light: "Light", dark: "Dark" };
