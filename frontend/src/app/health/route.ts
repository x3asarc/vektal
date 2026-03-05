import { NextResponse } from "next/server";

export function GET() {
  return NextResponse.json(
    {
      status: "ok",
      service: "frontend",
      timestamp: new Date().toISOString(),
    },
    { status: 200 }
  );
}
