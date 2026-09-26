"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { Loader2, Search } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import { api } from "@/lib/api";
import type { Company } from "@/types";

export function GlobalSearch() {
  const router = useRouter();
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<Company[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    if (debounceRef.current) clearTimeout(debounceRef.current);

    if (query.trim().length === 0) {
      setResults([]);
      setIsLoading(false);
      return;
    }

    setIsLoading(true);
    debounceRef.current = setTimeout(() => {
      api
        .get<Company[]>(`/api/stocks/search?q=${encodeURIComponent(query.trim())}`)
        .then(setResults)
        .finally(() => setIsLoading(false));
    }, 300);

    return () => {
      if (debounceRef.current) clearTimeout(debounceRef.current);
    };
  }, [query]);

  const handleSelect = (symbol: string) => {
    setOpen(false);
    setQuery("");
    setResults([]);
    router.push(`/stocks/${symbol}`);
  };

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild>
        <Button variant="ghost" size="icon" aria-label="Search stocks">
          <Search className="h-[1.1rem] w-[1.1rem]" />
        </Button>
      </PopoverTrigger>
      <PopoverContent align="end" className="w-80 p-2">
        <div className="relative">
          <Search className="absolute left-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-muted-foreground" />
          <Input
            autoFocus
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Search symbol, name or sector..."
            className="h-9 pl-8"
          />
        </div>
        <div className="mt-2 max-h-72 overflow-y-auto">
          {isLoading && (
            <div className="flex items-center justify-center py-4 text-muted-foreground">
              <Loader2 className="h-4 w-4 animate-spin" />
            </div>
          )}
          {!isLoading && query.trim().length > 0 && results.length === 0 && (
            <p className="px-2 py-4 text-center text-sm text-muted-foreground">No matches.</p>
          )}
          {!isLoading &&
            results.map((company) => (
              <button
                key={company.id}
                onClick={() => handleSelect(company.symbol)}
                className="flex w-full flex-col items-start rounded-md px-2 py-1.5 text-left text-sm hover:bg-accent"
              >
                <span className="font-medium">
                  {company.symbol} <span className="font-normal text-muted-foreground">&middot; {company.name}</span>
                </span>
                <span className="text-xs text-muted-foreground">{company.sector}</span>
              </button>
            ))}
        </div>
      </PopoverContent>
    </Popover>
  );
}
