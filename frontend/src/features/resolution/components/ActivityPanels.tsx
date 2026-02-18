"use client";

import { ResolutionActivityItem } from "@/shared/contracts/resolution";
import { userColor } from "@/features/resolution/components/CollaborationBadge";

type ActivityPanelsProps = {
  currentlyHappening: ResolutionActivityItem[];
  comingUpNext: ResolutionActivityItem[];
};

function ActivityList({
  title,
  items,
  emptyText,
}: {
  title: string;
  items: ResolutionActivityItem[];
  emptyText: string;
}) {
  return (
    <section className="panel" data-testid={title.toLowerCase().replace(/\s+/g, "-")}>
      <h2>{title}</h2>
      {items.length === 0 ? (
        <p className="muted">{emptyText}</p>
      ) : (
        <ul style={{ margin: 0 }}>
          {items.map((item) => (
            <li key={`${item.mode}-${item.batchId}`}>
              <strong>{item.label}</strong> ({item.mode}) - {item.status}
              {item.ownerUserId ? (
                <>
                  {" "}
                  • Owner:{" "}
                  <span style={{ color: userColor(item.ownerUserId) }}>
                    User {item.ownerUserId}
                  </span>
                </>
              ) : null}
              {item.scheduledFor ? <> • {item.scheduledFor}</> : null}
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

export function ActivityPanels({
  currentlyHappening,
  comingUpNext,
}: ActivityPanelsProps) {
  return (
    <div style={{ display: "grid", gap: 16 }}>
      <ActivityList
        title="Currently Happening"
        items={currentlyHappening}
        emptyText="No active dry-runs or apply operations."
      />
      <ActivityList
        title="Coming Up Next"
        items={comingUpNext}
        emptyText="No scheduled apply batches."
      />
    </div>
  );
}
