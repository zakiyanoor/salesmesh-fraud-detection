/** Filter fields: full width on phones, a fixed width from sm up. */
export const filterWidth = (width) => ({ width: { xs: "100%", sm: width } });

export const visuallyHidden = {
  position: "absolute", width: 1, height: 1, p: 0, m: -1, overflow: "hidden", clip: "rect(0 0 0 0)", border: 0,
};
