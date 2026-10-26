import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { ThemeProvider } from "@mui/material";
import { createAppTheme } from "../theme";
import RiskBadge from "./RiskBadge";

const renderBadge = (band) =>
  render(<ThemeProvider theme={createAppTheme()}><RiskBadge band={band} /></ThemeProvider>);

describe("RiskBadge", () => {
  it.each([["high", "High risk"], ["review", "Review"], ["low", "Low risk"], [null, "Not scored"]])(
    "%s shows a text label and an icon",
    (band, label) => {
      const { container } = renderBadge(band);
      expect(screen.getByText(label)).toBeInTheDocument();
      expect(container.querySelector("svg")).not.toBeNull();
    },
  );
});
