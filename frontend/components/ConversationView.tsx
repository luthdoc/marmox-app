interface Message {
  id: string;
  content: string;
  direction: "inbound" | "outbound";
  created_at: string;
  media_url: string | null;
}

interface ConversationViewProps {
  messages: Message[];
}

function formatTime(iso: string): string {
  return new Intl.DateTimeFormat("pt-BR", {
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(iso));
}

export function ConversationView({ messages }: ConversationViewProps) {
  if (messages.length === 0) {
    return (
      <div className="flex items-center justify-center py-8">
        <p className="text-[17px] text-[var(--color-ink-muted)]">
          Sem mensagens nesta conversa.
        </p>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-3 py-2">
      {messages.map((msg) => (
        <div
          key={msg.id}
          data-direction={msg.direction}
          className={`flex flex-col max-w-[75%] ${
            msg.direction === "inbound"
              ? "self-start mr-auto items-start"
              : "self-end ml-auto items-end"
          }`}
        >
          <div
            className={`rounded-[18px] px-4 py-2.5 ${
              msg.direction === "inbound"
                ? "bg-[var(--color-canvas-parchment)] text-[var(--color-ink)]"
                : "bg-[var(--color-action-blue)] text-white"
            }`}
          >
            <p className="text-[17px]">{msg.content}</p>
            {msg.media_url && (
              <a
                href={msg.media_url}
                target="_blank"
                rel="noopener noreferrer"
                className={`text-sm underline mt-1 block ${
                  msg.direction === "outbound"
                    ? "text-blue-200"
                    : "text-[var(--color-action-blue)]"
                }`}
              >
                Ver mídia
              </a>
            )}
          </div>
          <span className="text-xs text-[var(--color-ink-muted)] mt-1 px-1">
            {formatTime(msg.created_at)}
          </span>
        </div>
      ))}
    </div>
  );
}
