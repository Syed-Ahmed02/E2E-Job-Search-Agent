import { initApiPassthrough } from "langgraph-nextjs-api-passthrough";
import { NextRequest, NextResponse } from "next/server";
import { createClient } from "@/lib/supabase/server";

// This file acts as a proxy for requests to your LangGraph server.
// We intercept POST requests to inject user_id from session into the config.

const passthrough = initApiPassthrough({
  apiUrl: process.env.LANGGRAPH_API_URL ?? "http://localhost:2024",
  apiKey: process.env.LANGSMITH_API_KEY ?? "remove-me",
  runtime: "edge",
});

// Helper to inject user_id into request body for POST requests
async function injectUserConfig(req: NextRequest): Promise<{ body: string; userId: string } | null> {
  try {
    // Only modify POST requests that have a body
    if (req.method !== "POST" && req.method !== "PATCH" && req.method !== "PUT") {
      return null;
    }
    
    // Get user from session
    const supabase = await createClient();
    const { data: { user } } = await supabase.auth.getUser();
    
    if (!user) {
      console.log("[API Route] No user found in session");
      return null;
    }
    
    console.log(`[API Route] Injecting user_id: ${user.id}`);
    
    // Read the request body
    const body = await req.json().catch(() => null);
    if (!body) {
      console.log("[API Route] No body found in request");
      return null;
    }
    
    // Inject user_id into config if not already present
    if (!body.config) {
      body.config = {};
    }
    if (!body.config.configurable) {
      body.config.configurable = {};
    }
    if (!body.config.configurable.user_id) {
      body.config.configurable.user_id = user.id;
      console.log(`[API Route] Injected user_id into config: ${user.id}`);
    } else {
      console.log(`[API Route] user_id already present in config: ${body.config.configurable.user_id}`);
    }
    
    return {
      body: JSON.stringify(body),
      userId: user.id
    };
  } catch (error) {
    console.error("[API Route] Error injecting user config:", error);
    return null;
  }
}

export const GET = passthrough.GET;

export const POST = async (req: NextRequest) => {
  const modified = await injectUserConfig(req);
  if (modified) {
    // Create new request with modified body
    const modifiedReq = new NextRequest(req.url, {
      method: req.method,
      headers: req.headers,
      body: modified.body,
    });
    return passthrough.POST(modifiedReq);
  }
  return passthrough.POST(req);
};

export const PUT = async (req: NextRequest) => {
  const modified = await injectUserConfig(req);
  if (modified) {
    const modifiedReq = new NextRequest(req.url, {
      method: req.method,
      headers: req.headers,
      body: modified.body,
    });
    return passthrough.PUT(modifiedReq);
  }
  return passthrough.PUT(req);
};

export const PATCH = async (req: NextRequest) => {
  const modified = await injectUserConfig(req);
  if (modified) {
    const modifiedReq = new NextRequest(req.url, {
      method: req.method,
      headers: req.headers,
      body: modified.body,
    });
    return passthrough.PATCH(modifiedReq);
  }
  return passthrough.PATCH(req);
};

export const DELETE = passthrough.DELETE;

export const OPTIONS = passthrough.OPTIONS;

// Export runtime as a static string for Next.js (must match passthrough config)
export const runtime = "edge";
