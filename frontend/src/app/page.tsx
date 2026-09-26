import {
  BarChart3,
  Bot,
  Gauge,
  LineChart,
  ListChecks,
  Scale,
  Sparkles,
} from "lucide-react";

import { Navbar } from "@/components/layout/navbar";
import { Footer } from "@/components/layout/footer";
import { HeroCta } from "@/components/hero-cta";
import { TypewriterText } from "@/components/typewriter-text";
import { brand } from "@/config/brand";

const features = [
  {
    icon: Bot,
    title: "AI Research",
    description:
      "Ask questions in plain language and get structured, data-grounded research summaries - never guesses.",
  },
  {
    icon: BarChart3,
    title: "Financial Analysis",
    description: "Revenue, profit, margins and growth trends laid out clearly, annual and quarterly.",
  },
  {
    icon: LineChart,
    title: "Technical Analysis",
    description: "SMA, EMA, RSI, MACD and volatility, calculated directly from historical price data.",
  },
  {
    icon: Scale,
    title: "Stock Comparison",
    description: "Compare up to three companies side by side across fundamentals and momentum.",
  },
  {
    icon: ListChecks,
    title: "Watchlists",
    description: "Track the companies you're researching with live-refreshed key metrics.",
  },
  {
    icon: Gauge,
    title: "Stock Screener",
    description: "Filter the universe by sector, valuation, growth and AI research score.",
  },
];

export default function Home() {
  return (
    <div className="flex flex-1 flex-col">
      <Navbar />

      <main className="flex-1">
        <section className="relative overflow-hidden">
          <div
            aria-hidden
            className="pointer-events-none absolute inset-0 -z-10 bg-[radial-gradient(ellipse_at_top,_var(--tw-gradient-stops))] from-primary/10 via-transparent to-transparent"
          />
          <div className="mx-auto max-w-7xl px-4 py-24 sm:px-6 sm:py-32 lg:px-8">
            <div className="mx-auto max-w-3xl text-center">
              <span className="inline-flex items-center gap-1.5 rounded-full border bg-muted/50 px-3 py-1 text-xs font-medium text-muted-foreground">
                <Sparkles className="h-3.5 w-3.5" />
                Private beta &mdash; invite only
              </span>
              <h1 className="mt-6 text-4xl font-bold tracking-tight text-balance sm:text-6xl">
                <TypewriterText text={brand.tagline} />
              </h1>
              <p className="mt-6 text-lg leading-8 text-muted-foreground text-balance">
                {brand.description}
              </p>
              <HeroCta />
            </div>
          </div>
        </section>

        <section className="border-t bg-muted/20">
          <div className="mx-auto max-w-7xl px-4 py-20 sm:px-6 lg:px-8">
            <div className="mx-auto max-w-2xl text-center">
              <h2 className="text-3xl font-semibold tracking-tight">Everything you need to research a stock</h2>
              <p className="mt-4 text-muted-foreground">
                One workspace for fundamentals, technicals and AI-generated research context.
              </p>
            </div>
            <div className="mt-14 grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-3">
              {features.map((feature) => (
                <div
                  key={feature.title}
                  className="rounded-xl border bg-card p-6 shadow-sm transition-colors hover:border-primary/40"
                >
                  <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10 text-primary">
                    <feature.icon className="h-5 w-5" />
                  </div>
                  <h3 className="mt-4 font-semibold">{feature.title}</h3>
                  <p className="mt-2 text-sm text-muted-foreground">{feature.description}</p>
                </div>
              ))}
            </div>
          </div>
        </section>
      </main>

      <Footer />
    </div>
  );
}
