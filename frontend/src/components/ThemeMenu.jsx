import { useId, useState } from "react";
import { IconButton, ListItemIcon, ListItemText, Menu, MenuItem } from "@mui/material";
import { useColorScheme } from "@mui/material/styles";
import DarkModeOutlined from "@mui/icons-material/DarkModeOutlined";
import LightModeOutlined from "@mui/icons-material/LightModeOutlined";
import SettingsBrightnessOutlined from "@mui/icons-material/SettingsBrightnessOutlined";
import { MODES, MODE_LABELS } from "../colorMode/colorModeContext";

const ICONS = {
  system: <SettingsBrightnessOutlined fontSize="small" />,
  light: <LightModeOutlined fontSize="small" />,
  dark: <DarkModeOutlined fontSize="small" />,
};

/**
 * Theme choice (issue #28): System (follows the device), Light or Dark, remembered by the provider.
 * The button names the current choice; the menu marks it as checked.
 */
export default function ThemeMenu() {
  const { mode, systemMode, setMode } = useColorScheme();
  const current = mode || "system";
  const [anchor, setAnchor] = useState(null);
  const menuId = useId();
  const followed = current === "system" && systemMode ? `, now ${MODE_LABELS[systemMode].toLowerCase()}` : "";

  const choose = (next) => {
    setMode(next);
    setAnchor(null);
  };

  return (
    <>
      <IconButton
        size="small"
        aria-label={`Theme: ${MODE_LABELS[current]}${followed}`}
        aria-haspopup="menu"
        aria-controls={anchor ? menuId : undefined}
        aria-expanded={anchor ? "true" : undefined}
        onClick={(e) => setAnchor(e.currentTarget)}
      >
        {ICONS[current]}
      </IconButton>
      <Menu id={menuId} anchorEl={anchor} open={Boolean(anchor)} onClose={() => setAnchor(null)}>
        {MODES.map((m) => (
          <MenuItem key={m} role="menuitemradio" aria-checked={m === current} selected={m === current} onClick={() => choose(m)}>
            <ListItemIcon>{ICONS[m]}</ListItemIcon>
            <ListItemText>{MODE_LABELS[m]}</ListItemText>
          </MenuItem>
        ))}
      </Menu>
    </>
  );
}
