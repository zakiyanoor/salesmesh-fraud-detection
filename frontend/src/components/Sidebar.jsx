import { NavLink } from "react-router-dom";
import { Drawer, Box, Typography, Button, Divider, List, ListItem, ListItemButton, ListItemIcon, ListItemText } from "@mui/material";
import DashboardIcon from "@mui/icons-material/SpaceDashboardOutlined";
import FlagIcon from "@mui/icons-material/FlagOutlined";
import PeopleIcon from "@mui/icons-material/PeopleAltOutlined";
import ShieldIcon from "@mui/icons-material/ShieldOutlined";
import InsightsIcon from "@mui/icons-material/InsightsOutlined";
import HistoryIcon from "@mui/icons-material/HistoryOutlined";
import FactCheckIcon from "@mui/icons-material/FactCheckOutlined";
import ReceiptIcon from "@mui/icons-material/ReceiptLongOutlined";
import DownloadIcon from "@mui/icons-material/FileDownloadOutlined";
import ManageAccountsIcon from "@mui/icons-material/ManageAccountsOutlined";
import HelpIcon from "@mui/icons-material/HelpOutlineOutlined";
import ThemeMenu from "./ThemeMenu";
import { useAuth } from "../auth/authContext";
import { ROLE_LABELS, menuFor } from "../auth/roles";

export const DRAWER_WIDTH = 240;

const ICONS = {
  overview: <DashboardIcon />,
  flagged: <FlagIcon />,
  allAgents: <PeopleIcon />,
  threat: <ShieldIcon />,
  analytics: <InsightsIcon />,
  history: <HistoryIcon />,
  confirm: <FactCheckIcon />,
  audit: <ReceiptIcon />,
  reports: <DownloadIcon />,
  accounts: <ManageAccountsIcon />,
  howItWorks: <HelpIcon />,
};

/** Permanent from md up; below md a temporary drawer that closes after each choice. */
export default function Sidebar({ variant = "permanent", open = true, onClose, onNavigate }) {
  const { user, logout } = useAuth();

  return (
    <Drawer
      variant={variant}
      open={open}
      onClose={onClose}
      // The phone drawer is a modal dialog, so it needs a name of its own.
      slotProps={variant === "temporary" ? { paper: { "aria-label": "Menu" } } : undefined}
      sx={{
        width: variant === "permanent" ? DRAWER_WIDTH : undefined,
        flexShrink: 0,
        "& .MuiDrawer-paper": {
          width: DRAWER_WIDTH,
          maxWidth: "85vw",
          boxSizing: "border-box",
          bgcolor: "background.paper",
          borderRight: "1px solid",
          borderColor: "divider",
          p: 3,
        },
      }}
    >
      {/* The brand is the page banner on desktop; in the phone drawer the top bar already is. */}
      <Box component={variant === "permanent" ? "header" : "div"} sx={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", gap: 1, mb: 4 }}>
        <Box>
          <Typography variant="h6" component="p">SalesMesh</Typography>
          <Typography variant="caption" color="text.secondary" sx={{ display: "block" }}>
            Fraud Detection
          </Typography>
        </Box>
        {/* On phones the top bar has the theme menu; the drawer does not repeat it. */}
        {variant === "permanent" && <ThemeMenu />}
      </Box>
      <Box component="nav" aria-label="Main menu" sx={{ display: "flex", flexDirection: "column", flexGrow: 1 }}>

        <List sx={{ flexGrow: 1 }}>
          {menuFor(user?.role).map((item) => (
            <ListItem key={item.key} disablePadding>
              <ListItemButton
                component={NavLink}
                to={item.path}
                end={item.path === "/"}
                onClick={onNavigate}
                sx={{
                  borderRadius: 1,
                  mb: 0.5,
                  "&.active": { bgcolor: "action.selected", color: "primary.dark" },
                }}
              >
                <ListItemIcon sx={{ minWidth: 36, color: "inherit" }}>{ICONS[item.key]}</ListItemIcon>
                <ListItemText primary={item.label} slotProps={{ primary: { variant: "body2" } }} />
              </ListItemButton>
            </ListItem>
          ))}
        </List>

        <Box>
          <Divider sx={{ mb: 2 }} />
          <Typography variant="caption" color="text.secondary" sx={{ display: "block", overflowWrap: "anywhere" }}>
            Signed in as {user?.username}
          </Typography>
          <Typography variant="caption" color="text.secondary" sx={{ display: "block", mb: 1 }}>
            {ROLE_LABELS[user?.role] || user?.role}
          </Typography>
          <Button size="small" onClick={logout} sx={{ px: 0 }}>
            Sign out
          </Button>
        </Box>
      </Box>
    </Drawer>
  );
}
