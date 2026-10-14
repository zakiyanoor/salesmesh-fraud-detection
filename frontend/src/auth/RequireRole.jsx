import { Navigate, useLocation } from "react-router-dom";
import { useAuth } from "./authContext";

export default function RequireRole({ roles, children }) {
  const { user } = useAuth();
  const location = useLocation();
  if (!roles.includes(user?.role)) return <Navigate to="/403" replace state={{ from: location.pathname }} />;
  return children;
}
