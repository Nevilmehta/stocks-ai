/**
 * Centralized branding configuration.
 *
 * Nothing else in the app should hardcode the product name, tagline, or
 * legal text - import from here instead, so a rename only touches this file.
 */
export const brand = {
  productName: "StockAI",
  shortName: "StockAI",
  tagline: "Research Indian Stocks Smarter.",
  description:
    "Financials, technical indicators and AI-powered analysis in one research platform.",
  logoPath: "/logo.svg",
  supportEmail: "support@example.com",
  footerText: "StockAI is a private research platform. Not investment advice.",
  disclaimer:
    "This platform is intended for informational, educational and research purposes only. " +
    "It does not constitute personalized investment advice. Market investments involve risk. " +
    "Users should independently verify information before making financial decisions.",
} as const;

export type Brand = typeof brand;
