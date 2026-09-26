"use client";

import Link from "next/link";

import { Button } from "@/components/ui/button";
import { useAuth } from "@/context/auth-context";

export function HeroCta() {
  const { user, isLoading } = useAuth();

  if (isLoading) {
    return <div className="h-11" aria-hidden />;
  }

  if (user) {
    return (
      <div className="mt-10 flex items-center justify-center gap-4">
        <Button asChild size="lg">
          <Link href="/dashboard">Go to Dashboard</Link>
        </Button>
      </div>
    );
  }

  return (
    <div className="mt-10 flex items-center justify-center gap-4">
      <Button asChild size="lg">
        <Link href="/login">Login</Link>
      </Button>
      <Button asChild size="lg" variant="outline">
        <Link href="/login?demo=1">Explore Demo</Link>
      </Button>
    </div>
  );
}
