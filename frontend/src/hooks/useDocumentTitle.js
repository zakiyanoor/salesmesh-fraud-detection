import { useEffect } from "react";

export const APP_NAME = "SalesMesh Fraud Detection";

export function useDocumentTitle(title) {
  useEffect(() => {
    document.title = title ? `${title} · ${APP_NAME}` : APP_NAME;
  }, [title]);
}
