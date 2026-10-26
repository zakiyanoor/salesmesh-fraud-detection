import { Navigate, useSearchParams } from "react-router-dom";
import { useAuth } from "./authContext";
import { safeTarget } from "./redirect";

/** /sign-in once signed in: open the remembered page if it is safe and the role may open it, else the home page. */
export default function AfterSignIn() {
  const [params] = useSearchParams();
  const { user } = useAuth();
  return <Navigate to={safeTarget(params.get("next"), user?.role)} replace />;
}
