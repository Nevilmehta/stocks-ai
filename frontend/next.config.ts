import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // The dev-mode floating indicator (route/compile status) only offers
  // position or full on/off, no size control - disabled since it overlaps
  // page content. Compile errors still show in the terminal.
  devIndicators: false,
};

export default nextConfig;
