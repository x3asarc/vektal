"use client";

import { ChatBlock } from "@/shared/contracts/chat";

type MessageBlockRendererProps = {
  blocks: ChatBlock[];
};

function renderScalar(value: unknown): string {
  if (value === null || value === undefined) return "—";
  if (typeof value === "string") return value;
  if (typeof value === "number" || typeof value === "boolean") return String(value);
  try {
    return JSON.stringify(value);
  } catch {
    return "[unserializable]";
  }
}

export function MessageBlockRenderer({ blocks }: MessageBlockRendererProps) {
  return (
    <div className="chat-blocks">
      {blocks.map((block, index) => {
        if (block.type === "text") {
          return (
            <p key={`text-${index}`} className="chat-block chat-block-text">
              {block.text}
            </p>
          );
        }

        if (block.type === "alert") {
          return (
            <p key={`alert-${index}`} className="chat-block chat-block-alert" role="alert">
              {block.text ?? "Alert"}
            </p>
          );
        }

        if (block.type === "table") {
          const rows = Array.isArray(block.data?.rows) ? block.data.rows : [];
          return (
            <section key={`table-${index}`} className="chat-block chat-block-table">
              <h4>{block.title ?? "table"}</h4>
              {rows.length === 0 ? (
                <p className="muted">No rows.</p>
              ) : (
                <ul>
                  {rows.map((row, rowIndex) => (
                    <li key={`row-${rowIndex}`}>{renderScalar(row)}</li>
                  ))}
                </ul>
              )}
            </section>
          );
        }

        if (block.type === "diff") {
          const groups = Array.isArray(block.data?.groups) ? block.data.groups : [];
          return (
            <section key={`diff-${index}`} className="chat-block chat-block-diff">
              <h4>{block.title ?? "diff"}</h4>
              {groups.length === 0 ? (
                <p className="muted">No diff groups.</p>
              ) : (
                <ul>
                  {groups.map((group, groupIndex) => (
                    <li key={`group-${groupIndex}`}>{renderScalar(group)}</li>
                  ))}
                </ul>
              )}
            </section>
          );
        }

        if (block.type === "action") {
          return (
            <section key={`action-${index}`} className="chat-block chat-block-action">
              <h4>{block.title ?? "action"}</h4>
              <pre>{renderScalar(block.data)}</pre>
            </section>
          );
        }

        if (block.type === "progress") {
          return (
            <section key={`progress-${index}`} className="chat-block chat-block-progress">
              <h4>{block.title ?? "progress"}</h4>
              <pre>{renderScalar(block.data)}</pre>
            </section>
          );
        }

        return (
          <section key={`unknown-${index}`} className="chat-block">
            <pre>{renderScalar(block)}</pre>
          </section>
        );
      })}
    </div>
  );
}
