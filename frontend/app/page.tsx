import { NycMap } from "@/components/NycMap";

export default function MapOverviewPage() {
  return (
    <div className="flex h-[calc(100vh-6.5rem)] flex-col">
      <NycMap />
    </div>
  );
}
