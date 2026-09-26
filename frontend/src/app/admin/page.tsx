"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import {
  Activity,
  AlertTriangle,
  BarChart3,
  CheckCircle2,
  ExternalLink,
  Loader2,
  MessageSquareText,
  ShieldAlert,
  Upload,
  UserPlus,
  Users,
} from "lucide-react";
import { toast } from "sonner";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Navbar } from "@/components/layout/navbar";
import { Footer } from "@/components/layout/footer";
import { StrategySettingsSection } from "@/components/strategy-settings";
import { useAuth } from "@/context/auth-context";
import { ApiError, api } from "@/lib/api";
import type { AdminAnalytics, MarketDataUploadResponse, SyncHistoryResponse, User, UserRole } from "@/types";

function CreateUserForm({ onCreated }: { onCreated: (user: User) => void }) {
  const [email, setEmail] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [password, setPassword] = useState("");
  const [role, setRole] = useState<UserRole>("user");
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    setIsSubmitting(true);
    try {
      const user = await api.post<User>("/api/admin/users", {
        email,
        password,
        display_name: displayName,
        role,
      });
      toast.success(`Invited ${user.email}`);
      onCreated(user);
      setEmail("");
      setDisplayName("");
      setPassword("");
      setRole("user");
    } catch (error) {
      toast.error(error instanceof ApiError ? error.message : "Could not create user.");
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-5 lg:items-end">
      <div className="space-y-2">
        <Label htmlFor="new-email">Email</Label>
        <Input id="new-email" type="email" required value={email} onChange={(e) => setEmail(e.target.value)} />
      </div>
      <div className="space-y-2">
        <Label htmlFor="new-name">Display name</Label>
        <Input id="new-name" required value={displayName} onChange={(e) => setDisplayName(e.target.value)} />
      </div>
      <div className="space-y-2">
        <Label htmlFor="new-password">Temporary password</Label>
        <Input
          id="new-password"
          type="text"
          required
          minLength={8}
          value={password}
          onChange={(e) => setPassword(e.target.value)}
        />
      </div>
      <div className="space-y-2">
        <Label htmlFor="new-role">Role</Label>
        <Select value={role} onValueChange={(value) => setRole(value as UserRole)}>
          <SelectTrigger id="new-role" className="w-full">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="user">User</SelectItem>
            <SelectItem value="admin">Admin</SelectItem>
          </SelectContent>
        </Select>
      </div>
      <Button type="submit" disabled={isSubmitting} className="gap-2">
        {isSubmitting ? <Loader2 className="h-4 w-4 animate-spin" /> : <UserPlus className="h-4 w-4" />}
        Create user
      </Button>
    </form>
  );
}

function AnalyticsSection() {
  const [analytics, setAnalytics] = useState<AdminAnalytics | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    api
      .get<AdminAnalytics>("/api/admin/analytics")
      .then(setAnalytics)
      .catch(() => toast.error("Failed to load analytics."))
      .finally(() => setIsLoading(false));
  }, []);

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="flex items-center gap-1.5 text-sm font-medium text-muted-foreground">
              <Users className="h-3.5 w-3.5" /> Users
            </CardTitle>
          </CardHeader>
          <CardContent className="text-3xl font-semibold">
            {isLoading ? <Skeleton className="h-9 w-14" /> : analytics?.total_users}
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="flex items-center gap-1.5 text-sm font-medium text-muted-foreground">
              <Activity className="h-3.5 w-3.5" /> Active users
            </CardTitle>
          </CardHeader>
          <CardContent className="text-3xl font-semibold">
            {isLoading ? <Skeleton className="h-9 w-14" /> : analytics?.active_users}
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="flex items-center gap-1.5 text-sm font-medium text-muted-foreground">
              <BarChart3 className="h-3.5 w-3.5" /> Research sessions
            </CardTitle>
          </CardHeader>
          <CardContent className="text-3xl font-semibold">
            {isLoading ? <Skeleton className="h-9 w-14" /> : analytics?.total_research_sessions}
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="flex items-center gap-1.5 text-sm font-medium text-muted-foreground">
              <MessageSquareText className="h-3.5 w-3.5" /> Research messages
            </CardTitle>
          </CardHeader>
          <CardContent className="text-3xl font-semibold">
            {isLoading ? <Skeleton className="h-9 w-14" /> : analytics?.total_research_messages}
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Most researched stocks</CardTitle>
          <CardDescription>Companies mentioned most often across all users&apos; AI Analyse and chat prompts.</CardDescription>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="space-y-2">
              {Array.from({ length: 3 }).map((_, i) => (
                <Skeleton key={i} className="h-9 w-full" />
              ))}
            </div>
          ) : !analytics || analytics.most_researched.length === 0 ? (
            <p className="text-sm text-muted-foreground">No research activity yet.</p>
          ) : (
            <div className="space-y-1">
              {analytics.most_researched.map((stock, index) => (
                <Link
                  key={stock.symbol}
                  href={`/stocks/${stock.symbol}`}
                  className="flex items-center justify-between rounded-md px-2 py-2 text-sm hover:bg-accent"
                >
                  <span className="flex items-center gap-3">
                    <span className="w-4 text-muted-foreground">{index + 1}</span>
                    <span className="font-medium">{stock.symbol}</span>
                    <span className="text-muted-foreground">{stock.name}</span>
                  </span>
                  <Badge variant="secondary">
                    {stock.mention_count} mention{stock.mention_count === 1 ? "" : "s"}
                  </Badge>
                </Link>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

function MarketDataSyncSection() {
  const [history, setHistory] = useState<SyncHistoryResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isUploading, setIsUploading] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const loadHistory = () => {
    api
      .get<SyncHistoryResponse>("/api/admin/market-data/sync-history")
      .then(setHistory)
      .catch(() => toast.error("Failed to load sync history."))
      .finally(() => setIsLoading(false));
  };

  useEffect(() => {
    loadHistory();
  }, []);

  const handleUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const files = event.target.files;
    if (!files || files.length === 0) return;

    setIsUploading(true);
    try {
      const formData = new FormData();
      Array.from(files).forEach((file) => formData.append("files", file));

      const response = await api.postForm<MarketDataUploadResponse>("/api/admin/market-data/upload", formData);

      for (const result of response.results) {
        if (result.error) {
          toast.error(`${result.filename}: ${result.error}`);
        } else {
          toast.success(`${result.filename}: ${result.rows_synced} companies synced for ${result.trade_date}`);
        }
      }
      loadHistory();
    } catch (error) {
      toast.error(error instanceof ApiError ? error.message : "Upload failed.");
    } finally {
      setIsUploading(false);
      if (fileInputRef.current) fileInputRef.current.value = "";
    }
  };

  const lastSync = history?.last_sync ?? null;
  const lastSyncFailed = lastSync?.status === "failure";

  return (
    <Card>
      <CardHeader>
        <CardTitle>Market data sync</CardTitle>
        <CardDescription>
          Automatic NSE sync runs daily at 8 PM IST. Use this if it ever fails or you need to backfill a
          missing trading day.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {isLoading ? (
          <Skeleton className="h-9 w-64" />
        ) : lastSync ? (
          <div
            className={
              "flex flex-wrap items-center gap-2 rounded-md border px-3 py-2 text-sm " +
              (lastSyncFailed
                ? "border-amber-500/30 bg-amber-500/10 text-amber-700 dark:text-amber-400"
                : "border-emerald-500/30 bg-emerald-500/10 text-emerald-700 dark:text-emerald-400")
            }
          >
            {lastSyncFailed ? <AlertTriangle className="h-4 w-4" /> : <CheckCircle2 className="h-4 w-4" />}
            {lastSyncFailed ? (
              <span>
                Automatic sync last <strong>failed</strong> for {lastSync.trade_date}
                {lastSync.error_message ? `: ${lastSync.error_message}` : ""}. Upload the bhavcopy manually
                below.
              </span>
            ) : (
              <span>
                Last successful sync: <strong>{lastSync.trade_date}</strong> ({lastSync.rows_synced}{" "}
                companies, via {lastSync.source.replace("_", " ")})
              </span>
            )}
          </div>
        ) : (
          <p className="text-sm text-muted-foreground">No sync has run yet.</p>
        )}

        <div className="flex flex-wrap items-center gap-3">
          <Button asChild variant="outline" size="sm" className="gap-1.5">
            <a href="https://www.nseindia.com/all-reports" target="_blank" rel="noreferrer">
              <ExternalLink className="h-3.5 w-3.5" /> Download official NSE Bhavcopy
            </a>
          </Button>
          <Button
            size="sm"
            className="gap-1.5"
            disabled={isUploading}
            onClick={() => fileInputRef.current?.click()}
          >
            {isUploading ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Upload className="h-3.5 w-3.5" />}
            Upload Bhavcopy ZIP(s)
          </Button>
          <input
            ref={fileInputRef}
            type="file"
            accept=".zip"
            multiple
            className="hidden"
            onChange={handleUpload}
          />
        </div>
        <p className="text-xs text-muted-foreground">
          Upload the official ZIP file(s) exactly as downloaded from NSE - the trading day is read from the
          filename automatically. You can select multiple files to backfill several missing days at once.
        </p>

        {history && history.history.length > 0 && (
          <div className="overflow-x-auto pt-2">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Date</TableHead>
                  <TableHead>Source</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead className="text-right">Rows</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {history.history.map((entry, i) => (
                  <TableRow key={i}>
                    <TableCell>{entry.trade_date}</TableCell>
                    <TableCell className="capitalize text-muted-foreground">
                      {entry.source.replace("_", " ")}
                    </TableCell>
                    <TableCell>
                      <Badge variant={entry.status === "success" ? "secondary" : "destructive"}>
                        {entry.status}
                      </Badge>
                    </TableCell>
                    <TableCell className="text-right tabular-nums">{entry.rows_synced}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

function AdminUsersPage() {
  const [users, setUsers] = useState<User[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [updatingId, setUpdatingId] = useState<string | null>(null);

  useEffect(() => {
    api
      .get<User[]>("/api/admin/users")
      .then(setUsers)
      .catch((error) => toast.error(error instanceof ApiError ? error.message : "Failed to load users."))
      .finally(() => setIsLoading(false));
  }, []);

  const toggleActive = async (user: User) => {
    setUpdatingId(user.id);
    try {
      const updated = await api.patch<User>(`/api/admin/users/${user.id}`, {
        is_active: !user.is_active,
      });
      setUsers((prev) => prev.map((u) => (u.id === updated.id ? updated : u)));
    } catch (error) {
      toast.error(error instanceof ApiError ? error.message : "Failed to update user.");
    } finally {
      setUpdatingId(null);
    }
  };

  return (
    <div className="flex flex-1 flex-col">
      <Navbar />
      <main className="flex-1 bg-muted/20">
        <div className="mx-auto max-w-6xl space-y-8 px-4 py-10 sm:px-6 lg:px-8">
          <div>
            <h1 className="text-2xl font-semibold tracking-tight">Admin</h1>
            <p className="mt-1 text-sm text-muted-foreground">
              Manage who can access this private beta. There is no public signup.
            </p>
          </div>

          <AnalyticsSection />

          <MarketDataSyncSection />

          <StrategySettingsSection />

          <Card>
            <CardHeader>
              <CardTitle>Invite a user</CardTitle>
              <CardDescription>They can sign in immediately with the temporary password.</CardDescription>
            </CardHeader>
            <CardContent>
              <CreateUserForm onCreated={(user) => setUsers((prev) => [user, ...prev])} />
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Users ({users.length})</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="overflow-x-auto">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Email</TableHead>
                      <TableHead>Name</TableHead>
                      <TableHead>Role</TableHead>
                      <TableHead>Status</TableHead>
                      <TableHead className="text-right">Action</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {isLoading ? (
                      <TableRow>
                        <TableCell colSpan={5} className="text-center text-muted-foreground">
                          Loading...
                        </TableCell>
                      </TableRow>
                    ) : (
                      users.map((user) => (
                        <TableRow key={user.id}>
                          <TableCell className="font-medium">{user.email}</TableCell>
                          <TableCell>{user.display_name}</TableCell>
                          <TableCell>
                            <Badge variant={user.role === "admin" ? "default" : "secondary"}>{user.role}</Badge>
                          </TableCell>
                          <TableCell>
                            <Badge variant={user.is_active ? "secondary" : "destructive"}>
                              {user.is_active ? "Active" : "Deactivated"}
                            </Badge>
                          </TableCell>
                          <TableCell className="text-right">
                            <Button
                              size="sm"
                              variant="outline"
                              disabled={updatingId === user.id}
                              onClick={() => toggleActive(user)}
                            >
                              {updatingId === user.id && <Loader2 className="h-3.5 w-3.5 animate-spin" />}
                              {user.is_active ? "Deactivate" : "Activate"}
                            </Button>
                          </TableCell>
                        </TableRow>
                      ))
                    )}
                  </TableBody>
                </Table>
              </div>
            </CardContent>
          </Card>
        </div>
      </main>
      <Footer />
    </div>
  );
}

export default function AdminPage() {
  const { user, isLoading } = useAuth();

  if (isLoading) return null;

  if (!user || user.role !== "admin") {
    return (
      <div className="flex flex-1 flex-col">
        <Navbar />
        <main className="flex flex-1 items-center justify-center bg-muted/20 px-4">
          <Card className="max-w-md text-center">
            <CardHeader className="items-center">
              <ShieldAlert className="h-8 w-8 text-destructive" />
              <CardTitle>Admin access required</CardTitle>
              <CardDescription>You don&apos;t have permission to view this page.</CardDescription>
            </CardHeader>
          </Card>
        </main>
        <Footer />
      </div>
    );
  }

  return <AdminUsersPage />;
}
