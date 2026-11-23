import { Navigate } from "react-router-dom";
import { DEFAULT_PATH } from "./redirect";

/** /sign-in once signed in: open the home page. */
export default function AfterSignIn() {
  return <Navigate to={DEFAULT_PATH} replace />;
}
