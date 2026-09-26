"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useState } from "react";
import { LineChart, Loader2 } from "lucide-react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { brand } from "@/config/brand";
import { useAuth } from "@/context/auth-context";
import { ApiError } from "@/lib/api";

function LoginForm() {
  const { login } = useAuth();
  const router = useRouter();
  const searchParams = useSearchParams();
  const isDemo = searchParams.get("demo") === "1";

  const [email, setEmail] = useState(isDemo ? "demo@example.com" : "");
  const [password, setPassword] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    setIsSubmitting(true);
    try {
      await login(email, password);
      const next = searchParams.get("next") ?? "/dashboard";
      router.push(next);
    } catch (error) {
      const message = error instanceof ApiError ? error.message : "Something went wrong. Please try again.";
      toast.error(message);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <Card className="w-full max-w-sm">
      <CardHeader className="items-center text-center">
        <span className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary text-primary-foreground">
          <LineChart className="h-5 w-5" />
        </span>
        <CardTitle className="mt-2 text-xl">Sign in to {brand.shortName}</CardTitle>
        <CardDescription>
          Private beta access. Ask your administrator if you don&apos;t have an account.
        </CardDescription>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="email">Email</Label>
            <Input
              id="email"
              type="email"
              autoComplete="email"
              required
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              placeholder="you@example.com"
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="password">Password</Label>
            <Input
              id="password"
              type="password"
              autoComplete="current-password"
              required
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              placeholder="••••••••"
            />
          </div>
          <Button type="submit" className="w-full" disabled={isSubmitting}>
            {isSubmitting && <Loader2 className="h-4 w-4 animate-spin" />}
            Sign in
          </Button>
        </form>
        {isDemo && (
          <p className="mt-4 rounded-md bg-muted p-3 text-xs text-muted-foreground">
            Demo email prefilled. The demo account password is issued by your administrator during
            local setup (see README).
          </p>
        )}
        <p className="mt-6 text-center text-xs text-muted-foreground">
          Don&apos;t have an account?{" "}
          <Link href="/register" className="font-medium text-foreground hover:underline">
            Register
          </Link>
        </p>
        <p className="mt-2 text-center text-xs text-muted-foreground">
          <Link href="/" className="hover:text-foreground">
            &larr; Back to home
          </Link>
        </p>
      </CardContent>
    </Card>
  );
}

export default function LoginPage() {
  return (
    <div className="flex flex-1 items-center justify-center bg-muted/20 px-4 py-16">
      <Suspense fallback={null}>
        <LoginForm />
      </Suspense>
    </div>
  );
}
