import { NextRequest, NextResponse } from "next/server";
import { localizeApiErrorPayload } from "@/lib/i18n/api-errors";

import {
  ACCESS_KEY_COOKIE,
  SESSION_MAX_AGE_SECONDS,
  createSessionToken,
  sessionCookieOptions,
} from "@/lib/auth/session";

// ponytail: single admin user from env; upgrade path: database-backed users table with RBAC.
export async function POST(request: NextRequest) {
  const adminUser = process.env.AUTH_USERNAME || process.env.HINDSIGHT_AUTH_USERNAME || "admin";
  const adminPassword =
    process.env.AUTH_PASSWORD ||
    process.env.HINDSIGHT_AUTH_PASSWORD ||
    process.env.HINDSIGHT_CP_ACCESS_KEY;
  const accessKey =
    process.env.HINDSIGHT_CP_ACCESS_KEY || adminPassword || process.env.AUTH_SECRET_KEY;

  // If no auth is configured, return 503
  if (!accessKey && !adminPassword) {
    return NextResponse.json(
      localizeApiErrorPayload(request, {
        error: "Access key not configured",
        errorKey: "api.errors.auth.accessKeyNotConfigured",
      }),
      { status: 503 }
    );
  }

  let body: { key?: string; username?: string; password?: string };
  try {
    body = await request.json();
  } catch {
    return NextResponse.json(
      localizeApiErrorPayload(request, {
        error: "Invalid request body",
        errorKey: "api.errors.auth.invalidRequestBody",
      }),
      { status: 400 }
    );
  }

  let isValid = false;

  // 1. Check username + password if provided
  if (body.username && body.password && adminPassword) {
    isValid =
      constantTimeCompare(body.username, adminUser) &&
      constantTimeCompare(body.password, adminPassword);
  }

  // 2. Fall back to key comparison (or password as key)
  const candidateKey = body.key || body.password;
  if (!isValid && candidateKey) {
    if (accessKey && constantTimeCompare(candidateKey, accessKey)) {
      isValid = true;
    } else if (adminPassword && constantTimeCompare(candidateKey, adminPassword)) {
      isValid = true;
    }
  }

  if (!isValid) {
    return NextResponse.json(
      localizeApiErrorPayload(request, {
        error: "Invalid access key",
        errorKey: "api.errors.auth.invalidAccessKey",
      }),
      { status: 401 }
    );
  }

  const sessionSecret = accessKey || adminPassword || "hindsight-session-secret";
  const response = NextResponse.json({ success: true });

  response.cookies.set({
    name: ACCESS_KEY_COOKIE,
    value: await createSessionToken(sessionSecret),
    ...sessionCookieOptions(request),
    maxAge: SESSION_MAX_AGE_SECONDS,
  });

  return response;
}

/**
 * Constant-time string comparison to prevent timing attacks.
 */
function constantTimeCompare(a: string, b: string): boolean {
  if (a.length !== b.length) {
    return false;
  }

  let result = 0;
  for (let i = 0; i < a.length; i++) {
    result |= a.charCodeAt(i) ^ b.charCodeAt(i);
  }

  return result === 0;
}
