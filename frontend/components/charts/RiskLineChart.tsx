"use client";

import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { WeekPoint } from "@/lib/types";

export function RiskLineChart({ data }: { data: WeekPoint[] }) {
  return (
    <ResponsiveContainer width="100%" height="100%">
      <LineChart data={data} margin={{ top: 16, right: 24, left: 0, bottom: 0 }}>
        <CartesianGrid stroke="rgba(255,255,255,0.06)" vertical={false} />
        <XAxis dataKey="label" tick={{ fill: "#94a3b8", fontSize: 12 }} axisLine={false} tickLine={false} />
        <YAxis
          domain={[0, 100]}
          tick={{ fill: "#94a3b8", fontSize: 12 }}
          axisLine={false}
          tickLine={false}
          width={36}
        />
        <Tooltip
          contentStyle={{
            background: "#131a2b",
            border: "1px solid rgba(255,255,255,0.1)",
            borderRadius: 12,
            color: "#e2e8f0",
          }}
          formatter={(value) => [`${value}%`, "Risk"]}
        />
        <Line
          type="monotone"
          dataKey="risk"
          stroke="#4ade80"
          strokeWidth={2.5}
          dot={{ r: 4, fill: "#4ade80", strokeWidth: 0 }}
          label={{ fill: "#cbd5e1", fontSize: 11, position: "top" }}
        />
      </LineChart>
    </ResponsiveContainer>
  );
}
