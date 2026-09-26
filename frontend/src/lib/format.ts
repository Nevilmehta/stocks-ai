/** Formatting helpers for Indian-style currency (Rs. Lakh/Crore) and percentages. */

export function formatCrore(valueInCrore: number | null | undefined): string {
  if (valueInCrore === null || valueInCrore === undefined || Number.isNaN(valueInCrore)) {
    return "Data unavailable";
  }

  const absValue = Math.abs(valueInCrore);
  if (absValue >= 1_00_000) {
    return `Rs. ${(valueInCrore / 1_00_000).toFixed(2)} Lakh Cr`;
  }
  if (absValue >= 1) {
    return `Rs. ${valueInCrore.toFixed(2)} Cr`;
  }
  // Values below 1 Cr are shown in Lakh (1 Cr = 100 Lakh).
  return `Rs. ${(valueInCrore * 100).toFixed(2)} Lakh`;
}

export function formatPrice(value: number | null | undefined): string {
  if (value === null || value === undefined || Number.isNaN(value)) return "Data unavailable";
  return `Rs. ${value.toLocaleString("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

export function formatPercent(value: number | null | undefined, digits = 2): string {
  if (value === null || value === undefined || Number.isNaN(value)) return "Data unavailable";
  const sign = value > 0 ? "+" : "";
  return `${sign}${value.toFixed(digits)}%`;
}

export function formatNumber(value: number | null | undefined, digits = 2): string {
  if (value === null || value === undefined || Number.isNaN(value)) return "Data unavailable";
  return value.toFixed(digits);
}

export function formatCompactVolume(value: number | null | undefined): string {
  if (value === null || value === undefined || Number.isNaN(value)) return "Data unavailable";
  return new Intl.NumberFormat("en-IN", { notation: "compact", maximumFractionDigits: 1 }).format(value);
}

export function formatDate(value: string | null | undefined): string {
  if (!value) return "unavailable";
  return new Date(value).toLocaleDateString("en-IN", { day: "numeric", month: "short", year: "numeric" });
}
