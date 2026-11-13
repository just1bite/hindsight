"use client";

import { Suspense, useState, FormEvent, useEffect } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import { useTranslations } from "next-intl";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardDescription, CardHeader } from "@/components/ui/card";
import { LanguageSwitcher } from "@/components/language-switcher";
import { sanitizeReturnTo, withBasePath } from "@/lib/base-path";
import Image from "next/image";

function LoginForm() {
  const t = useTranslations("login");
  const [username, setUsername] = useState("admin");
  const [password, setPassword] = useState("");
  const [key, setKey] = useState("");
  const [useAccessKey, setUseAccessKey] = useState(false);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const router = useRouter();
  const searchParams = useSearchParams();

  // Validate returnTo to prevent open-redirect via crafted login links.
  const returnTo = sanitizeReturnTo(searchParams.get("returnTo"));

  useEffect(() => {
    // Focus the primary input on mount
    const input = document.getElementById(useAccessKey ? "access-key" : "password");
    input?.focus();
  }, [useAccessKey]);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError("");
    setLoading(true);

    try {
      const payload = useAccessKey ? { key } : { username, password, key: password };

      const res = await fetch(withBasePath("/api/auth/login"), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      if (res.ok) {
        // Navigate to the returnTo URL
        router.push(returnTo);
        router.refresh();
      } else {
        const data = await res.json().catch(() => null);
        setError(data?.error || t("invalidKey"));
      }
    } catch {
      setError(t("connectFailed"));
    } finally {
      setLoading(false);
    }
  }

  const isSubmitDisabled = loading || (useAccessKey ? !key : !password);

  return (
    <div className="min-h-screen bg-background flex items-center justify-center p-4">
      <div className="absolute top-4 right-4">
        <LanguageSwitcher />
      </div>
      <Card className="w-full max-w-md">
        <CardHeader className="text-center">
          <Image
            src={withBasePath("/logo.png")}
            alt="Hindsight"
            width={160}
            height={160}
            className="mx-auto"
            unoptimized
          />
          <CardDescription>{t("description")}</CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-4">
            {useAccessKey ? (
              <div>
                <Input
                  id="access-key"
                  type="password"
                  placeholder={t("accessKeyPlaceholder")}
                  value={key}
                  onChange={(e) => setKey(e.target.value)}
                  autoComplete="off"
                />
              </div>
            ) : (
              <>
                <div>
                  <Input
                    id="username"
                    type="text"
                    placeholder={t("usernamePlaceholder")}
                    value={username}
                    onChange={(e) => setUsername(e.target.value)}
                    autoComplete="username"
                  />
                </div>
                <div>
                  <Input
                    id="password"
                    type="password"
                    placeholder={t("passwordPlaceholder")}
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    autoComplete="current-password"
                  />
                </div>
              </>
            )}

            {error && <p className="text-sm text-red-600 dark:text-red-400">{error}</p>}

            <Button type="submit" className="w-full" disabled={isSubmitDisabled}>
              {loading ? t("signingIn") : t("signIn")}
            </Button>

            <div className="text-center pt-2">
              <button
                type="button"
                onClick={() => {
                  setError("");
                  setUseAccessKey(!useAccessKey);
                }}
                className="text-xs text-muted-foreground hover:text-foreground underline underline-offset-4 cursor-pointer"
              >
                {useAccessKey ? t("username") : t("accessKey")}
              </button>
            </div>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}

export default function LoginPage() {
  return (
    <Suspense>
      <LoginForm />
    </Suspense>
  );
}
