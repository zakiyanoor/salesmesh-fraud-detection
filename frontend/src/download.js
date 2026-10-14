/** Saves a downloaded file under the server's file name, through a temporary object URL. */
export function saveFile({ blob, filename }) {
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  link.rel = "noopener";
  document.body.appendChild(link);
  link.click();
  link.remove();
  // Revoke after the click has been handled, so the browser can start the download.
  setTimeout(() => URL.revokeObjectURL(url), 0);
}
