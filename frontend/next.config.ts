import type { NextConfig } from "next";

const rawApiUrl = process.env.NEXT_PUBLIC_API_URL ?? "https://inframindai.onrender.com/api/v1";
const cleanApiUrl = rawApiUrl.trim().replace(/\/+$/, "");
const targetUrl = cleanApiUrl.endsWith("/api/v1") ? cleanApiUrl : `${cleanApiUrl}/api/v1`;

const nextConfig: NextConfig = {
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: `${targetUrl}/:path*`,
      },
    ];
  },
};

export default nextConfig;
