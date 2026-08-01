"use client";
import { useEffect, useRef, useState, useCallback } from "react";
import { tokenStore } from "@/lib/api";

const WS_BASE = process.env.NEXT_PUBLIC_WS_URL ?? "ws://localhost:8000/api/v1/ws";

export interface LiveMetric {
  type: "metric" | "ping";
  device_uuid?: string;
  id?: number;
  collected_at?: string;
  cpu_usage_percent?: number;
  ram_usage_percent?: number;
  disk_usage_percent?: number;
  network_bytes_sent?: number;
  network_bytes_recv?: number;
  upload_speed_bps?: number;
  download_speed_bps?: number;
  battery_percent?: number;
  total_processes?: number;
  suspicious_process_count?: number;
  uptime_seconds?: number;
}

export function useLiveMetrics(deviceUuid: string) {
  const [latest, setLatest] = useState<LiveMetric | null>(null);
  const [connected, setConnected] = useState(false);

  // Use a ref for the WebSocket so we can close it imperatively
  const wsRef = useRef<WebSocket | null>(null);
  // Use a ref for the retry timer
  const retryRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  // Track whether the hook is still mounted
  const mountedRef = useRef(true);

  // connectRef holds the latest version of connect so the onclose callback
  // never captures a stale closure (Bug #6 fix)
  const connectRef = useRef<() => void>(() => {});

  const connect = useCallback(() => {
    if (!mountedRef.current) return;

    const token = tokenStore.getAccess();
    if (!token || !deviceUuid) return;

    // Clean up any existing connection before creating a new one
    if (wsRef.current) {
      wsRef.current.onclose = null; // Prevent reconnect loop from old socket
      wsRef.current.close();
      wsRef.current = null;
    }

    const ws = new WebSocket(`${WS_BASE}/metrics/${deviceUuid}?token=${token}`);
    wsRef.current = ws;

    ws.onopen = () => {
      if (mountedRef.current) setConnected(true);
    };

    ws.onmessage = (e: MessageEvent) => {
      if (!mountedRef.current) return;
      try {
        const data: LiveMetric = JSON.parse(e.data);
        if (data.type === "metric") setLatest(data);
      } catch {
        // Malformed JSON — ignore
      }
    };

    ws.onclose = () => {
      if (!mountedRef.current) return;
      setConnected(false);
      // Always use connectRef.current here — not the captured `connect`
      // This is the critical fix for the stale closure bug.
      retryRef.current = setTimeout(() => connectRef.current(), 3000);
    };

    ws.onerror = () => {
      // onerror always fires before onclose — just let onclose handle retry
      ws.close();
    };
  }, [deviceUuid]);

  // Keep connectRef in sync with the latest connect function
  useEffect(() => {
    connectRef.current = connect;
  }, [connect]);

  useEffect(() => {
    mountedRef.current = true;
    connect();

    return () => {
      mountedRef.current = false;
      if (retryRef.current) clearTimeout(retryRef.current);
      if (wsRef.current) {
        wsRef.current.onclose = null; // Prevent retry on intentional close
        wsRef.current.close();
        wsRef.current = null;
      }
    };
  }, [connect]);

  return { latest, connected };
}
