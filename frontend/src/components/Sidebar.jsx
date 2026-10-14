import { NavLink } from "react-router-dom";
import { Drawer, Box, Typography, Button, Divider, List, ListItemButton, ListItemIcon, ListItemText } from "@mui/material";
import DashboardIcon from "@mui/icons-material/SpaceDashboardOutlined";
import PeopleIcon from "@mui/icons-material/PeopleAltOutlined";
import InsightsIcon from "@mui/icons-material/InsightsOutlined";
import HistoryIcon from "@mui/icons-material/HistoryOutlined";
import ColorModeToggle from "./ColorModeToggle";
import { api } from "../api";

export const DRAWER_WIDTH = 240;

const NAV_ITEMS = [
  { label: "Flagged Agents", path: "/", icon: <DashboardIcon /> },
  { label: "All Agents", path: "/all-agents", icon: <PeopleIcon /> },
  { label: "Analytics", path: "/analytics", icon: <InsightsIcon /> },
  { label: "Review History", path: "/history", icon: <HistoryIcon /> },
];

export default function Sidebar({ username, onLogout }) {
  const handleLogout = async () => {
    await api.logout();
    onLogout();
  };

  return (
    <Drawer
      variant="permanent"
      sx={{
        width: DRAWER_WIDTH,
        flexShrink: 0,
        "& .MuiDrawer-paper": {
          width: DRAWER_WIDTH,
          bgcolor: "background.paper",
          borderRight: "1px solid",
          borderColor: "divider",
          p: 3,
          display: "flex",
        },
      }}
    >
      <Typography variant="h6">SalesMesh</Typography>
      <Typography variant="caption" color="text.secondary" sx={{ display: "block", mb: 4 }}>
        Fraud Detection
      </Typography>

      <List sx={{ flexGrow: 1 }}>
        {NAV_ITEMS.map((item) => (
          <ListItemButton
            key={item.path}
            component={NavLink}
            to={item.path}
            end={item.path === "/"}
            sx={{
              borderRadius: 1,
              mb: 0.5,
              "&.active": { bgcolor: "action.selected", color: "primary.dark" },
            }}
          >
            <ListItemIcon sx={{ minWidth: 36, color: "inherit" }}>{item.icon}</ListItemIcon>
            <ListItemText primary={item.label} primaryTypographyProps={{ variant: "body2" }} />
          </ListItemButton>
        ))}
      </List>

      <Box>
        <Divider sx={{ mb: 2 }} />
        <Typography variant="caption" color="text.secondary" sx={{ display: "block", mb: 1 }}>
          Signed in as {username}
        </Typography>
        <Box sx={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
          <Button size="small" onClick={handleLogout} sx={{ px: 0 }}>
            Sign out
          </Button>
          <ColorModeToggle />
        </Box>
      </Box>
    </Drawer>
  );
}